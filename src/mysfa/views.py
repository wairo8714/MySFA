import csv
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView

from accounts.models import CustomUser

from .forms import (
    GroupForm,
    ProductMasterForm,
    IndustryMasterForm,
    PostForm, 
    UserProfileForm,
)
from .models import (
    ChangeRequest,
    ChangeRequestRow,
    Group,
    JoinRequest,
    Post,
    ProductMaster,
    IndustryMaster,
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
    """
    Returns:
      {
        ok_count: int,
        error_count: int,
        total_count: int,
        errors: [{row: int, message: str}],
        rows: [payload dict ...]  # only valid rows
      }
    """
    import io
    import unicodedata

    raw = file_obj.read()

    def _decode_bytes(b: bytes) -> str:
        # まずUTF-8（BOM含む）を試し、それがダメならExcelで多いCP932を試す
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
            "errors": [{"row": 1, "message": "CSVが空です。テンプレートCSVを再ダウンロードして使用してください。"}],
            "rows": [],
        }

    def _norm(s: str) -> str:
        return unicodedata.normalize("NFKC", (s or "")).strip().replace("\ufeff", "")

    header_norm = [_norm(h) for h in header_row]
    expected_norm = [_norm(h) for h in PRODUCT_CSV_HEADERS]

    if header_norm[: len(expected_norm)] != expected_norm or any(h != "" for h in header_norm[len(expected_norm) :]):
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
    reader = (dict(zip(headers, (row + [""] * len(headers))[: len(headers)])) for row in csv_reader)

    errors = []
    valid_payloads = []
    seen_codes = set()
    total = 0

    for i, row in enumerate(reader, start=2):  # 2行目からデータ
        # 空行スキップ（全列が空）
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
            errors.append({"row": i, "message": f"商品コードがCSV内で重複しています: {code}"})
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
            errors.append({"row": i, "message": "自由項目（数値1）は整数で入力してください。"})
            continue
        try:
            payload["custom_int_2"] = _parse_csv_int(row.get("自由項目（数値2）"))
        except (ValueError, TypeError):
            errors.append({"row": i, "message": "自由項目（数値2）は整数で入力してください。"})
            continue

        
        try:
            d = _parse_csv_date(row.get("自由項目（日付1）"))
            payload["custom_date_1"] = d or None
        except ValueError:
            errors.append({"row": i, "message": "自由項目（日付1）は YYYY-MM-DD もしくは YYYY/MM/DD で入力してください。"})
            continue

        valid_payloads.append(payload)

    codes = [p["product_code"] for p in valid_payloads]
    if codes:
        active_exists = set(
            ProductMaster.objects.filter(group=group, is_active=True, product_code__in=codes).values_list(
                "product_code", flat=True
            )
        )
        if active_exists:
            # codesに紐付く各行にエラー付け
            for idx, p in enumerate(valid_payloads):
                if p["product_code"] in active_exists:
                    errors.append({"row": 0, "message": f"既に登録済みの商品コードが含まれています（追加のみ）: {p['product_code']}"})
            valid_payloads = [p for p in valid_payloads if p["product_code"] not in active_exists]

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
                    errors.append({"row": 0, "message": f"承認待ちの申請が既に存在する商品コードが含まれています: {p['product_code']}"})
            valid_payloads = [p for p in valid_payloads if p["product_code"] not in pending_codes]

    return {
        "ok_count": len(valid_payloads),
        "error_count": len(errors),
        "total_count": total,
        "errors": errors[:30],  # 画面には最大30件
        "rows": valid_payloads,
    }


def _transfer_creator_or_archive(group):
    members = group.users.order_by("custom_user_id")
    if members.exists():
        group.creator = members.first()
        group.is_active = True
        group.save(update_fields=["creator", "is_active"])
        return

    group.creator = None
    group.is_active = False
    group.save(update_fields=["creator", "is_active"])


