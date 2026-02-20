import csv
import secrets
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Q
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import ListView

from accounts.models import CustomUser

from .forms import (
    GroupForm,
    IndustryMasterForm,
    PostCommentForm,
    PostForm,
    ProductMasterForm,
    UserProfileForm,
)
from .models import (
    ChangeRequest,
    ChangeRequestRow,
    Group,
    GroupMembership,
    IndustryMaster,
    JoinRequest,
    Post,
    PostComment,
    ProductMaster,
)

PRODUCT_CSV_HEADERS = [
    "商品コード",
    "商品名",
    "大分類",
    "小分類",
    "自由項目（文字1）",
    "自由項目（文字2）",
    "自由項目（文字3）",
    "自由項目（数値1）",
    "自由項目（数値2）",
    "自由項目（日付1）",
    "自由記入",
]


def _parse_csv_date(value: str):
    value = (value or "").strip()
    if not value:
        return ""
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError("invalid date format")


def _parse_csv_int(value: str):
    value = (value or "").strip()
    if value == "":
        return None
    return int(value)


def _validate_product_csv(group, file_obj):
    import io
    import unicodedata

    # アップロードされたcsvファイルは文字コードがユーザーによりバラバラ
    # 一度 bytes のまま受けとり、utf-8,cp932でデコード
    raw = file_obj.read()

    def _decode_bytes(b: bytes) -> str:
        for enc in ("utf-8-sig", "cp932"):
            try:
                return b.decode(enc)
            except UnicodeDecodeError:
                continue
        return b.decode("utf-8", errors="replace")

    text = _decode_bytes(raw)
    sio = io.StringIO(text)
    csv_reader = csv.reader(sio)

    try:
        header_row = next(csv_reader)
    except StopIteration:
        return {
            "ok_count": 0,
            "error_count": 1,
            "total_count": 0,
            "errors": [
                {
                    "row": 1,
                    "message": "CSVが空です。テンプレートCSVを再ダウンロードして使用してください。",
                }
            ],
            "rows": [],
        }

    def _norm(s: str) -> str:
        return unicodedata.normalize("NFKC", (s or "")).strip().replace("\ufeff", "")

    header_norm = [_norm(h) for h in header_row]
    expected_norm = [_norm(h) for h in PRODUCT_CSV_HEADERS]

    if header_norm[: len(expected_norm)] != expected_norm or any(
        h != "" for h in header_norm[len(expected_norm) :]
    ):
        return {
            "ok_count": 0,
            "error_count": 1,
            "total_count": 0,
            "errors": [
                {
                    "row": 1,
                    "message": "CSVヘッダーがテンプレートと一致しません。テンプレートCSVを再ダウンロードして使用してください。",
                }
            ],
            "rows": [],
        }

    headers = PRODUCT_CSV_HEADERS
    reader = (
        # 列番号依存解消/可読性を上げる為、CSV行を「ヘッダー名→値」の辞書に変換
        # NULL列の空欄補完/余剰列の切り捨てでエラー防止
        dict(zip(headers, (row + [""] * len(headers))[: len(headers)]))
        for row in csv_reader
    )

    errors = []
    valid_payloads = []
    seen_codes = set()
    total = 0

    # csv2行目からエラー行探索させる(1行目はヘッダー)
    for i, row in enumerate(reader, start=2):
        if not row or all((v or "").strip() == "" for v in row.values()):
            continue
        total += 1
        if total > 1000:
            errors.append({"row": i, "message": "行数が上限（1000行）を超えています。"})
            break

        code = (row.get("商品コード") or "").strip()
        name = (row.get("商品名") or "").strip()

        if not code:
            errors.append({"row": i, "message": "商品コードが未入力です。"})
            continue
        if not name:
            errors.append({"row": i, "message": "商品名が未入力です。"})
            continue

        if code in seen_codes:
            errors.append(
                {"row": i, "message": f"商品コードがCSV内で重複しています: {code}"}
            )
            continue
        seen_codes.add(code)

        payload = {
            "product_code": code,
            "name": name,
            "category_main": (row.get("大分類") or "").strip() or None,
            "category_sub": (row.get("小分類") or "").strip() or None,
            "custom_text_1": (row.get("自由項目（文字1）") or "").strip() or None,
            "custom_text_2": (row.get("自由項目（文字2）") or "").strip() or None,
            "custom_text_3": (row.get("自由項目（文字3）") or "").strip() or None,
            "description": (row.get("自由記入") or "").strip() or None,
        }

        try:
            payload["custom_int_1"] = _parse_csv_int(row.get("自由項目（数値1）"))
        except (ValueError, TypeError):
            errors.append(
                {"row": i, "message": "自由項目（数値1）は整数で入力してください。"}
            )
            continue
        try:
            payload["custom_int_2"] = _parse_csv_int(row.get("自由項目（数値2）"))
        except (ValueError, TypeError):
            errors.append(
                {"row": i, "message": "自由項目（数値2）は整数で入力してください。"}
            )
            continue

        try:
            d = _parse_csv_date(row.get("自由項目（日付1）"))
            payload["custom_date_1"] = d or None
        except ValueError:
            errors.append(
                {
                    "row": i,
                    "message": "自由項目（日付1）は YYYY-MM-DD もしくは YYYY/MM/DD で入力してください。",
                }
            )
            continue

        valid_payloads.append(payload)

    codes = [p["product_code"] for p in valid_payloads]
    if codes:
        active_exists = set(
            ProductMaster.objects.filter(
                group=group, is_active=True, product_code__in=codes
            ).values_list("product_code", flat=True)
        )
        if active_exists:
            for idx, p in enumerate(valid_payloads):
                if p["product_code"] in active_exists:
                    errors.append(
                        {
                            "row": 0,
                            "message": (
                                "既に登録済みの商品コードが含まれています（追加のみ）: "
                                f"{p['product_code']}"
                            ),
                        }
                    )
            valid_payloads = [
                p for p in valid_payloads if p["product_code"] not in active_exists
            ]

        # 承認待ちが被ってたらNG
        pending_codes = set(
            ChangeRequestRow.objects.filter(
                change_request__group=group,
                change_request__kind=ChangeRequest.Kind.PRODUCT,
                change_request__status=ChangeRequest.Status.PENDING,
                code__in=codes,
            ).values_list("code", flat=True)
        )
        if pending_codes:
            for p in valid_payloads:
                if p["product_code"] in pending_codes:
                    errors.append(
                        {
                            "row": 0,
                            "message": (
                                "承認待ちの申請が既に存在する商品コードが含まれています: "
                                f"{p['product_code']}"
                            ),
                        }
                    )
            valid_payloads = [
                p for p in valid_payloads if p["product_code"] not in pending_codes
            ]

    return {
        "ok_count": len(valid_payloads),
        "error_count": len(errors),
        "total_count": total,
        "errors": errors[:30],
        "rows": valid_payloads,
    }


def _transfer_creator_or_archive(group):
    qs = GroupMembership.objects.select_for_update().filter(
        group=group,
        is_active=True,
        user__is_active=True,
    )

    candidate = (
        qs.filter(role=GroupMembership.Role.ADMIN).order_by("joined_at", "id").first()
    )
    if not candidate:
        candidate = (
            qs.filter(role=GroupMembership.Role.MEMBER)
            .order_by("joined_at", "id")
            .first()
        )

    # creatorとOWNERで二重管理状態になっている OWNERを正とした構成に変更予定
    if candidate:
        qs.filter(role=GroupMembership.Role.OWNER).exclude(id=candidate.id).update(
            role=GroupMembership.Role.ADMIN
        )
        candidate.role = GroupMembership.Role.OWNER
        candidate.save(update_fields=["role"])

        group.creator_id = candidate.user_id
        group.is_active = True
        group.save(update_fields=["creator", "is_active"])
        return

    group.creator = None
    # id:72014332 = demo用グループ(アーカイブ化させないため)
    # Groupにis_demoフラグを追加し、ハードコーディング回避の設定予定
    if getattr(group, "custom_id", None) == "72014332":
        group.is_active = True
        group.save(update_fields=["creator", "is_active"])
        return

    group.is_active = False
    group.save(update_fields=["creator", "is_active"])


# OWNER と creator を一致させたい (creator廃止に伴い要改修)
def ensure_membership(user, group):
    if not user or not getattr(user, "pk", None):
        return None
    if not group or not getattr(group, "pk", None):
        return None

    is_member = GroupMembership.objects.filter(
        group=group,
        user=user,
        is_active=True,
        user__is_active=True,
    ).exists()
    if not is_member:
        return None

    desired_role = (
        GroupMembership.Role.OWNER
        if group.creator_id == user.pk
        else GroupMembership.Role.MEMBER
    )

    m = GroupMembership.objects.filter(group=group, user=user).first()
    if not m:
        m = GroupMembership.objects.create(
            group=group,
            user=user,
            role=desired_role,
            is_active=True,
        )
        return m

    changed = False
    if not m.is_active:
        m.is_active = True
        changed = True
    if group.creator_id == user.pk and m.role != GroupMembership.Role.OWNER:
        m.role = GroupMembership.Role.OWNER
        changed = True
    if changed:
        m.save(update_fields=["role", "is_active"])
    return m


