import logging
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import check_password, make_password
from django.core.files import File
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View, generic

from .forms import CustomUserCreationForm
from .models import CustomUser

logger = logging.getLogger(__name__)


class SignUpView(generic.CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"

    def form_valid(self, form):
        if form.is_valid():
            user_id = form.cleaned_data.get("custom_user_id")
            logger.info(f"Received user ID: {user_id}")
            return super().form_valid(form)
        else:
            logger.error(f"Form errors: {form.errors}")
            return self.form_invalid(form)


class ForgotPasswordView(View):
    def get(self, request):
        return render(request, "forgot_password.html")

    def post(self, request):
        custom_user_id = request.POST.get("custom_user_id")
        try:
            user = CustomUser.objects.get(custom_user_id=custom_user_id)
            request.session["custom_user_id"] = user.custom_user_id
            return render(
                request, "forgot_password.html", {"secret_question": user.question}
            )
        except CustomUser.DoesNotExist:
            messages.error(request, "ユーザーIDが見つかりません。")
            return render(request, "forgot_password.html")


class VerifyAnswerView(View):
    def post(self, request):
        custom_user_id = request.session.get("custom_user_id")
        secret_answer = request.POST.get("secret_answer")
        try:
            user = CustomUser.objects.get(custom_user_id=custom_user_id)
            if check_password(secret_answer, user.answer):
                return render(request, "forgot_password.html", {"reset_password": True})
            else:
                messages.error(request, "秘密の質問の答えが正しくありません。")
                return render(
                    request, "forgot_password.html", {"secret_question": user.question}
                )
        except CustomUser.DoesNotExist:
            messages.error(request, "ユーザーが見つかりません。")
            return redirect("accounts:forgot_password")


class PasswordResetView(View):
    def post(self, request):
        custom_user_id = request.session.get("custom_user_id")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")
        custom_user_id = request.session.get("custom_user_id")
        password_pattern = re.compile(r"^(?=.*[0-9])(?=.*[a-zA-Z]).{5,15}$")
        if not password_pattern.match(new_password):
            messages.error(
                request,
                "パスワードは半角英数字を各1文字以上含む5文字以上15文字以下で入力してください。",
            )
            return render(request, "forgot_password.html", {"reset_password": True})

        if new_password != confirm_password:
            messages.error(request, "パスワードが一致しません。")
            return render(request, "forgot_password.html", {"reset_password": True})

        try:
            user = CustomUser.objects.get(custom_user_id=custom_user_id)
            user.password1 = make_password(new_password)
            user.password2 = make_password(new_password)
            user.save()
            messages.success(request, "パスワードがリセットされました。")
            return redirect("login")
        except CustomUser.DoesNotExist:
            messages.error(request, "ユーザーIDが存在しません。")
            return redirect("accounts:forgot_password")


class CheckUserIdView(View):
    def get(self, request, *args, **kwargs):
        user_id = request.GET.get("custom_user_id", None)
        if user_id:
            exists = CustomUser.objects.filter(custom_user_id=user_id).exists()
            if exists:
                return JsonResponse(
                    {"error": "このユーザーIDは既に使用されています。"}, status=400
                )
            else:
                return JsonResponse({"success": "このユーザーIDは使用可能です。"})
        return JsonResponse({"error": "ユーザーIDが提供されていません。"}, status=400)


class DemoLoginView(View):
    def get(self, request, *args, **kwargs):
        if not getattr(settings, "DEMO_ENABLED", False):
            return redirect("login")

        demo_user_id = getattr(settings, "DEMO_USER_ID", "demo001")
        demo_group_custom_id = getattr(settings, "DEMO_GROUP_CUSTOM_ID", "DEMO0001")
        demo_group_name = getattr(settings, "DEMO_GROUP_NAME", "体験用グループ")
        dummy_user_ids = getattr(
            settings, "DEMO_DUMMY_USER_IDS", ["demo002", "demo003"]
        )
        raw_pw = "demo123"

        demo_user, _ = CustomUser.objects.get_or_create(
            custom_user_id=demo_user_id,
            defaults={
                "username": demo_user_id,
                "password": make_password(raw_pw),
                "password1": raw_pw,
                "password2": raw_pw,
                "question": "demo",
                "answer": "demo",
            },
        )

        from mysfa.models import Group

        demo_group, _ = Group.objects.get_or_create(
            custom_id=demo_group_custom_id,
            defaults={"name": demo_group_name, "creator": demo_user},
        )
        if not demo_group.creator:
            demo_group.creator = demo_user
            demo_group.save(update_fields=["creator"])

        demo_group.users.add(demo_user)
        demo_user.groups.add(demo_group)

        # デモ内に「他ユーザーがいる体」を作るためのダミーユーザーを用意
        # NOTE:
        # CustomUser.save() は password1/password2/answer を毎回 make_password してしまうため、
        # ここでは update() + default_storage で “必要なときだけ” 値を更新する（再ハッシュ地雷回避）。
        from pathlib import Path

        src_dir = Path(__file__).resolve().parents[1]  # .../src
        default_profile_keys = {
            # 既存コード側のデフォルト参照
            "default_images/ic013.png",
            # リポジトリ上の静的素材パス（過去に直接セットしていた場合の揺れも吸収）
            "images/default_image/ic013.png",
        }

        demo_profiles = {
            "demo002": {
                "display_name": "山田太郎",
                "asset_path": src_dir
                / "static"
                / "images"
                / "default_image"
                / "demo002_ProfileImage.jpg",
                "dest_key": "default_images/demo002_ProfileImage.jpg",
            },
            "demo003": {
                "display_name": "山田花子",
                "asset_path": src_dir
                / "static"
                / "images"
                / "default_image"
                / "demo003_ProfileImage.jpg",
                "dest_key": "default_images/demo003_ProfileImage.jpg",
            },
        }

        def set_profile_image_if_needed(
            user: CustomUser, dest_key: str, asset_path: Path
        ):
            current_key = getattr(user.profile_image, "name", "") or ""
            if current_key == dest_key:
                return
            if current_key and current_key not in default_profile_keys:
                # デモ用途なので、既存のアップロード画像は差し替える（孤児ファイルを残さない）
                if default_storage.exists(current_key):
                    default_storage.delete(current_key)

            if not asset_path.exists():
                return

            if default_storage.exists(dest_key):
                default_storage.delete(dest_key)
            with asset_path.open("rb") as f:
                saved_key = default_storage.save(dest_key, File(f))
            CustomUser.objects.filter(custom_user_id=user.custom_user_id).update(
                profile_image=saved_key
            )

        for dummy_user_id in dummy_user_ids:
            if dummy_user_id == demo_user_id:
                continue

            dummy_user, _ = CustomUser.objects.get_or_create(
                custom_user_id=dummy_user_id,
                defaults={
                    "username": dummy_user_id,
                    "password": make_password(raw_pw),
                    "password1": raw_pw,
                    "password2": raw_pw,
                    "question": "demo",
                    "answer": "demo",
                },
            )
            demo_group.users.add(dummy_user)
            dummy_user.groups.add(demo_group)

            profile = demo_profiles.get(dummy_user_id)
            if not profile:
                continue

            # 表示名（username）をセット（すでに人名に変えてあるなら触らない）
            if (
                profile.get("display_name")
                and dummy_user.username == dummy_user.custom_user_id
            ):
                CustomUser.objects.filter(custom_user_id=dummy_user_id).update(
                    username=profile["display_name"]
                )

            # demo002 のプロフィール画像を指定素材に固定（ユーザー要望）
            if profile.get("asset_path") and profile.get("dest_key"):
                set_profile_image_if_needed(
                    dummy_user,
                    dest_key=profile["dest_key"],
                    asset_path=profile["asset_path"],
                )

        # 投稿の自動seedは要望により停止中（再開したい場合は DEMO_SEED_POSTS=true で有効化）
        if getattr(settings, "DEMO_SEED_POSTS", False):
            from mysfa.models import Post

            def attach_post_image_if_needed(
                post: Post, dest_key: str, asset_path: Path
            ):
                current_key = getattr(post.image, "name", "") or ""
                if current_key == dest_key:
                    return
                if current_key and default_storage.exists(current_key):
                    default_storage.delete(current_key)
                if not asset_path.exists():
                    return
                if default_storage.exists(dest_key):
                    default_storage.delete(dest_key)
                with asset_path.open("rb") as f:
                    saved_key = default_storage.save(dest_key, File(f))
                Post.objects.filter(pk=post.pk).update(image=saved_key)

            def upsert_post(
                *,
                user: CustomUser,
                group: Group,
                product_name: str,
                customer_category: str,
                contents: str,
                image_filename: str | None = None,
            ):
                # すでに同一内容があれば作らない（ログインの度に増えない）
                exists = Post.objects.filter(
                    user=user,
                    group=group,
                    product_name=product_name,
                    customer_category=customer_category,
                ).exists()
                if exists:
                    return

                post = Post.objects.create(
                    user=user,
                    group=group,
                    product_name=product_name[:50],
                    customer_category=customer_category[:50],
                    contents=contents[:100],
                )

                if image_filename:
                    asset_path = (
                        src_dir
                        / "static"
                        / "images"
                        / "default_image"
                        / image_filename
                    )
                    dest_key = f"post_images/demo/{image_filename}"
                    attach_post_image_if_needed(
                        post, dest_key=dest_key, asset_path=asset_path
                    )

            # PDF（file://demo002.pdf / file://demo003.pdf）を元に投稿をseed
            demo002 = CustomUser.objects.filter(custom_user_id="demo002").first()
            demo003 = CustomUser.objects.filter(custom_user_id="demo003").first()

            if demo002:
                upsert_post(
                    user=demo002,
                    group=demo_group,
                    product_name="無調整牛乳",
                    customer_category="喫茶店",
                    contents=(
                        "フェザリングが起きにくい特性を活かし提案。"
                        "コーヒーとの相性も評価され、カフェラテに採用。"
                    ),
                    image_filename="demo002_PostImage1.jpg",
                )
                upsert_post(
                    user=demo002,
                    group=demo_group,
                    product_name="スライスチーズ",
                    customer_category="ファストフード",
                    contents=(
                        "訪問中にチェダーチーズ使用のスライスチーズの問い合わせ。"
                        "サンプル配布後、ハンバーガーのレギュラーメニューに採用。"
                    ),
                    image_filename="demo002_PostImage2.jpg",
                )
                upsert_post(
                    user=demo002,
                    group=demo_group,
                    product_name="無塩バター",
                    customer_category="パティスリー",
                    contents=(
                        "コンパウンドバター使用店舗で無塩バターを提案。"
                        "乳風味と自然な色合いが評価され、パウンドケーキ用に採用。"
                    ),
                    image_filename="demo002_PostImage3.png",
                )

            if demo003:
                upsert_post(
                    user=demo003,
                    group=demo_group,
                    product_name="クリームチーズ",
                    customer_category="パティスリー",
                    contents=(
                        "チーズケーキ提供店舗へクリームチーズを提案。"
                        "酸味控えめで自然な風味が高評価で採用。"
                    ),
                    image_filename="demo003_PostImage1.jpg",
                )
                upsert_post(
                    user=demo003,
                    group=demo_group,
                    product_name="無塩バター",
                    customer_category="ブーランジェリー",
                    contents=(
                        "店頭販売用クッキーに採用。"
                        "各社北海道産を食べ比べ、ほろほろ食感になる点が高評価。"
                    ),
                    image_filename="demo003_PostImage2.jpg",
                )
                upsert_post(
                    user=demo003,
                    group=demo_group,
                    product_name="脱脂粉乳",
                    customer_category="学校",
                    contents=(
                        "給食のクリームシチューでスポット採用。"
                        "ロット管理が容易な点が評価され、今後も利用予定。"
                    ),
                    image_filename="demo003_PostImage3.jpg",
                )

        request.session["is_demo"] = True

        # authenticate() を経由しないので backend を明示してログイン
        login(request, demo_user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("mysfa:timeline")


class CustomLogoutView(View):
    def get(self, request):
        request.session.flush()
        logout(request)
        return redirect("home")


class DeleteAccountView(View):
    def get(self, request):
        if "messages" in request.session:
            del request.session["messages"]

        user = request.user
        logger.info(f"Original request.user: {type(user)}")
        logger.info(f"request.user.is_authenticated: {user.is_authenticated}")

        if hasattr(user, "_wrapped"):
            user = user._wrapped
            logger.info(f"After _wrapped: {type(user)}")

        try:
            if user.is_authenticated:
                logger.info(
                    f"User is authenticated, custom_user_id: "
                    f"{getattr(user, 'custom_user_id', 'Not found')}"
                )
                fresh_user = CustomUser.objects.get(custom_user_id=user.custom_user_id)
                logger.info(
                    f"Fresh user retrieved: {type(fresh_user)}, "
                    f"ID: {fresh_user.custom_user_id}"
                )
            else:
                logger.info("User is not authenticated")
                fresh_user = None
        except (CustomUser.DoesNotExist, AttributeError) as e:
            logger.error(f"Error getting fresh user: {e}")
            fresh_user = None

        context = {
            "debug": True,
            "user": fresh_user if fresh_user else user,
            "user_type": (
                type(fresh_user).__name__ if fresh_user else type(user).__name__
            ),
            "verification_result": None,
        }

        logger.info(f"Final context user: {type(context['user'])}")
        if context["user"]:
            logger.info(
                f"Final user ID: "
                f"{getattr(context['user'], 'custom_user_id', 'Not found')}"
            )

        return render(request, "registration/delete_account.html", context)

    def post(self, request):
        password = request.POST.get("password")

        user = request.user
        logger.info(f"POST - Original request.user: {type(user)}")
        logger.info(f"POST - request.user.is_authenticated: {user.is_authenticated}")

        if hasattr(user, "_wrapped"):
            user = user._wrapped
            logger.info(f"POST - After _wrapped: {type(user)}")

        try:
            if user.is_authenticated:
                logger.info(
                    f"POST - User is authenticated, custom_user_id: "
                    f"{getattr(user, 'custom_user_id', 'Not found')}"
                )
                fresh_user = CustomUser.objects.get(custom_user_id=user.custom_user_id)
                logger.info(
                    f"POST - Fresh user retrieved: {type(fresh_user)}, "
                    f"ID: {fresh_user.custom_user_id}"
                )
            else:
                logger.info("POST - User is not authenticated")
                messages.error(request, "ユーザーが認証されていません。")
                return render(request, "registration/delete_account.html")
        except (CustomUser.DoesNotExist, AttributeError) as e:
            logger.error(f"POST - Error getting fresh user: {e}")
            messages.error(request, "ユーザー情報の取得に失敗しました。")
            return render(request, "registration/delete_account.html")

        logger.info(f"Delete account attempt for user: {fresh_user.custom_user_id}")
        logger.info(f"User model type: {type(fresh_user)}")
        logger.info(f"User fields: {[field.name for field in fresh_user._meta.fields]}")
        logger.info(f"Password field exists: {hasattr(fresh_user, 'password1')}")
        logger.info(
            f"Password1 field value: "
            f"{getattr(fresh_user, 'password1', 'Not found')}"
        )
        logger.info(
            f"Standard password field exists: {hasattr(fresh_user, 'password')}"
        )
        logger.info(
            f"Standard password field value: "
            f"{getattr(fresh_user, 'password', 'Not found')}"
        )

        password_verified = False
        verification_method = None

        if hasattr(fresh_user, "password1") and fresh_user.password1:
            try:
                if check_password(password, fresh_user.password1):
                    password_verified = True
                    verification_method = "password1 field"
                    logger.info(
                        "Password verification successful using password1 field"
                    )
                else:
                    logger.info("Password verification failed using password1 field")
            except Exception as e:
                logger.error(f"Error checking password with password1: {e}")

        if not password_verified:
            try:
                if fresh_user.check_password(password):
                    password_verified = True
                    verification_method = "Django's check_password"
                    logger.info(
                        "Password verification successful using Django's check_password"
                    )
                else:
                    logger.info(
                        "Password verification failed using Django's check_password"
                    )
            except Exception as e:
                logger.error(f"Error checking password with Django's method: {e}")

        if not password_verified and hasattr(fresh_user, "password1"):
            try:
                latest_user = CustomUser.objects.get(
                    custom_user_id=fresh_user.custom_user_id
                )
                if check_password(password, latest_user.password1):
                    password_verified = True
                    verification_method = "latest user data"
                    logger.info(
                        "Password verification successful using latest user data"
                    )
                else:
                    logger.info("Password verification failed using latest user data")
            except Exception as e:
                logger.error(f"Error checking password with latest user data: {e}")

        logger.info(f"Final password verification result: {password_verified}")
        if password_verified:
            logger.info(f"Verification method used: {verification_method}")

        if password_verified:
            logger.info(
                f"Password verification successful for user: "
                f"{fresh_user.custom_user_id}"
            )
            try:
                logger.info(f"About to delete user: {fresh_user.custom_user_id}")

                fresh_user.delete()
                logger.info(f"User {fresh_user.custom_user_id} deleted successfully")

                try:
                    check_user = CustomUser.objects.get(
                        custom_user_id=fresh_user.custom_user_id
                    )
                    logger.warning(
                        f"User still exists after deletion: {check_user.custom_user_id}"
                    )
                except CustomUser.DoesNotExist:
                    logger.info(
                        f"User {fresh_user.custom_user_id} "
                        f"confirmed deleted from database"
                    )

                request.session.flush()
                logout(request)
                messages.success(request, "アカウントが削除されました。")
                return redirect("home")
            except Exception as e:
                logger.error(f"Error deleting user: {e}")
                messages.error(request, "アカウントの削除中にエラーが発生しました。")
                return render(request, "registration/delete_account.html")
        else:
            logger.warning(
                f"All password verification methods failed for user: "
                f"{fresh_user.custom_user_id}"
            )

            context = {
                "debug": True,
                "user": fresh_user,
                "user_type": type(fresh_user).__name__,
                "verification_result": {
                    "verified": False,
                    "method": "None",
                    "password_length": len(password) if password else 0,
                },
            }

            messages.error(request, "パスワードが正しくありません。")
            return render(request, "registration/delete_account.html", context)