class Timeline(LoginRequiredMixin, ListView):
    model = Post
    template_name = "post/timeline.html"
    context_object_name = "object_list"
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        custom_id = self.request.GET.get("custom_id")
        user_groups = Group.objects.filter(users=user, is_active=True)

        if custom_id:
            group = get_object_or_404(Group, custom_id=custom_id, users=user, is_active=True)
            queryset = Post.objects.filter(group=group).distinct()
        else:
            queryset = Post.objects.filter(group__in=user_groups).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        custom_id = self.request.GET.get("custom_id")
        context["user_groups"] = Group.objects.filter(users=self.request.user, is_active=True)
        context["selected_group_id"] = custom_id
        context["form"] = PostForm(user=self.request.user)

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

            base = reverse("mysfa:timeline")
            if custom_id:
                return redirect(f"{base}?custom_id={custom_id}")
            return redirect(base)

        form = PostForm(request.POST, request.FILES, user=request.user)

        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            if not post.group:
                last_group = Group.objects.filter(users=request.user, is_active=True).last()
                if last_group:
                    post.group = last_group
            if "image" in request.FILES:
                post.image = request.FILES["image"]
            post.save()

            base = reverse("mysfa:timeline")
            if custom_id:
                return redirect(f"{base}?custom_id={custom_id}")
            return redirect(base)

        self.object_list = self.get_queryset()
        context = self.get_context_data()
        context["form"] = form
        context["selected_group_id"] = custom_id
        return self.render_to_response(context)


class MyPost(LoginRequiredMixin, ListView):
    model = Post
    template_name = "post/mypost.html"
    context_object_name = "posts"
    paginate_by = 10

    def get_queryset(self):
        custom_user_id = self.kwargs["custom_user_id"]
        user = get_object_or_404(CustomUser, custom_user_id=custom_user_id)
        queryset = Post.objects.filter(user=user)

        custom_id = self.request.GET.get("custom_id")
        if custom_id:
            try:
                group = Group.objects.get(custom_id=custom_id, is_active=True)
                queryset = queryset.filter(group=group)
            except Group.DoesNotExist:
                queryset = Post.objects.none()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        custom_user_id = self.kwargs["custom_user_id"]
        context["displayed_user"] = get_object_or_404(CustomUser, custom_user_id=custom_user_id)
        context["current_user"] = self.request.user
        context["form"] = UserProfileForm(instance=self.request.user)

        from django.conf import settings

        context["MEDIA_URL"] = settings.MEDIA_URL

        user_groups = Group.objects.filter(users=context["displayed_user"], is_active=True)
        context["user_groups"] = user_groups

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
        if "delete_post_id" in request.POST:
            post_id = request.POST.get("delete_post_id")
            post = get_object_or_404(Post, id=post_id, user=request.user)
            if post.image:
                post.image.delete(save=False)
            post.delete()
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
        group = get_object_or_404(Group, custom_id=self.kwargs["custom_id"], is_active=True)
        return Post.objects.filter(group=group).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = get_object_or_404(Group, custom_id=self.kwargs["custom_id"], is_active=True)
        user = self.request.user
        creator = group.creator
        members = group.users.all()

        context["group"] = group
        context["is_member"] = group.users.filter(pk=user.pk).exists()
        context["creator"] = creator
        context["members"] = members
        context["member_count"] = members.count()
        context["user_has_requested"] = JoinRequest.objects.filter(user=user, group=group).exists()
        context["join_requests"] = JoinRequest.objects.filter(group=group)

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
        if "delete_post_id" in request.POST:
            post_id = request.POST.get("delete_post_id")
            post = get_object_or_404(Post, id=post_id, user=request.user)
            if post.image:
                post.image.delete(save=False)
            post.delete()
            return redirect("mysfa:group_posts", custom_id=self.kwargs["custom_id"])

        return self.get(request, *args, **kwargs)


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
        if request.user in group.users.all():
            group.is_locked = not group.is_locked
            group.save()
        return redirect("mysfa:group_posts", custom_id=group.custom_id)


class JoinGroupView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs["custom_id"], is_active=True)
        request.user.groups.add(group)
        group.users.add(request.user)
        return redirect("mysfa:group_posts", custom_id=kwargs["custom_id"])


class JoinGroupRequestView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs["custom_id"], is_active=True)

        if request.user in group.users.all():
            return redirect("mysfa:group_posts", custom_id=group.custom_id)

        if group.is_locked:
            if not JoinRequest.objects.filter(user=request.user, group=group).exists():
                JoinRequest.objects.create(user=request.user, group=group)
            return redirect("mysfa:group_posts", custom_id=group.custom_id)

        request.user.groups.add(group)
        group.users.add(request.user)
        return redirect("mysfa:group_posts", custom_id=group.custom_id)


class ApproveJoinRequestView(View):
    def post(self, request, custom_id, request_id):
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True)
        join_request = get_object_or_404(JoinRequest, user__custom_user_id=request_id, group=group)
        group.users.add(join_request.user)
        join_request.delete()
        return redirect("mysfa:group_posts", custom_id=custom_id)