def get_membership(user, group):
    ensure_membership(user, group)

    return GroupMembership.objects.filter(
        group=group,
        user=user,
        is_active=True,
        user__is_active=True,
    ).first()


def is_group_admin(user, group):
    m = get_membership(user, group)
    return bool(
        m and m.role in (GroupMembership.Role.OWNER, GroupMembership.Role.ADMIN)
    )


def is_group_owner(user, group):
    m = get_membership(user, group)
    return bool(m and m.role == GroupMembership.Role.OWNER)


def require_group_admin(user, group):
    if not is_group_admin(user, group):
        raise PermissionDenied


def require_group_owner(user, group):
    if not is_group_owner(user, group):
        raise PermissionDenied


class TrialPingView(View):
    def get(self, request):
        return JsonResponse({"ok": True})


class TrialStartView(View):
    TRIAL_DURATION_MINUTES = 30
    DEMO_GROUP_CUSTOM_ID = "72014332"

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home")

        trial_session_id = uuid.uuid4()
        expires_at = timezone.now() + timedelta(minutes=self.TRIAL_DURATION_MINUTES)
        raw_password = secrets.token_urlsafe(32)
        trial_question = "trial用質問"
        trial_answer = secrets.token_urlsafe(16)

        user = None
        for _ in range(30):
            n = secrets.randbelow(1000)
            custom_user_id = f"trial{n:03d}"
            username = f"お試しユーザー{n:03d}"

            try:
                with transaction.atomic():
                    user = CustomUser(
                        custom_user_id=custom_user_id,
                        username=username,
                        question=trial_question,
                        answer=trial_answer,
                        is_trial=True,
                        trial_started_at=timezone.now(),
                        trial_expires_at=expires_at,
                        trial_session_id=trial_session_id,
                    )
                    user.set_password(raw_password)
                    user.save()

                    demo_group, _created = Group.objects.get_or_create(
                        custom_id=self.DEMO_GROUP_CUSTOM_ID,
                        defaults={"name": "お試しグループ", "is_active": True},
                    )
                    if not demo_group.is_active:
                        demo_group.is_active = True
                        demo_group.save(update_fields=["is_active"])

                    if demo_group.creator_id is None:
                        demo_group.creator_id = user.pk
                        demo_group.save(update_fields=["creator"])

                    user.groups.add(demo_group)

                    GroupMembership.objects.get_or_create(
                        group=demo_group,
                        user=user,
                        defaults={
                            "role": (
                                GroupMembership.Role.OWNER
                                if demo_group.creator_id == user.pk
                                else GroupMembership.Role.MEMBER
                            ),
                            "is_active": True,
                        },
                    )

                break
            except IntegrityError:
                user = None
                continue

        if user is None:
            messages.error(
                request,
                "お試しユーザーの作成に失敗しました。少し時間をおいて再度お試しください。",
            )
            return redirect("home")

        request.session["trial_session_id"] = str(trial_session_id)
        request.session["trial_expires_at"] = str(expires_at.timestamp())

        login(request, user)
        messages.success(
            request,
            format_html(
                "お試しログインへようこそ！<br><br>"
                "このモードでは、ログアウト時 または 30分経過時 に全ての編集データが削除されます。"
            ),
        )
        return redirect("home")