class RejectJoinRequestView(View):
    def post(self, request, custom_id, request_id):
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True)
        join_request = get_object_or_404(JoinRequest, user__custom_user_id=request_id, group=group)
        join_request.delete()
        return redirect("mysfa:group_posts", custom_id=custom_id)


class LeaveGroupView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs["custom_id"], is_active=True)
        was_creator = group.creator_id == request.user.pk
        request.user.groups.remove(group)
        group.users.remove(request.user)

        if was_creator or group.users.count() == 0:
            _transfer_creator_or_archive(group)

        return redirect("home")


class DeleteGroupView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs["custom_id"], is_active=True)
        if request.user != group.creator:
            return HttpResponseForbidden("グループの作成者のみ削除を行うことができます。")
        group.is_active = False
        group.save(update_fields=["is_active"])
        return redirect("home")


class RemoveMemberView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs["custom_id"], is_active=True)
        user_to_remove = get_object_or_404(CustomUser, custom_user_id=kwargs["custom_user_id"])

        if request.user == group.creator and user_to_remove in group.users.all():
            group.users.remove(user_to_remove)
            messages.success(request, f"{user_to_remove.username}をグループから退会させました。")
        else:
            messages.error(request, "この操作を行う権限がありません。")

        return redirect("mysfa:group_posts", custom_id=kwargs["custom_id"])


class ProductMasterIndexView(LoginRequiredMixin, View):
    template_name = "master/product-master.html"

    def get(self, request, custom_id):
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True, users=request.user)

        search = request.GET.get("search", "").strip()

        allowed_per_page = (25, 50, 100, 500)
        raw = request.GET.get("per_page", "50")
        try:
            per_page = int(raw)
        except (TypeError, ValueError):
            per_page = 50
        if per_page not in allowed_per_page:
            per_page = 50

        qs = ProductMaster.objects.filter(group=group, is_active=True).order_by("product_code")
        if search:
            qs = qs.filter(Q(product_code__icontains=search) | Q(name__icontains=search))

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
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True, users=request.user)

        form = ProductMasterForm(request.POST)
        if form.is_valid():
            product_code = form.cleaned_data["product_code"]
            existing = ProductMaster.objects.filter(group=group, product_code=product_code).first()

            payload = {field: form.cleaned_data.get(field) for field in form.Meta.fields}
            payload["product_code"] = product_code

            with transaction.atomic():
                title_prefix = "商品更新申請" if existing else "商品追加申請"
                cr = ChangeRequest.objects.create(
                    group=group,
                    kind=ChangeRequest.Kind.PRODUCT,
                    status=ChangeRequest.Status.PENDING,
                    requester=request.user,
                    submitted_at=timezone.now(),
                    title=f"{title_prefix}: {product_code} {payload.get('name','')}",
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

            messages.success(request, "変更申請を送信しました（承認後に反映されます）。")
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

        qs = ProductMaster.objects.filter(group=group, is_active=True).order_by("product_code")
        if search:
            qs = qs.filter(Q(product_code__icontains=search) | Q(name__icontains=search))

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
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True, users=request.user)
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
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True, users=request.user)
        master = get_object_or_404(ProductMaster, pk=pk, group=group)

        form = ProductMasterForm(request.POST, instance=master)
        if "product_code" in form.fields:
            form.fields["product_code"].disabled = True
        if form.is_valid():
            product_code = master.product_code
            payload = {field: form.cleaned_data.get(field) for field in form.Meta.fields}
            payload["product_code"] = product_code
            payload["_target_pk"] = master.pk

            with transaction.atomic():
                cr = ChangeRequest.objects.create(
                    group=group,
                    kind=ChangeRequest.Kind.PRODUCT,
                    status=ChangeRequest.Status.PENDING,
                    requester=request.user,
                    submitted_at=timezone.now(),
                    title=f"商品更新申請: {product_code} {payload.get('name','')}",
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

            messages.success(request, "変更申請を送信しました（承認後に反映されます）。")
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
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True, users=request.user)

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
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True, users=request.user)
        f = request.FILES.get("file")
        if not f:
            return JsonResponse({"ok": False, "message": "CSVファイルを選択してください。"}, status=400)

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
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True, users=request.user)
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


class ProductDeleteRequestCreateView(LoginRequiredMixin, View):
    template_name = "master/product-delete-request.html"

    def get(self, request, custom_id, pk):
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True, users=request.user)
        master = get_object_or_404(ProductMaster, pk=pk, group=group, is_active=True)

        already_requested = ChangeRequestRow.objects.filter(
            change_request__group=group,
            change_request__kind=ChangeRequest.Kind.PRODUCT,
            change_request__status=ChangeRequest.Status.PENDING,
            op=ChangeRequestRow.Op.DELETE,
            code=str(master.product_code),
        ).exists()

        return render(
            request,
            self.template_name,
            {
                "group": group,
                "master": master,
                "already_requested": already_requested,
            },
        )

    def post(self, request, custom_id, pk):
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True, users=request.user)
        master = get_object_or_404(ProductMaster, pk=pk, group=group, is_active=True)

        exists = ChangeRequestRow.objects.filter(
            change_request__group=group,
            change_request__kind=ChangeRequest.Kind.PRODUCT,
            change_request__status=ChangeRequest.Status.PENDING,
            op=ChangeRequestRow.Op.DELETE,
            code=str(master.product_code),
        ).exists()
        if exists:
            messages.info(request, "この商品はすでに削除依頼中です。")
            return redirect("mysfa:product_master", custom_id=custom_id)

        with transaction.atomic():
            cr = ChangeRequest.objects.create(
                group=group,
                kind=ChangeRequest.Kind.PRODUCT,
                status=ChangeRequest.Status.PENDING,
                requester=request.user,
                submitted_at=timezone.now(),
                title=f"商品削除依頼: {master.product_code} {master.name}",
            )
            ChangeRequestRow.objects.create(
                change_request=cr,
                row_index=1,
                op=ChangeRequestRow.Op.DELETE,
                code=str(master.product_code),
                name=master.name,
                is_valid=True,
            )

        messages.success(request, "削除依頼を送信しました。")
        return redirect("mysfa:product_master", custom_id=custom_id)


class ProductChangeRequestInboxView(LoginRequiredMixin, View):
    template_name = "master/product-change-requests.html"

    def get(self, request, custom_id):
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True, users=request.user)
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

        return render(request, self.template_name, {"group": group, "requests": requests_qs})


class ProductChangeRequestDecideView(LoginRequiredMixin, View):
    def post(self, request, custom_id, cr_id):
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True, users=request.user)
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
                        ProductMaster.objects.filter(group=group, product_code=row.code).update(is_active=False)
                        continue

                    if row.op == ChangeRequestRow.Op.UPSERT:
                        data = row.diff_json or {}
                        code = str(row.code)
                        obj = ProductMaster.objects.filter(group=group, product_code=code).first()
                        if not obj:
                            obj = ProductMaster(group=group, product_code=code)

                        # apply payload (ignore unknown keys)
                        for key, value in data.items():
                            if key in ("_target_pk", "group", "is_active", "created_at", "updated_at"):
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
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True, users=request.user)

        selected_ids = request.POST.getlist("selected_ids")
        if not selected_ids:
            messages.error(request, "削除する商品を選択してください。")
            return redirect("mysfa:product_master", custom_id=custom_id)

        masters_qs = (
            ProductMaster.objects.filter(group=group, is_active=True, id__in=selected_ids)
            .order_by("product_code")
        )
        masters = list(masters_qs)

        if len(masters) != len(set(selected_ids)):
            messages.error(request, "選択された商品の中に、存在しない商品または無効な商品があります。")
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
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True, users=request.user)
        masters = IndustryMaster.objects.filter(group=group, is_active=True).order_by("name")
        return render(request, self.template_name, {"group": group, "form": IndustryMasterForm(), "masters": masters})

    def post(self, request, custom_id):
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True, users=request.user)
        form = IndustryMasterForm(request.POST)

        masters = IndustryMaster.objects.filter(group=group, is_active=True).order_by("name")
        if not form.is_valid():
            return render(request, self.template_name, {"group": group, "form": form, "masters": masters})

        name = form.cleaned_data["name"].strip()
        if IndustryMaster.objects.filter(group=group, name=name, is_active=True).exists():
            messages.error(request, "既に登録されています。")
            return redirect("mysfa:industry_master", custom_id=custom_id)

        IndustryMaster.objects.create(group=group, name=name, is_active=True)
        messages.success(request, "業態を登録しました。")
        return redirect("mysfa:industry_master", custom_id=custom_id)