class Timeline(LoginRequiredMixin, ListView):
    model = Post
    template_name = "post/timeline.html"
    # TODO: デフォルト名をわざわざ指定してしまっている → "post"に変更の上、該当template参照箇所も同時に修正
    context_object_name = "object_list"
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        custom_id = self.request.GET.get("custom_id")
        user_groups = Group.objects.filter(users=user, is_active=True)

        if custom_id:
            group = get_object_or_404(
                Group, custom_id=custom_id, users=user, is_active=True
            )
            queryset = (
                Post.objects.filter(group=group)
                .select_related("user", "group", "product", "industry")
                .prefetch_related("comments__author")
            )
        else:
            queryset = (
                Post.objects.filter(group__in=user_groups)
                .select_related("user", "group", "product", "industry")
                .prefetch_related("comments__author")
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        custom_id = self.request.GET.get("custom_id")
        context["user_groups"] = Group.objects.filter(
            users=self.request.user, is_active=True
        )
        context["selected_group_id"] = custom_id
        initial = {}
        if custom_id:
            g = Group.objects.filter(
                custom_id=custom_id, users=self.request.user, is_active=True
            ).first()
            if g:
                initial["group"] = g.pk
                context["selected_group_pk"] = g.pk
        context["form"] = PostForm(user=self.request.user, initial=initial)

        queryset = self.get_queryset()
        paginator = Paginator(queryset, self.paginate_by)
        page = self.request.GET.get("page")
        try:
            object_list = paginator.page(page)
        except PageNotAnInteger:
            object_list = paginator.page(1)
        except EmptyPage:
            object_list = paginator.page(paginator.num_pages)

        context["object_list"] = object_list
        context["object_list_class_name"] = object_list.__class__.__name__
        return context

    def post(self, request, *args, **kwargs):
        custom_id = request.GET.get("custom_id")

        if "delete_post_id" in request.POST:
            post_id = request.POST.get("delete_post_id")
            post = get_object_or_404(Post, id=post_id, user=request.user)
            if post.image:
                post.image.delete(save=False)
            post.delete()
            messages.success(request, "投稿を削除しました。")

            base = reverse("mysfa:timeline")
            if custom_id:
                return redirect(f"{base}?custom_id={custom_id}")
            return redirect(base)

        form = PostForm(request.POST, request.FILES, user=request.user)

        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            if "image" in request.FILES:
                post.image = request.FILES["image"]
            post.save()

            messages.success(request, "投稿しました。")

            base = reverse("mysfa:timeline")
            if custom_id:
                return redirect(f"{base}?custom_id={custom_id}")
            return redirect(base)

        self.object_list = self.get_queryset()
        context = self.get_context_data()
        context["form"] = form
        context["selected_group_id"] = custom_id
        return self.render_to_response(context)


class ProductMasterSearchApiView(LoginRequiredMixin, View):
    def get(self, request, custom_id):
        group = get_object_or_404(
            Group, custom_id=custom_id, is_active=True, users=request.user
        )

        q = (request.GET.get("q") or "").strip()
        try:
            limit = int(request.GET.get("limit") or 50)
        except (TypeError, ValueError):
            limit = 50
        limit = max(1, min(limit, 200))

        qs = ProductMaster.objects.filter(group=group, is_active=True).order_by(
            "product_code"
        )
        if q:
            qs = qs.filter(Q(product_code__icontains=q) | Q(name__icontains=q))

        results = [
            {
                "id": m.id,
                "product_code": m.product_code,
                "name": m.name,
                "label": f"{m.product_code} {m.name}",
            }
            for m in qs[:limit]
        ]
        return JsonResponse({"results": results})


class IndustryMasterSearchApiView(LoginRequiredMixin, View):
    def get(self, request, custom_id):
        group = get_object_or_404(
            Group, custom_id=custom_id, is_active=True, users=request.user
        )

        q = (request.GET.get("q") or "").strip()
        try:
            limit = int(request.GET.get("limit") or 50)
        except (TypeError, ValueError):
            limit = 50
        limit = max(1, min(limit, 200))

        qs = IndustryMaster.objects.filter(group=group, is_active=True).order_by(
            "name", "id"
        )
        if q:
            qs = qs.filter(name__icontains=q)

        results = [{"id": m.id, "name": m.name, "label": m.name} for m in qs[:limit]]
        return JsonResponse({"results": results})


class MyGroupsApiView(LoginRequiredMixin, View):
    def get(self, request):
        qs = Group.objects.filter(users=request.user, is_active=True).order_by(
            "name", "custom_id"
        )
        results = [{"custom_id": g.custom_id, "name": g.name} for g in qs]
        return JsonResponse({"results": results})


class ProductCategoryOptionsApiView(LoginRequiredMixin, View):
    def get(self, request, custom_id):
        group = get_object_or_404(
            Group, custom_id=custom_id, is_active=True, users=request.user
        )
        qs = ProductMaster.objects.filter(group=group, is_active=True)

        mains = list(
            qs.exclude(category_main__isnull=True)
            .exclude(category_main="")
            .order_by()
            .values_list("category_main", flat=True)
            .distinct()
        )
        subs = list(
            qs.exclude(category_sub__isnull=True)
            .exclude(category_sub="")
            .order_by()
            .values_list("category_sub", flat=True)
            .distinct()
        )

        # DBのcollation差で順序がブレないよう、Python側で安定ソートする
        mains = sorted(mains)
        subs = sorted(subs)

        return JsonResponse({"category_main": mains, "category_sub": subs})


class MyPost(LoginRequiredMixin, ListView):
    model = Post
    template_name = "post/mypost.html"
    context_object_name = "posts"
    paginate_by = 10

    def get_queryset(self):
        custom_user_id = self.kwargs["custom_user_id"]
        user = get_object_or_404(CustomUser, custom_user_id=custom_user_id)
        queryset = (
            Post.objects.filter(user=user)
            .select_related("user", "group", "product", "industry")
            .prefetch_related("liked_users", "comments__author")
        )

        custom_id = self.request.GET.get("custom_id")
        if custom_id:
            group = Group.objects.filter(
                custom_id=custom_id,
                is_active=True,
                users=user,
            ).first()
            if not group:
                return Post.objects.none()
            queryset = queryset.filter(group=group)

        status = (self.request.GET.get("status") or "").strip()
        allowed_statuses = {s for s, _label in Post.Status.choices}
        if status and status in allowed_statuses:
            queryset = queryset.filter(status=status)

        sort = (self.request.GET.get("sort") or "").strip()
        if sort == "group":
            queryset = queryset.order_by("group__name", "-created_at", "-id")
        else:
            queryset = queryset.order_by("-created_at", "-id")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        custom_user_id = self.kwargs["custom_user_id"]
        context["displayed_user"] = get_object_or_404(
            CustomUser, custom_user_id=custom_user_id
        )
        context["current_user"] = self.request.user
        context["form"] = UserProfileForm(instance=self.request.user)

        from django.conf import settings

        context["MEDIA_URL"] = settings.MEDIA_URL

        user_groups = Group.objects.filter(
            users=context["displayed_user"], is_active=True
        )
        context["user_groups"] = user_groups
        context["status_choices"] = list(Post.Status.choices)
        context["selected_status"] = (self.request.GET.get("status") or "").strip()
        context["selected_sort"] = (self.request.GET.get("sort") or "").strip()

        queryset = self.get_queryset()
        paginator = Paginator(queryset, self.paginate_by)
        page = self.request.GET.get("page")
        try:
            object_list = paginator.page(page)
        except PageNotAnInteger:
            object_list = paginator.page(1)
        except EmptyPage:
            object_list = paginator.page(paginator.num_pages)

        context["object_list"] = object_list
        context["object_list_class_name"] = object_list.__class__.__name__
        context["posts"] = object_list

        params = self.request.GET.copy()
        if "page" in params:
            params.pop("page")
        context["query_params"] = params.urlencode()
        return context

    def post(self, request, *args, **kwargs):
        if "delete_post_id" in request.POST:
            post_id = request.POST.get("delete_post_id")
            post = get_object_or_404(Post, id=post_id, user=request.user)
            if post.image:
                post.image.delete(save=False)
            post.delete()
            messages.success(request, "投稿を削除しました。")
            return redirect("mysfa:mypost", custom_user_id=request.user.custom_user_id)

        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("mysfa:mypost", custom_user_id=request.user.custom_user_id)

        context = self.get_context_data()
        context["form"] = form
        return render(request, self.template_name, context)


@method_decorator(login_required, name="dispatch")
class UploadIconView(View):
    def post(self, request, *args, **kwargs):
        user = request.user
        default_image_path = "default_images/ic013.png"

        if "profile_image" in request.FILES:
            if user.profile_image and user.profile_image.name != default_image_path:
                user.profile_image.delete(save=False)
            user.profile_image = request.FILES["profile_image"]
        else:
            if not user.profile_image:
                user.profile_image = default_image_path

        user.save()
        return redirect("mysfa:mypost", custom_user_id=user.custom_user_id)


class UpdateUsernameView(View):
    def post(self, request, *args, **kwargs):
        user = request.user
        user.username = request.POST.get("username")
        user.save()
        return redirect("mysfa:mypost", custom_user_id=user.custom_user_id)


class GroupPost(LoginRequiredMixin, ListView):
    model = Post
    template_name = "group/grouppost.html"
    context_object_name = "posts"
    paginate_by = 10

    def get_queryset(self):
        group = get_object_or_404(
            Group, custom_id=self.kwargs["custom_id"], is_active=True
        )
        qs = (
            Post.objects.filter(group=group)
            .select_related("user", "group", "product", "industry")
            .prefetch_related("comments__author")
            .distinct()
        )

        status = (self.request.GET.get("status") or "").strip()
        allowed_statuses = {s for s, _label in Post.Status.choices}
        if status and status in allowed_statuses:
            qs = qs.filter(status=status)

        sort = (self.request.GET.get("sort") or "").strip()
        if sort == "member":
            qs = qs.order_by("user__username", "-created_at", "-id")
        else:
            qs = qs.order_by("-created_at", "-id")
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = get_object_or_404(
            Group, custom_id=self.kwargs["custom_id"], is_active=True
        )
        user = self.request.user
        creator = group.creator
        members = group.users.all()

        context["group"] = group
        context["is_member"] = group.users.filter(pk=user.pk).exists()
        context["membership"] = get_membership(user, group)
        context["can_group_admin"] = is_group_admin(user, group)
        context["can_group_owner"] = is_group_owner(user, group)
        context["creator"] = creator
        memberships = {
            m.user_id: m
            for m in GroupMembership.objects.filter(
                group=group, is_active=True
            ).select_related("user")
        }
        member_rows = []
        for u in members:
            m = memberships.get(u.pk)
            if not m:
                role = (
                    GroupMembership.Role.OWNER
                    if group.creator_id == u.pk
                    else GroupMembership.Role.MEMBER
                )
                m = GroupMembership(group=group, user=u, role=role, is_active=True)
            member_rows.append({"user": u, "membership": m})

        context["member_rows"] = member_rows
        context["member_count"] = members.count()
        context["user_has_requested"] = JoinRequest.objects.filter(
            user=user, group=group
        ).exists()
        context["join_requests"] = JoinRequest.objects.filter(group=group)
        context["status_choices"] = list(Post.Status.choices)
        context["selected_status"] = (self.request.GET.get("status") or "").strip()
        context["selected_sort"] = (self.request.GET.get("sort") or "").strip()

        queryset = self.get_queryset()
        paginator = Paginator(queryset, self.paginate_by)
        page = self.request.GET.get("page")
        try:
            object_list = paginator.page(page)
        except PageNotAnInteger:
            object_list = paginator.page(1)
        except EmptyPage:
            object_list = paginator.page(paginator.num_pages)

        context["object_list"] = object_list
        context["object_list_class_name"] = object_list.__class__.__name__
        context["posts"] = object_list

        params = self.request.GET.copy()
        if "page" in params:
            params.pop("page")
        context["query_params"] = params.urlencode()
        return context

    def post(self, request, *args, **kwargs):
        if "delete_post_id" in request.POST:
            post_id = request.POST.get("delete_post_id")
            post = get_object_or_404(Post, id=post_id, user=request.user)
            if post.image:
                post.image.delete(save=False)
            post.delete()
            messages.success(request, "投稿を削除しました。")
            return redirect("mysfa:group_posts", custom_id=self.kwargs["custom_id"])

        return self.get(request, *args, **kwargs)


class GroupAdminView(LoginRequiredMixin, View):
    template_name = "group/group_admin.html"

    def get(self, request, custom_id):
        from django.conf import settings

        group = get_object_or_404(Group, custom_id=custom_id, is_active=True)
        require_group_admin(request.user, group)

        # 旧データ救済：Group.usersにいるのにmembershipが無いユーザーを作る
        members = group.users.all().select_related()
        existing = {
            (m.user_id): m
            for m in GroupMembership.objects.filter(group=group).select_related("user")
        }
        for u in members:
            if u.pk not in existing:
                role = (
                    GroupMembership.Role.OWNER
                    if group.creator_id == u.pk
                    else GroupMembership.Role.MEMBER
                )
                existing[u.pk] = GroupMembership.objects.create(
                    group=group, user=u, role=role, is_active=True
                )

        member_rows = []
        for u in members:
            m = existing.get(u.pk)
            if not m:
                continue
            member_rows.append(
                {
                    "user": u,
                    "membership": m,
                    "is_creator": group.creator_id == u.pk,
                }
            )

        context = {
            "group": group,
            "MEDIA_URL": settings.MEDIA_URL,
            "member_rows": member_rows,
            "membership": get_membership(request.user, group),
            "can_group_admin": is_group_admin(request.user, group),
            "can_group_owner": is_group_owner(request.user, group),
        }
        return render(request, self.template_name, context)


class GroupMembershipUpdateView(LoginRequiredMixin, View):
    def post(self, request, custom_id, custom_user_id):
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True)
        require_group_owner(request.user, group)

        target_user = get_object_or_404(CustomUser, custom_user_id=custom_user_id)
        target = get_object_or_404(
            GroupMembership, group=group, user=target_user, is_active=True
        )

        role = request.POST.get("role")
        if role not in (
            GroupMembership.Role.ADMIN,
            GroupMembership.Role.MEMBER,
            GroupMembership.Role.OWNER,
        ):
            messages.error(request, "不正なロールです。")
            return redirect("mysfa:group_admin", custom_id=custom_id)

        # OWNERは委譲専用（ここでOWNERに変えない）
        if role == GroupMembership.Role.OWNER and target_user.pk != group.creator_id:
            messages.error(
                request, "オーナー変更は「オーナーにする」から行ってください。"
            )
            return redirect("mysfa:group_admin", custom_id=custom_id)

        if target.role == GroupMembership.Role.OWNER:
            messages.error(request, "オーナーのロールはこの操作では変更できません。")
            return redirect("mysfa:group_admin", custom_id=custom_id)

        target.role = role
        target.save(update_fields=["role"])
        messages.success(request, "ロールを更新しました。")
        return redirect("mysfa:group_admin", custom_id=custom_id)


class GroupTransferOwnerView(LoginRequiredMixin, View):
    def post(self, request, custom_id, custom_user_id):
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True)
        require_group_owner(request.user, group)

        target_user = get_object_or_404(CustomUser, custom_user_id=custom_user_id)
        target = get_object_or_404(
            GroupMembership, group=group, user=target_user, is_active=True
        )

        if target.role == GroupMembership.Role.OWNER:
            return redirect("mysfa:group_admin", custom_id=custom_id)

        with transaction.atomic():
            qs = GroupMembership.objects.select_for_update().filter(
                group=group, is_active=True
            )
            qs.filter(role=GroupMembership.Role.OWNER).update(
                role=GroupMembership.Role.ADMIN
            )
            target.role = GroupMembership.Role.OWNER
            target.save(update_fields=["role"])

            group.creator_id = target_user.pk
            group.save(update_fields=["creator"])

        messages.success(request, f"{target_user.username} をオーナーにしました。")
        return redirect("mysfa:group_admin", custom_id=custom_id)


@method_decorator(login_required, name="dispatch")
class UploadGroupIconView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs["custom_id"], is_active=True)
        default_image_path = "default_images/702.png"

        if "icon" in request.FILES:
            if group.icon and group.icon.name != default_image_path:
                group.icon.delete(save=False)
            group.icon = request.FILES["icon"]
        else:
            if not group.icon:
                group.icon = default_image_path

        group.save()
        return redirect("mysfa:group_posts", custom_id=group.custom_id)


class ToggleGroupLockView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs["custom_id"], is_active=True)
        require_group_admin(request.user, group)

        group.is_locked = not group.is_locked
        group.save(update_fields=["is_locked"])
        return redirect("mysfa:group_posts", custom_id=group.custom_id)


class JoinGroupView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs["custom_id"], is_active=True)

        if group.custom_id == "72014332" and group.creator_id is None:
            with transaction.atomic():
                g = (
                    Group.objects.select_for_update()
                    .filter(custom_id=group.custom_id, is_active=True)
                    .first()
                )
                if g and g.creator_id is None:
                    g.creator_id = request.user.pk
                    g.save(update_fields=["creator"])
                    group = g

        request.user.groups.add(group)

        GroupMembership.objects.get_or_create(
            group=group,
            user=request.user,
            defaults={"role": GroupMembership.Role.MEMBER, "is_active": True},
        )

        ensure_membership(request.user, group)
        return redirect("mysfa:group_posts", custom_id=kwargs["custom_id"])


class JoinGroupRequestView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs["custom_id"], is_active=True)

        if GroupMembership.objects.filter(
            group=group,
            user=request.user,
            is_active=True,
            user__is_active=True,
        ).exists():
            return redirect("mysfa:group_posts", custom_id=group.custom_id)

        if group.custom_id == "72014332" and group.creator_id is None:
            with transaction.atomic():
                g = (
                    Group.objects.select_for_update()
                    .filter(custom_id=group.custom_id, is_active=True)
                    .first()
                )
                if g and g.creator_id is None:
                    g.creator_id = request.user.pk
                    g.save(update_fields=["creator"])
                    group = g

            request.user.groups.add(group)
            ensure_membership(request.user, group)
            return redirect("mysfa:group_posts", custom_id=group.custom_id)

        if group.is_locked:
            if not JoinRequest.objects.filter(user=request.user, group=group).exists():
                JoinRequest.objects.create(user=request.user, group=group)
            return redirect("mysfa:group_posts", custom_id=group.custom_id)

        request.user.groups.add(group)

        GroupMembership.objects.get_or_create(
            group=group,
            user=request.user,
            defaults={"role": GroupMembership.Role.MEMBER, "is_active": True},
        )
        ensure_membership(request.user, group)
        return redirect("mysfa:group_posts", custom_id=group.custom_id)


class ApproveJoinRequestView(View):
    def post(self, request, custom_id, request_id):
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True)
        require_group_admin(request.user, group)

        join_request = get_object_or_404(
            JoinRequest, user__custom_user_id=request_id, group=group
        )
        join_request.user.groups.add(group)

        GroupMembership.objects.get_or_create(
            group=group,
            user=join_request.user,
            defaults={"role": GroupMembership.Role.MEMBER, "is_active": True},
        )

        join_request.delete()
        return redirect("mysfa:group_posts", custom_id=custom_id)


class RejectJoinRequestView(View):
    def post(self, request, custom_id, request_id):
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True)
        require_group_admin(request.user, group)

        join_request = get_object_or_404(
            JoinRequest, user__custom_user_id=request_id, group=group
        )
        join_request.delete()
        return redirect("mysfa:group_posts", custom_id=custom_id)


class LeaveGroupView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs["custom_id"], is_active=True)
        was_creator = group.creator_id == request.user.pk
        request.user.groups.remove(group)

        with transaction.atomic():
            # 退会履歴を保持せず、その場でレコード削除
            GroupMembership.objects.filter(
                group=group,
                user=request.user,
            ).delete()

            remaining_count = GroupMembership.objects.filter(
                group=group,
                is_active=True,
                user__is_active=True,
            ).count()
            if was_creator or remaining_count == 0:
                _transfer_creator_or_archive(group)

        return redirect("home")


class DeleteGroupView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs["custom_id"], is_active=True)
        require_group_owner(request.user, group)

        group.is_active = False
        group.save(update_fields=["is_active"])
        return redirect("home")


class RemoveMemberView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs["custom_id"], is_active=True)
        require_group_admin(request.user, group)

        user_to_remove = get_object_or_404(
            CustomUser, custom_user_id=kwargs["custom_user_id"]
        )
        target_m = get_membership(user_to_remove, group)
        if target_m and target_m.role == GroupMembership.Role.OWNER:
            messages.error(
                request, "オーナーは退会させられません。委譲後に行ってください。"
            )
            return redirect("mysfa:group_posts", custom_id=kwargs["custom_id"])

        if GroupMembership.objects.filter(
            group=group,
            user=user_to_remove,
            is_active=True,
            user__is_active=True,
        ).exists():
            user_to_remove.groups.remove(group)
            GroupMembership.objects.filter(group=group, user=user_to_remove).delete()
            messages.success(
                request, f"{user_to_remove.username}をグループから退会させました。"
            )
        else:
            messages.error(request, "このユーザーはグループに所属していません。")

        return redirect("mysfa:group_posts", custom_id=kwargs["custom_id"])


class ProductMasterIndexView(LoginRequiredMixin, View):
    template_name = "master/product-master.html"

    def get(self, request, custom_id):
        group = get_object_or_404(
            Group, custom_id=custom_id, is_active=True, users=request.user
        )

        search = request.GET.get("search", "").strip()

        allowed_per_page = (25, 50, 100, 500)
        raw = request.GET.get("per_page", "50")
        try:
            per_page = int(raw)
        except (TypeError, ValueError):
            per_page = 50
        if per_page not in allowed_per_page:
            per_page = 50

        qs = ProductMaster.objects.filter(group=group, is_active=True).order_by(
            "product_code"
        )
        if search:
            qs = qs.filter(
                Q(product_code__icontains=search) | Q(name__icontains=search)
            )

        total_count = qs.count()

        paginator = Paginator(qs, per_page)
        page = request.GET.get("page", 1)
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        masters = page_obj

        context = {
            "group": group,
            "search": search,
            "masters": masters,
            "form": ProductMasterForm(),
            "page_obj": page_obj,
            "paginator": paginator,
            "total_count": total_count,
            "per_page": per_page,
            "allowed_per_page": allowed_per_page,
            "is_creator": group.creator_id == request.user.pk,
        }
        return render(request, self.template_name, context)

    def post(self, request, custom_id):
        group = get_object_or_404(
            Group, custom_id=custom_id, is_active=True, users=request.user
        )

        form = ProductMasterForm(request.POST)
        if form.is_valid():
            product_code = form.cleaned_data["product_code"]
            existing = ProductMaster.objects.filter(
                group=group, product_code=product_code
            ).first()

            payload = {
                field: form.cleaned_data.get(field) for field in form.Meta.fields
            }
            payload["product_code"] = product_code

            with transaction.atomic():
                title_prefix = "商品更新申請" if existing else "商品追加申請"
                cr = ChangeRequest.objects.create(
                    group=group,
                    kind=ChangeRequest.Kind.PRODUCT,
                    status=ChangeRequest.Status.PENDING,
                    requester=request.user,
                    submitted_at=timezone.now(),
                    title=f"{title_prefix}: {product_code} {payload.get('name', '')}",
                )
                ChangeRequestRow.objects.create(
                    change_request=cr,
                    row_index=1,
                    op=ChangeRequestRow.Op.UPSERT,
                    code=str(product_code),
                    name=payload.get("name", ""),
                    diff_json=payload,
                    is_valid=True,
                )

            messages.success(
                request, "変更申請を送信しました（承認後に反映されます）。"
            )
            return redirect("mysfa:product_master", custom_id=custom_id)

        search = request.GET.get("search", "").strip()

        allowed_per_page = (25, 50, 100, 500)
        raw = request.GET.get("per_page", "50")
        try:
            per_page = int(raw)
        except (TypeError, ValueError):
            per_page = 50
        if per_page not in allowed_per_page:
            per_page = 50

        qs = ProductMaster.objects.filter(group=group, is_active=True).order_by(
            "product_code"
        )
        if search:
            qs = qs.filter(
                Q(product_code__icontains=search) | Q(name__icontains=search)
            )

        total_count = qs.count()

        paginator = Paginator(qs, per_page)
        page = request.GET.get("page", 1)
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        masters = page_obj

        context = {
            "group": group,
            "search": search,
            "masters": masters,
            "form": form,
            "page_obj": page_obj,
            "paginator": paginator,
            "total_count": total_count,
            "per_page": per_page,
            "allowed_per_page": allowed_per_page,
            "is_creator": group.creator_id == request.user.pk,
        }
        return render(request, self.template_name, context)