class IndustryMasterEditView(LoginRequiredMixin, View):
    template_name = "master/industry-master-edit.html"

    def get(self, request, custom_id, pk):
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True, users=request.user)
        master = get_object_or_404(IndustryMaster, pk=pk, group=group, is_active=True)
        form = IndustryMasterForm(instance=master)
        return render(request, self.template_name, {"group": group, "master": master, "form": form})

    def post(self, request, custom_id, pk):
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True, users=request.user)
        master = get_object_or_404(IndustryMaster, pk=pk, group=group, is_active=True)

        form = IndustryMasterForm(request.POST, instance=master)
        if not form.is_valid():
            return render(request, self.template_name, {"group": group, "master": master, "form": form})

        name = form.cleaned_data["name"].strip()
        if IndustryMaster.objects.filter(group=group, name=name, is_active=True).exclude(pk=master.pk).exists():
            messages.error(request, "既に登録されています。")
            return redirect("mysfa:industry_master_edit", custom_id=custom_id, pk=pk)

        master.name = name
        master.save(update_fields=["name"])
        messages.success(request, "業態を更新しました。")
        return redirect("mysfa:industry_master", custom_id=custom_id)


class IndustryMasterDeleteView(LoginRequiredMixin, View):
    def post(self, request, custom_id, pk):
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True, users=request.user)
        master = get_object_or_404(IndustryMaster, pk=pk, group=group, is_active=True)

        master.is_active = False
        master.save(update_fields=["is_active"])

        messages.success(request, "業態を削除しました。")
        return redirect("mysfa:industry_master", custom_id=custom_id)


class IndustryMasterBulkDeleteView(LoginRequiredMixin, View):
    def post(self, request, custom_id):
        group = get_object_or_404(Group, custom_id=custom_id, is_active=True, users=request.user)
        selected_ids = request.POST.getlist("selected_ids")

        if not selected_ids:
            messages.error(request, "削除する業態を選択してください。")
            return redirect("mysfa:industry_master", custom_id=custom_id)

        qs = IndustryMaster.objects.filter(group=group, is_active=True, id__in=selected_ids)
        if qs.count() != len(set(selected_ids)):
            messages.error(request, "選択された業態の中に、存在しないものが含まれています。")
            return redirect("mysfa:industry_master", custom_id=custom_id)

        count = qs.count()
        qs.update(is_active=False)

        messages.success(request, f"業態を削除しました（{count}件）。")
        return redirect("mysfa:industry_master", custom_id=custom_id)
            
        
class CreateGroupView(View):
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
            group.users.add(request.user)
            request.user.groups.add(group)
            return redirect("mysfa:group_posts", custom_id=group.custom_id)
        return render(request, "group/create_group.html", {"form": form})


class SearchGroupView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get("q", "")
        groups = Group.objects.filter(name__icontains=query, is_active=True)
        for group in groups:
            group.is_member = group.users.filter(custom_user_id=request.user.custom_user_id).exists()
        return render(request, "group/search_group.html", {"groups": groups, "query": query})

    def post(self, request, custom_id):
        group = Group.objects.get(custom_id=custom_id, is_active=True)
        request.user.groups.add(group)
        group.users.add(request.user)
        return redirect("mysfa:timeline")


class SearchProductsView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get("q", "")
        selected_group_id = request.GET.get("custom_id")
        user_groups = request.user.groups.all()
        page = request.GET.get("page", 1)

        if query:
            if selected_group_id:
                posts = Post.objects.filter(
                    product_name__icontains=query,
                    group__id=selected_group_id,
                    group__in=user_groups,
                )
            else:
                posts = Post.objects.filter(product_name__icontains=query, group__in=user_groups)
        else:
            posts = []

        paginator = Paginator(posts, 5)
        try:
            object_list = paginator.page(page)
        except PageNotAnInteger:
            object_list = paginator.page(1)
        except EmptyPage:
            object_list = paginator.page(paginator.num_pages)

        context = {
            "query": query,
            "object_list": object_list,
            "user_groups": user_groups,
            "selected_group_id": selected_group_id,
        }
        return render(request, "post/search_products.html", context)

    def post(self, request):
        if "delete_post_id" in request.POST:
            post_id = request.POST.get("delete_post_id")
            post = get_object_or_404(Post, id=post_id, user=request.user)
            if post.image:
                post.image.delete(save=False)
            post.delete()
            return redirect("mysfa:search_products")