class ProductMasterEditView(LoginRequiredMixin, View):
    template_name = "master/product-master-edit.html"

    def get(self, request, custom_id, pk):
        group = get_object_or_404(
            Group, custom_id=custom_id, is_active=True, users=request.user
        )
        master = get_object_or_404(ProductMaster, pk=pk, group=group)

        form = ProductMasterForm(instance=master)
        if "product_code" in form.fields:
            form.fields["product_code"].disabled = True
        return render(
            request,
            self.template_name,
            {
                "group": group,
                "master": master,
                "form": form,
            },
        )

    def post(self, request, custom_id, pk):
        group = get_object_or_404(
            Group, custom_id=custom_id, is_active=True, users=request.user
        )
        master = get_object_or_404(ProductMaster, pk=pk, group=group)

        form = ProductMasterForm(request.POST, instance=master)
        if "product_code" in form.fields:
            form.fields["product_code"].disabled = True
        if form.is_valid():
            product_code = master.product_code
            payload = {
                field: form.cleaned_data.get(field) for field in form.Meta.fields
            }
            payload["product_code"] = product_code
            payload["_target_pk"] = master.pk

            with transaction.atomic():
                cr = ChangeRequest.objects.create(
                    group=group,
                    kind=ChangeRequest.Kind.PRODUCT,
                    status=ChangeRequest.Status.PENDING,
                    requester=request.user,
                    submitted_at=timezone.now(),
                    title=f"商品更新申請: {product_code} {payload.get('name', '')}",
                )
                ChangeRequestRow.objects.create(
                    change_request=cr,
                    row_index=1,
                    op=ChangeRequestRow.Op.UPSERT,
                    code=str(product_code),
                    name=payload.get("name", ""),
                    diff_json=payload,
                    is_valid=True,
                )

            messages.success(
                request, "変更申請を送信しました（承認後に反映されます）。"
            )
            return redirect("mysfa:product_master", custom_id=custom_id)

        return render(
            request,
            self.template_name,
            {
                "group": group,
                "master": master,
                "form": form,
            },
        )


class ProductMasterCsvTemplateView(LoginRequiredMixin, View):
    def get(self, request, custom_id):
        group = get_object_or_404(
            Group, custom_id=custom_id, is_active=True, users=request.user
        )

        # Excel由来の文字コード事故を減らすため、UTF-8 BOM付きで返す
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="product_master_template_{group.custom_id}.csv"'
        )
        response.write("\ufeff")

        writer = csv.writer(response)
        writer.writerow(PRODUCT_CSV_HEADERS)
        return response


class ProductMasterCsvValidateView(LoginRequiredMixin, View):
    def post(self, request, custom_id):
        group = get_object_or_404(
            Group, custom_id=custom_id, is_active=True, users=request.user
        )
        f = request.FILES.get("file")
        if not f:
            return JsonResponse(
                {"ok": False, "message": "CSVファイルを選択してください。"}, status=400
            )

        result = _validate_product_csv(group, f.file)
        return JsonResponse(
            {
                "ok": result["error_count"] == 0 and result["total_count"] <= 1000,
                "total_count": result["total_count"],
                "error_count": result["error_count"],
                "ok_count": result["ok_count"],
                "errors": result["errors"],
            }
        )


class ProductMasterCsvSubmitView(LoginRequiredMixin, View):
    def post(self, request, custom_id):
        group = get_object_or_404(
            Group, custom_id=custom_id, is_active=True, users=request.user
        )
        f = request.FILES.get("file")
        if not f:
            messages.error(request, "CSVファイルを選択してください。")
            return redirect("mysfa:product_master", custom_id=custom_id)

        result = _validate_product_csv(group, f.file)
        if result["total_count"] > 1000:
            messages.error(request, "行数が上限（1000行）を超えています。")
            return redirect("mysfa:product_master", custom_id=custom_id)
        if result["error_count"] > 0:
            messages.error(request, "CSVにエラーがあるため、登録依頼できません。")
            return redirect("mysfa:product_master", custom_id=custom_id)
        if result["ok_count"] == 0:
            messages.error(request, "登録依頼できる行がありません。")
            return redirect("mysfa:product_master", custom_id=custom_id)

        payloads = result["rows"]
        with transaction.atomic():
            cr = ChangeRequest.objects.create(
                group=group,
                kind=ChangeRequest.Kind.PRODUCT,
                status=ChangeRequest.Status.PENDING,
                requester=request.user,
                submitted_at=timezone.now(),
                title=f"CSV一括登録: {len(payloads)}件",
            )
            rows = [
                ChangeRequestRow(
                    change_request=cr,
                    row_index=i + 1,
                    op=ChangeRequestRow.Op.UPSERT,
                    code=str(p["product_code"]),
                    name=p.get("name", ""),
                    diff_json=p,
                    is_valid=True,
                )
                for i, p in enumerate(payloads)
            ]
            ChangeRequestRow.objects.bulk_create(rows)

        messages.success(request, f"CSV登録の依頼を送信しました（{len(payloads)}件）。")
        return redirect("mysfa:product_master", custom_id=custom_id)


class ProductChangeRequestInboxView(LoginRequiredMixin, View):
    template_name = "master/product-change-requests.html"

    def get(self, request, custom_id):
        group = get_object_or_404(
            Group, custom_id=custom_id, is_active=True, users=request.user
        )
        if request.user != group.creator:
            return HttpResponseForbidden("グループ管理者以外は閲覧できません。")

        requests_qs = (
            ChangeRequest.objects.filter(
                group=group,
                kind=ChangeRequest.Kind.PRODUCT,
                status=ChangeRequest.Status.PENDING,
            )
            .prefetch_related("rows")
            .order_by("-submitted_at", "-id")
        )

        return render(
            request, self.template_name, {"group": group, "requests": requests_qs}
        )


class ProductChangeRequestDecideView(LoginRequiredMixin, View):
    def post(self, request, custom_id, cr_id):
        group = get_object_or_404(
            Group, custom_id=custom_id, is_active=True, users=request.user
        )
        if request.user != group.creator:
            return HttpResponseForbidden("グループ管理者以外は操作できません。")

        cr = get_object_or_404(
            ChangeRequest,
            id=cr_id,
            group=group,
            kind=ChangeRequest.Kind.PRODUCT,
            status=ChangeRequest.Status.PENDING,
        )

        action = request.POST.get("action")

        with transaction.atomic():
            if action == "approve":
                for row in cr.rows.all():
                    if row.op == ChangeRequestRow.Op.DELETE:
                        ProductMaster.objects.filter(
                            group=group, product_code=row.code
                        ).update(is_active=False)
                        continue

                    if row.op == ChangeRequestRow.Op.UPSERT:
                        data = row.diff_json or {}
                        code = str(row.code)
                        obj = ProductMaster.objects.filter(
                            group=group, product_code=code
                        ).first()
                        if not obj:
                            obj = ProductMaster(group=group, product_code=code)

                        # 受け取ったペイロードを反映するが、
                        for key, value in data.items():
                            if key in (
                                "_target_pk",
                                "group",
                                "is_active",
                                "created_at",
                                "updated_at",
                            ):
                                continue
                            if hasattr(obj, key):
                                setattr(obj, key, value)

                        obj.group = group
                        obj.product_code = code
                        obj.is_active = True
                        obj.save()

                cr.status = ChangeRequest.Status.APPROVED
                cr.approver = request.user
                cr.decided_at = timezone.now()
                cr.save()

                messages.success(request, "申請を承認しました。")
            else:
                cr.status = ChangeRequest.Status.REJECTED
                cr.decided_at = timezone.now()
                cr.save()

                messages.info(request, "申請を却下しました。")

        return redirect("mysfa:product_change_requests", custom_id=custom_id)


class ProductDeleteRequestBulkCreateView(LoginRequiredMixin, View):

    def post(self, request, custom_id):
        group = get_object_or_404(
            Group, custom_id=custom_id, is_active=True, users=request.user
        )

        selected_ids = request.POST.getlist("selected_ids")
        if not selected_ids:
            messages.error(request, "削除する商品を選択してください。")
            return redirect("mysfa:product_master", custom_id=custom_id)

        masters_qs = ProductMaster.objects.filter(
            group=group, is_active=True, id__in=selected_ids
        ).order_by("product_code")
        masters = list(masters_qs)

        if len(masters) != len(set(selected_ids)):
            messages.error(
                request,
                "選択された商品の中に、存在しない商品または無効な商品があります。",
            )
            return redirect("mysfa:product_master", custom_id=custom_id)

        codes = [str(m.product_code) for m in masters]

        pending_codes = set(
            ChangeRequestRow.objects.filter(
                change_request__group=group,
                change_request__kind=ChangeRequest.Kind.PRODUCT,
                change_request__status=ChangeRequest.Status.PENDING,
                op=ChangeRequestRow.Op.DELETE,
                code__in=codes,
            ).values_list("code", flat=True)
        )

        if pending_codes:
            pending_list = ", ".join(sorted(pending_codes))
            messages.error(
                request,
                f"承認待ち商品が含まれているため、中止しました。対象商品コード: {pending_list}",
            )
            return redirect("mysfa:product_master", custom_id=custom_id)

        with transaction.atomic():
            cr = ChangeRequest.objects.create(
                group=group,
                kind=ChangeRequest.Kind.PRODUCT,
                status=ChangeRequest.Status.PENDING,
                requester=request.user,
                submitted_at=timezone.now(),
                title=f"商品削除依頼: {len(masters)}件",
            )
            rows = [
                ChangeRequestRow(
                    change_request=cr,
                    row_index=i + 1,
                    op=ChangeRequestRow.Op.DELETE,
                    code=str(m.product_code),
                    name=m.name,
                    is_valid=True,
                )
                for i, m in enumerate(masters)
            ]
            ChangeRequestRow.objects.bulk_create(rows)

        messages.success(request, f"削除依頼を送信しました({len(masters)}件)。")
        return redirect("mysfa:product_master", custom_id=custom_id)


class IndustryMasterIndexView(LoginRequiredMixin, View):
    template_name = "master/industry-master.html"

    def get(self, request, custom_id):
        group = get_object_or_404(
            Group, custom_id=custom_id, is_active=True, users=request.user
        )
        search = request.GET.get("search", "").strip()

        allowed_per_page = (25, 50, 100, 500)
        raw = request.GET.get("per_page", "50")
        try:
            per_page = int(raw)
        except (TypeError, ValueError):
            per_page = 50
        if per_page not in allowed_per_page:
            per_page = 50

        qs = IndustryMaster.objects.filter(group=group, is_active=True).order_by("name")
        if search:
            qs = qs.filter(name__icontains=search)

        total_count = qs.count()

        paginator = Paginator(qs, per_page)
        page = request.GET.get("page", 1)
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        masters = page_obj

        return render(
            request,
            self.template_name,
            {
                "group": group,
                "form": IndustryMasterForm(),
                "masters": masters,
                "page_obj": page_obj,
                "paginator": paginator,
                "total_count": total_count,
                "per_page": per_page,
                "allowed_per_page": allowed_per_page,
                "search": search,
            },
        )

    def post(self, request, custom_id):
        group = get_object_or_404(
            Group, custom_id=custom_id, is_active=True, users=request.user
        )
        form = IndustryMasterForm(request.POST)

        search = request.GET.get("search", "").strip()

        allowed_per_page = (25, 50, 100, 500)
        raw = request.GET.get("per_page", "50")
        try:
            per_page = int(raw)
        except (TypeError, ValueError):
            per_page = 50
        if per_page not in allowed_per_page:
            per_page = 50

        qs = IndustryMaster.objects.filter(group=group, is_active=True).order_by("name")
        if search:
            qs = qs.filter(name__icontains=search)

        total_count = qs.count()

        paginator = Paginator(qs, per_page)
        page = request.GET.get("page", 1)
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        masters = page_obj
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "group": group,
                    "form": form,
                    "masters": masters,
                    "page_obj": page_obj,
                    "paginator": paginator,
                    "total_count": total_count,
                    "per_page": per_page,
                    "allowed_per_page": allowed_per_page,
                    "search": search,
                },
            )

        name = form.cleaned_data["name"].strip()
        if IndustryMaster.objects.filter(
            group=group, name=name, is_active=True
        ).exists():
            messages.error(request, "既に登録されています。")
            return redirect("mysfa:industry_master", custom_id=custom_id)

        IndustryMaster.objects.create(group=group, name=name, is_active=True)
        messages.success(request, "業態を登録しました。")
        return redirect("mysfa:industry_master", custom_id=custom_id)


class IndustryMasterEditView(LoginRequiredMixin, View):
    template_name = "master/industry-master-edit.html"

    def get(self, request, custom_id, pk):
        group = get_object_or_404(
            Group, custom_id=custom_id, is_active=True, users=request.user
        )
        master = get_object_or_404(IndustryMaster, pk=pk, group=group, is_active=True)
        form = IndustryMasterForm(instance=master)
        return render(
            request,
            self.template_name,
            {"group": group, "master": master, "form": form},
        )

    def post(self, request, custom_id, pk):
        group = get_object_or_404(
            Group, custom_id=custom_id, is_active=True, users=request.user
        )
        master = get_object_or_404(IndustryMaster, pk=pk, group=group, is_active=True)

        form = IndustryMasterForm(request.POST, instance=master)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"group": group, "master": master, "form": form},
            )

        name = form.cleaned_data["name"].strip()
        if (
            IndustryMaster.objects.filter(group=group, name=name, is_active=True)
            .exclude(pk=master.pk)
            .exists()
        ):
            messages.error(request, "既に登録されています。")
            return redirect("mysfa:industry_master_edit", custom_id=custom_id, pk=pk)

        master.name = name
        master.save(update_fields=["name"])
        messages.success(request, "業態を更新しました。")
        return redirect("mysfa:industry_master", custom_id=custom_id)


class IndustryMasterBulkDeleteView(LoginRequiredMixin, View):
    def post(self, request, custom_id):
        group = get_object_or_404(
            Group, custom_id=custom_id, is_active=True, users=request.user
        )
        selected_ids = request.POST.getlist("selected_ids")

        if not selected_ids:
            messages.error(request, "削除する業態を選択してください。")
            return redirect("mysfa:industry_master", custom_id=custom_id)

        qs = IndustryMaster.objects.filter(
            group=group, is_active=True, id__in=selected_ids
        )
        if qs.count() != len(set(selected_ids)):
            messages.error(
                request, "選択された業態の中に、存在しないものが含まれています。"
            )
            return redirect("mysfa:industry_master", custom_id=custom_id)

        count = qs.count()
        qs.update(is_active=False)

        messages.success(request, f"業態を削除しました（{count}件）。")
        return redirect("mysfa:industry_master", custom_id=custom_id)


class CreateGroupView(LoginRequiredMixin, View):
    def get(self, request):
        form = GroupForm()
        return render(request, "group/create_group.html", {"form": form})

    def post(self, request):
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.custom_id = group.generate_unique_id()
            group.is_locked = request.POST.get("is_locked") == "on"
            group.creator = request.user
            group.save()
            request.user.groups.add(group)

            GroupMembership.objects.get_or_create(
                group=group,
                user=request.user,
                defaults={"role": GroupMembership.Role.OWNER, "is_active": True},
            )
            return redirect("mysfa:group_posts", custom_id=group.custom_id)
        return render(request, "group/create_group.html", {"form": form})


class SearchGroupView(LoginRequiredMixin, View):
    def get(self, request):
        query = (request.GET.get("q") or "").strip()
        match_mode = request.GET.get("match") or "partial"
        membership = request.GET.get("membership") or "all"
        lock_filter = request.GET.get("lock") or "all"

        groups = Group.objects.filter(is_active=True).filter(
            Q(users__isnull=False) | Q(custom_id="72014332")
        )

        if query:
            if match_mode == "exact":
                groups = groups.filter(
                    Q(name__iexact=query) | Q(custom_id__iexact=query)
                )
            else:
                match_mode = "partial"
                groups = groups.filter(
                    Q(name__icontains=query) | Q(custom_id__icontains=query)
                )

        if membership == "joined":
            groups = groups.filter(users=request.user)
        elif membership == "not_joined":
            groups = groups.exclude(users=request.user)
        else:
            membership = "all"

        if lock_filter == "locked":
            groups = groups.filter(is_locked=True)
        elif lock_filter == "open":
            groups = groups.filter(is_locked=False)
        else:
            lock_filter = "all"

        groups = groups.distinct().order_by("name", "custom_id")

        group_ids = list(groups.values_list("id", flat=True))
        requested_ids = set(
            JoinRequest.objects.filter(
                user=request.user, group_id__in=group_ids
            ).values_list("group_id", flat=True)
        )

        for group in groups:
            group.is_member = group.users.filter(pk=request.user.pk).exists()
            group.user_has_requested = group.id in requested_ids

        return render(
            request,
            "group/search_group.html",
            {
                "groups": groups,
                "query": query,
                "match_mode": match_mode,
                "membership": membership,
                "lock_filter": lock_filter,
            },
        )

    def post(self, request, custom_id):
        group = Group.objects.get(custom_id=custom_id, is_active=True)
        request.user.groups.add(group)
        GroupMembership.objects.get_or_create(
            group=group,
            user=request.user,
            defaults={"role": GroupMembership.Role.MEMBER, "is_active": True},
        )
        return redirect("mysfa:timeline")