class SearchCustomersView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get("q", "")
        selected_group_id = request.GET.get("custom_id")
        user_groups = request.user.groups.all()
        page = request.GET.get("page", 1)

        if query:
            if selected_group_id:
                customers = Post.objects.filter(
                    customer_category__icontains=query,
                    group__id=selected_group_id,
                    group__in=user_groups,
                )
            else:
                customers = Post.objects.filter(customer_category__icontains=query, group__in=user_groups)
        else:
            customers = []

        paginator = Paginator(customers, 5)
        try:
            object_list = paginator.page(page)
        except PageNotAnInteger:
            object_list = paginator.page(1)
        except EmptyPage:
            object_list = paginator.page(paginator.num_pages)

        context = {
            "query": query,
            "object_list": object_list,
            "user_groups": user_groups,
            "selected_group_id": selected_group_id,
        }
        return render(request, "post/search_customers.html", context)

    def post(self, request):
        if "delete_post_id" in request.POST:
            post_id = request.POST.get("delete_post_id")
            post = get_object_or_404(Post, id=post_id, user=request.user)
            if post.image:
                post.image.delete(save=False)
            post.delete()
            return redirect("mysfa:search_customers")


class SearchUsersView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get("q", "")
        page = request.GET.get("page", 1)

        if query:
            users = CustomUser.objects.filter(Q(username__icontains=query) | Q(custom_user_id__icontains=query))
        else:
            users = CustomUser.objects.none()

        paginator = Paginator(users, 10)
        try:
            object_list = paginator.page(page)
        except PageNotAnInteger:
            object_list = paginator.page(1)
        except EmptyPage:
            object_list = paginator.page(paginator.num_pages)

        context = {
            "query": query,
            "object_list": object_list,
        }
        return render(request, "post/search_users.html", context)


@method_decorator(login_required, name="dispatch")
class LikePostView(View):
    def post(self, request, post_id):
        try:
            post = get_object_or_404(Post, id=post_id)

            if request.user in post.liked_users.all():
                post.liked_users.remove(request.user)
                post.likes_count -= 1
                status = "unliked"
            else:
                post.liked_users.add(request.user)
                post.likes_count += 1
                status = "liked"

            post.save()

            return JsonResponse(
                {
                    "status": status,
                    "count": post.likes_count,
                    "message": f"Post {status} successfully",
                }
            )

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


@method_decorator(login_required, name="dispatch")
class SalesReportView(View):
    def get(self, request, user_id=None, group_id=None):
        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")
        selected_group_id = request.GET.get("custom_id")

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
                posts = Post.objects.filter(
                    group=group,
                    created_at__date__gte=start_date,
                    created_at__date__lte=end_date,
                )
            except Group.DoesNotExist:
                return JsonResponse({"error": "グループが見つかりません"}, status=404)
        else:
            try:
                user = CustomUser.objects.get(custom_user_id=user_id)

                if selected_group_id:
                    try:
                        selected_group = Group.objects.get(custom_id=selected_group_id, is_active=True)
                        posts = Post.objects.filter(
                            user=user,
                            group=selected_group,
                            created_at__date__gte=start_date,
                            created_at__date__lte=end_date,
                        )
                    except Group.DoesNotExist:
                        return JsonResponse({"error": "選択されたグループが見つかりません"}, status=404)
                else:
                    user_groups = Group.objects.filter(users=user, is_active=True)
                    posts = Post.objects.filter(
                        group__in=user_groups,
                        created_at__date__gte=start_date,
                        created_at__date__lte=end_date,
                    )

            except CustomUser.DoesNotExist:
                return JsonResponse({"error": "ユーザーが見つかりません"}, status=404)

        product_counts = {}
        customer_counts = {}

        for post in posts:
            if post.product_name:
                product_counts[post.product_name] = product_counts.get(post.product_name, 0) + 1

            if post.customer_category:
                customer_counts[post.customer_category] = customer_counts.get(post.customer_category, 0) + 1

        product_data = [{"product_name": name, "count": count} for name, count in product_counts.items()]
        customer_data = [{"customer_category": category, "count": count} for category, count in customer_counts.items()]

        product_data.sort(key=lambda x: x["count"], reverse=True)
        customer_data.sort(key=lambda x: x["count"], reverse=True)

        if len(product_data) > 5:
            top_products = product_data[:5]
            other_count = sum(item["count"] for item in product_data[5:])
            if other_count > 0:
                top_products.append({"product_name": "その他", "count": other_count})
            product_data = top_products

        if len(customer_data) > 5:
            top_customers = customer_data[:5]
            other_count = sum(item["count"] for item in customer_data[5:])
            if other_count > 0:
                top_customers.append({"customer_category": "その他", "count": other_count})
            customer_data = top_customers

        response_data = {
            "product_data": product_data,
            "customer_data": customer_data,
            "start_date": start_date_str,
            "end_date": end_date_str,
            "total_posts": posts.count(),
        }
        return JsonResponse(response_data)