class SearchProductsView(LoginRequiredMixin, View):
    def get(self, request):
        query = (request.GET.get("q") or "").strip()
        match_mode = request.GET.get("match") or "partial"
        start_date_raw = (request.GET.get("start_date") or "").strip()
        end_date_raw = (request.GET.get("end_date") or "").strip()

        selected_group_custom_id = (request.GET.get("group") or "").strip()
        legacy_group_pk = (request.GET.get("custom_id") or "").strip()
        category_main = (request.GET.get("category_main") or "").strip()
        category_sub = (request.GET.get("category_sub") or "").strip()

        user_groups = Group.objects.filter(users=request.user, is_active=True).order_by(
            "name", "custom_id"
        )
        page = request.GET.get("page", 1)

        category_main_options = []
        category_sub_options = []
        if selected_group_custom_id:
            g = user_groups.filter(custom_id=selected_group_custom_id).first()
            if g:
                pm = ProductMaster.objects.filter(group=g, is_active=True)
                category_main_options = list(
                    pm.exclude(category_main__isnull=True)
                    .exclude(category_main="")
                    .values_list("category_main", flat=True)
                    .distinct()
                    .order_by("category_main")
                )
                category_sub_options = list(
                    pm.exclude(category_sub__isnull=True)
                    .exclude(category_sub="")
                    .values_list("category_sub", flat=True)
                    .distinct()
                    .order_by("category_sub")
                )

        date_error = None
        start_date = None
        end_date = None
        if start_date_raw:
            try:
                start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date()
            except ValueError:
                date_error = "開始日の形式が正しくありません。"
        if end_date_raw:
            try:
                end_date = datetime.strptime(end_date_raw, "%Y-%m-%d").date()
            except ValueError:
                date_error = "終了日の形式が正しくありません。"

        if not selected_group_custom_id and legacy_group_pk:
            g = user_groups.filter(pk=legacy_group_pk).first()
            if g:
                selected_group_custom_id = g.custom_id

        do_search = bool(
            query
            or start_date
            or end_date
            or selected_group_custom_id
            or category_main
            or category_sub
        )
        posts = Post.objects.none()
        if do_search:
            posts = (
                Post.objects.filter(group__in=user_groups)
                .select_related("user", "group", "product", "industry")
                .prefetch_related("liked_users", "comments__author")
            )

            if selected_group_custom_id:
                posts = posts.filter(group__group__custom_id=selected_group_custom_id)

            if start_date:
                posts = posts.filter(created_at__date__gte=start_date)
            if end_date:
                posts = posts.filter(created_at__date__lte=end_date)

            if category_main:
                if match_mode == "exact":
                    posts = posts.filter(product__category_main__iexact=category_main)
                else:
                    posts = posts.filter(
                        product__category_main__icontains=category_main
                    )

            if category_sub:
                if match_mode == "exact":
                    posts = posts.filter(product__category_sub__iexact=category_sub)
                else:
                    posts = posts.filter(product__category_sub__icontains=category_sub)

            if query:
                if match_mode == "exact":
                    qf = Q(product__product_code__iexact=query) | Q(
                        product__name__iexact=query
                    )
                else:
                    match_mode = "partial"
                    qf = Q(product__product_code__icontains=query) | Q(
                        product__name__icontains=query
                    )
                posts = posts.filter(qf)

        paginator = Paginator(posts, 5)
        try:
            object_list = paginator.page(page)
        except PageNotAnInteger:
            object_list = paginator.page(1)
        except EmptyPage:
            object_list = paginator.page(paginator.num_pages)

        params = {}
        if query:
            params["q"] = query
        if selected_group_custom_id:
            params["group"] = selected_group_custom_id
        if match_mode and match_mode != "partial":
            params["match"] = match_mode
        if start_date_raw:
            params["start_date"] = start_date_raw
        if end_date_raw:
            params["end_date"] = end_date_raw
        if category_main:
            params["category_main"] = category_main
        if category_sub:
            params["category_sub"] = category_sub

        context = {
            "query": query,
            "object_list": object_list,
            "user_groups": user_groups,
            "selected_group_custom_id": selected_group_custom_id,
            "match_mode": match_mode,
            "start_date": start_date_raw,
            "end_date": end_date_raw,
            "category_main": category_main,
            "category_sub": category_sub,
            "category_main_options": category_main_options,
            "category_sub_options": category_sub_options,
            "date_error": date_error,
            "query_params": urlencode(params),
            "did_search": do_search,
        }
        return render(request, "post/search_products.html", context)

    def post(self, request):
        if "delete_post_id" in request.POST:
            post_id = request.POST.get("delete_post_id")
            post = get_object_or_404(Post, id=post_id, user=request.user)
            if post.image:
                post.image.delete(save=False)
            post.delete()
            messages.success(request, "投稿を削除しました。")
            next_url = (request.POST.get("next") or "").strip()
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)
            return redirect("mysfa:search_products")


class SearchCustomersView(LoginRequiredMixin, View):
    def get(self, request):
        query = (request.GET.get("q") or "").strip()
        match_mode = request.GET.get("match") or "partial"
        start_date_raw = (request.GET.get("start_date") or "").strip()
        end_date_raw = (request.GET.get("end_date") or "").strip()

        selected_group_custom_id = (request.GET.get("group") or "").strip()
        legacy_group_pk = (request.GET.get("custom_id") or "").strip()

        user_groups = Group.objects.filter(users=request.user, is_active=True).order_by(
            "name", "custom_id"
        )
        page = request.GET.get("page", 1)

        date_error = None
        start_date = None
        end_date = None
        if start_date_raw:
            try:
                start_date = datetime.strptime(start_date_raw, "%Y-%m-%d").date()
            except ValueError:
                date_error = "開始日の形式が正しくありません。"
        if end_date_raw:
            try:
                end_date = datetime.strptime(end_date_raw, "%Y-%m-%d").date()
            except ValueError:
                date_error = "終了日の形式が正しくありません。"

        if not selected_group_custom_id and legacy_group_pk:
            g = user_groups.filter(pk=legacy_group_pk).first()
            if g:
                selected_group_custom_id = g.custom_id

        do_search = bool(query or start_date or end_date)
        customers = Post.objects.none()
        if do_search:
            customers = (
                Post.objects.filter(group__in=user_groups)
                .select_related("user", "group", "product", "industry")
                .prefetch_related("liked_users", "comments__author")
            )

            if selected_group_custom_id:
                customers = customers.filter(
                    group__group__custom_id=selected_group_custom_id
                )

            if start_date:
                customers = customers.filter(created_at__date__gte=start_date)
            if end_date:
                customers = customers.filter(created_at__date__lte=end_date)

            if query:
                if match_mode == "exact":
                    customers = customers.filter(industry__name__iexact=query)
                else:
                    match_mode = "partial"
                    customers = customers.filter(industry__name__icontains=query)

        paginator = Paginator(customers, 5)
        try:
            object_list = paginator.page(page)
        except PageNotAnInteger:
            object_list = paginator.page(1)
        except EmptyPage:
            object_list = paginator.page(paginator.num_pages)

        params = {}
        if query:
            params["q"] = query
        if selected_group_custom_id:
            params["group"] = selected_group_custom_id
        if match_mode and match_mode != "partial":
            params["match"] = match_mode
        if start_date_raw:
            params["start_date"] = start_date_raw
        if end_date_raw:
            params["end_date"] = end_date_raw

        context = {
            "query": query,
            "object_list": object_list,
            "user_groups": user_groups,
            "selected_group_custom_id": selected_group_custom_id,
            "match_mode": match_mode,
            "start_date": start_date_raw,
            "end_date": end_date_raw,
            "date_error": date_error,
            "query_params": urlencode(params),
            "did_search": do_search,
        }
        return render(request, "post/search_customers.html", context)

    def post(self, request):
        if "delete_post_id" in request.POST:
            post_id = request.POST.get("delete_post_id")
            post = get_object_or_404(Post, id=post_id, user=request.user)
            if post.image:
                post.image.delete(save=False)
            post.delete()
            messages.success(request, "投稿を削除しました。")
            next_url = (request.POST.get("next") or "").strip()
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)
            return redirect("mysfa:search_customers")


class SearchUsersView(LoginRequiredMixin, View):
    def get(self, request):
        query = (request.GET.get("q") or "").strip()
        match_mode = request.GET.get("match") or "partial"
        selected_group_custom_id = (request.GET.get("group") or "").strip()
        page = request.GET.get("page", 1)

        user_groups = Group.objects.filter(users=request.user, is_active=True).order_by(
            "name", "custom_id"
        )
        if (
            selected_group_custom_id
            and not user_groups.filter(custom_id=selected_group_custom_id).exists()
        ):
            selected_group_custom_id = ""

        do_search = bool(query or selected_group_custom_id)
        users = CustomUser.objects.none()
        if do_search:
            users = CustomUser.objects.all()

            if selected_group_custom_id:
                users = users.filter(
                    user_groups__custom_id=selected_group_custom_id,
                    user_groups__is_active=True,
                )

            if query:
                if match_mode == "exact":
                    users = users.filter(
                        Q(username__iexact=query) | Q(custom_user_id__iexact=query)
                    )
                else:
                    match_mode = "partial"
                    users = users.filter(
                        Q(username__icontains=query)
                        | Q(custom_user_id__icontains=query)
                    )

            users = users.distinct().order_by("username", "custom_user_id")

        paginator = Paginator(users, 10)
        try:
            object_list = paginator.page(page)
        except PageNotAnInteger:
            object_list = paginator.page(1)
        except EmptyPage:
            object_list = paginator.page(paginator.num_pages)

        params = {}
        if query:
            params["q"] = query
        if selected_group_custom_id:
            params["group"] = selected_group_custom_id
        if match_mode and match_mode != "partial":
            params["match"] = match_mode

        context = {
            "query": query,
            "object_list": object_list,
            "user_groups": user_groups,
            "selected_group_custom_id": selected_group_custom_id,
            "match_mode": match_mode,
            "query_params": urlencode(params),
            "did_search": do_search,
        }
        return render(request, "post/search_users.html", context)


@method_decorator(login_required, name="dispatch")
class LikePostView(View):
    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)

        with transaction.atomic():
            already_liked = post.liked_users.filter(pk=request.user.pk).exists()
            if already_liked:
                post.liked_users.remove(request.user)
                post.likes_count = max(0, post.likes_count - 1)
                liked = False
            else:
                post.liked_users.add(request.user)
                post.likes_count += 1
                liked = True

            post.save(update_fields=["likes_count"])

        return JsonResponse({"liked": liked, "likes_count": post.likes_count})


@method_decorator(login_required, name="dispatch")
class PostCommentCreateView(View):
    def post(self, request, post_id: int):
        post = get_object_or_404(Post, id=post_id)

        # 投稿が所属グループ外のユーザーからコメントされないようにする
        is_member = Group.objects.filter(
            id=post.group_id,
            is_active=True,
            users=request.user,
        ).exists()
        if not is_member:
            raise PermissionDenied

        form = PostCommentForm(request.POST)
        if not form.is_valid():
            messages.error(request, "コメント内容を入力してください。")
            next_url = (
                request.GET.get("next")
                or request.META.get("HTTP_REFERER")
                or reverse("mysfa:timeline")
            )
            return redirect(next_url)

        PostComment.objects.create(
            post=post,
            author=request.user,
            body=form.cleaned_data["body"],
        )
        messages.success(request, "コメントしました。")

        next_url = (
            request.GET.get("next")
            or request.META.get("HTTP_REFERER")
            or reverse("mysfa:timeline")
        )
        return redirect(next_url)


@method_decorator(login_required, name="dispatch")
class PostCommentDeleteView(View):
    def post(self, request, post_id: int, comment_id: int):
        comment = get_object_or_404(
            PostComment.objects.select_related("post", "author"),
            id=comment_id,
            post_id=post_id,
        )
        post = comment.post

        is_member = Group.objects.filter(
            id=post.group_id,
            is_active=True,
            users=request.user,
        ).exists()
        if not is_member:
            raise PermissionDenied

        if request.user != post.user and request.user != comment.author:
            raise PermissionDenied

        comment.delete()
        messages.success(request, "コメントを削除しました。")

        next_url = (
            request.GET.get("next")
            or request.META.get("HTTP_REFERER")
            or reverse("mysfa:timeline")
        )
        return redirect(next_url)


@method_decorator(login_required, name="dispatch")
class SalesReportView(LoginRequiredMixin, View):
    def get(self, request, user_id=None, group_id=None):
        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")
        selected_group_id = request.GET.get("custom_id")
        report_status_raw = (request.GET.get("report_status") or "").strip()
        status_fallback = (request.GET.get("status") or "").strip()
        report_sort = (request.GET.get("report_sort") or "").strip()
        report_top_n_raw = (request.GET.get("report_top_n") or "").strip()

        if not start_date_str or not end_date_str:
            return JsonResponse({"error": "開始日と終了日が必要です"}, status=400)

        def _parse_date(s: str):
            for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
                try:
                    return datetime.strptime(s, fmt).date()
                except ValueError:
                    continue
            raise ValueError("invalid date format")

        try:
            start_date = _parse_date(start_date_str)
            end_date = _parse_date(end_date_str)
        except ValueError:
            return JsonResponse({"error": "日付形式が正しくありません"}, status=400)

        if group_id:
            try:
                group = Group.objects.get(custom_id=group_id, is_active=True)
                is_member = group.users.filter(pk=request.user.pk).exists()
                if group.is_locked and not is_member:
                    return JsonResponse({"error": "権限がありません"}, status=403)
                posts = Post.objects.filter(
                    group=group,
                    created_at__date__gte=start_date,
                    created_at__date__lte=end_date,
                ).select_related("product", "industry")
            except Group.DoesNotExist:
                return JsonResponse({"error": "グループが見つかりません"}, status=404)
        else:
            try:
                user = CustomUser.objects.get(custom_user_id=user_id)

                if selected_group_id:
                    try:
                        selected_group = Group.objects.get(
                            custom_id=selected_group_id,
                            is_active=True,
                            users=user,
                        )
                        posts = Post.objects.filter(
                            user=user,
                            group=selected_group,
                            created_at__date__gte=start_date,
                            created_at__date__lte=end_date,
                        ).select_related("product", "industry")
                    except Group.DoesNotExist:
                        return JsonResponse(
                            {"error": "選択されたグループが見つかりません"}, status=404
                        )
                else:
                    user_groups = Group.objects.filter(users=user, is_active=True)
                    posts = Post.objects.filter(
                        user=user,
                        group__in=user_groups,
                        created_at__date__gte=start_date,
                        created_at__date__lte=end_date,
                    ).select_related("product", "industry")

            except CustomUser.DoesNotExist:
                return JsonResponse({"error": "ユーザーが見つかりません"}, status=404)

        allowed_statuses = {s for s, _label in Post.Status.choices}
        effective_status = report_status_raw or status_fallback
        if effective_status == "all":
            pass
        elif effective_status and effective_status in allowed_statuses:
            posts = posts.filter(status=effective_status)
        else:
            posts = posts.filter(status__in=[Post.Status.ADOPTED])

        try:
            report_top_n = int(report_top_n_raw) if report_top_n_raw else 5
        except (TypeError, ValueError):
            report_top_n = 5
        report_top_n = max(3, min(report_top_n, 20))

        product_qs = (
            posts.filter(product__isnull=False)
            .values("product__product_code", "product__name")
            .annotate(
                count=Count("id"),
                last_created_at=Max("created_at"),
            )
            .order_by()
        )
        customer_qs = (
            posts.filter(industry__isnull=False)
            .values("industry__name")
            .annotate(
                count=Count("id"),
                last_created_at=Max("created_at"),
            )
            .order_by()
        )

        if report_sort == "new":
            product_qs = product_qs.order_by(
                "-last_created_at",
                "-count",
                "product__product_code",
                "product__name",
            )
            customer_qs = customer_qs.order_by(
                "-last_created_at",
                "-count",
                "industry__name",
            )
        elif report_sort == "old":
            product_qs = product_qs.order_by(
                "last_created_at",
                "-count",
                "product__product_code",
                "product__name",
            )
            customer_qs = customer_qs.order_by(
                "last_created_at",
                "-count",
                "industry__name",
            )
        else:
            product_qs = product_qs.order_by(
                "-count",
                "-last_created_at",
                "product__product_code",
                "product__name",
            )
            customer_qs = customer_qs.order_by(
                "-count",
                "-last_created_at",
                "industry__name",
            )

        product_rows = list(product_qs)
        customer_rows = list(customer_qs)

        product_breakdown = [
            {
                "product_name": x["product__name"],
                "product_code": x["product__product_code"],
                "label": x["product__name"],
                "count": x["count"],
                "last_created_at": (
                    x["last_created_at"].isoformat()
                    if x.get("last_created_at")
                    else None
                ),
            }
            for x in product_rows
        ]
        customer_breakdown = [
            {
                "customer_category": x["industry__name"],
                "count": x["count"],
                "last_created_at": (
                    x["last_created_at"].isoformat()
                    if x.get("last_created_at")
                    else None
                ),
            }
            for x in customer_rows
        ]

        top_products = product_breakdown[:report_top_n]
        other_products = product_breakdown[report_top_n:]
        other_product_count = sum(item["count"] for item in other_products)
        if other_product_count > 0:
            top_products = top_products + [
                {
                    "product_name": "その他",
                    "product_code": "",
                    "label": "その他",
                    "count": other_product_count,
                    "last_created_at": max(
                        (
                            item["last_created_at"]
                            for item in other_products
                            if item.get("last_created_at")
                        ),
                        default=None,
                    ),
                }
            ]

        top_customers = customer_breakdown[:report_top_n]
        other_customers = customer_breakdown[report_top_n:]
        other_customer_count = sum(item["count"] for item in other_customers)
        if other_customer_count > 0:
            top_customers = top_customers + [
                {
                    "customer_category": "その他",
                    "count": other_customer_count,
                    "last_created_at": max(
                        (
                            item["last_created_at"]
                            for item in other_customers
                            if item.get("last_created_at")
                        ),
                        default=None,
                    ),
                }
            ]

        response_data = {
            "product_data": top_products,
            "customer_data": top_customers,
            "product_other_breakdown": other_products,
            "customer_other_breakdown": other_customers,
            "report_top_n": report_top_n,
            "start_date": start_date_str,
            "end_date": end_date_str,
            "total_posts": posts.count(),
        }
        return JsonResponse(response_data)
