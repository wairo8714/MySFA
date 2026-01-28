import json

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required

from .models import Post, GroupMembership

def health(request):
    return JsonResponse({"ok": True})


from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import GroupMembership, Post, PostComment


@require_http_methods(["GET", "HEAD"])
def health(request):
    return JsonResponse({"ok": True})


@require_http_methods(["GET"])
def me(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"detail": "Authentication credentials were not provided."}, status=401)

    return JsonResponse(
        {
            "id": user.pk,
            "custom_user_id": getattr(user, "custom_user_id", None),
            "username": user.get_username(),
            "email": getattr(user, "email", None),
        }
    )


@ensure_csrf_cookie
@require_http_methods(["GET", "HEAD"])
def csrf(request):
    return JsonResponse({"ok": True})


@require_http_methods(["GET"])
@login_required
def posts(request):
    try:
        group_id = int(request.GET.get("group_id", "0"))
    except ValueError:
        return JsonResponse({"detail": "group_id must be an integer."}, status=400)

    if group_id <= 0:
        return JsonResponse({"detail": "group_id is required."}, status=400)

    is_member = GroupMembership.objects.filter(
        group_id=group_id,
        user_id=request.user.pk,
        is_active=True,
    ).exists()

    if not is_member:
        return JsonResponse({"detail": "You do not have permission to access this group."}, status=403)

    try:
        page = int(request.GET.get("page", "1"))
        page_size = int(request.GET.get("page_size", "20"))
    except ValueError:
        return JsonResponse({"detail": "page and page_size must be integers."}, status=400)

    page_size = max(1, min(page_size, 50))

    qs = (
        Post.objects.filter(group_id=group_id)
        .select_related("user", "product", "industry")
        .prefetch_related("liked_users")
    )

    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    items = []
    for p in page_obj.object_list:
        items.append(
            {
                "id": p.id,
                "status": p.status,
                "contents": p.contents,
                "created_at": p.created_at.isoformat(),
                "likes_count": p.likes_count,
                "liked_by_me": p.liked_users.filter(pk=request.user.pk).exists(),
                "author": {
                    "id": p.user_id,
                    "username": p.user.get_username(),
                },
                "product": {
                    "id": p.product_id,
                    "name": p.product.name if p.product_id else "",
                },
                "industry": {
                    "id": p.industry_id,
                    "name": p.industry.name if p.industry_id else "",
                },
                "image_url": p.image.url if p.image else None,
            }
        )

    return JsonResponse(
        {
            "page": page_obj.number,
            "page_size": page_size,
            "total_pages": paginator.num_pages,
            "total_count": paginator.count,
            "items": items,
        }
    )


def _json_body(request):
    try:
        raw = request.body.decode("utf-8") if request.body else ""
        return json.loads(raw) if raw else {}
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _is_group_member(group_id, user_pk):
    return GroupMembership.objects.filter(
        group_id=group_id,
        user_id=user_pk,
        is_active=True,
    ).exists()


@require_http_methods(["GET"])
@login_required
def groups(request):
    qs = (
        GroupMembership.objects.filter(user_id=request.user.pk, is_active=True)
        .select_related("group")
        .order_by("group_id")
    )

    items = []
    for m in qs:
        g = m.group
        items.append(
            {
                "group_id": g.id,
                "custom_id": getattr(g, "custom_id", None),
                "name": g.name,
                "role": m.role,
            }
        )

    return JsonResponse({"items": items})


@require_http_methods(["POST"])
@login_required
def create_post(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "Invalid JSON."}, status=400)

    group_id = data.get("group_id")
    contents = (data.get("contents") or "").strip()

    if not isinstance(group_id, int) or group_id <= 0:
        return JsonResponse({"detail": "group_id is required and must be an integer."}, status=400)

    if not contents:
        return JsonResponse({"detail": "contents is required."}, status=400)

    if not _is_group_member(group_id, request.user.pk):
        return JsonResponse({"detail": "You don't have permission to access this group."} status=403)

    status = data.get("status") or Post.Status.NEGOTIATING
    product_id = data.get("product_id")
    industry_id = data.get("industry_id")

    post = Post.objects.create(
        user_id=request.user.pk,
        group_id=group_id,
        status=status,
        contents=contents,
        product_id=product_id if isinstance(product_id, int) else None,
        industry_id=industry_id if isinstance(industry_id, int) else None,
    )

    return JsonResponse(
        {
            "id": post.id,
            "created_at": post.created_at.isoformat(),
        },
        status=201,
    )


@require_http_mothods(["POST"])
@login_required
def toggle_like(request, post_id: int):
    try:
        post_id = int(post_id)
    except ValueError:
        return JsonResponse({"detail": "post_id must be an integer."}, status=400)

    
        post = (
            Post.objects.select_related("group")
            .prefetch_related("liked_users")
            .filter(id=post_id)
            .first()
        )
        if post is None:
            return JsonResponse({"detail": "Not found."}, status=404)

        if not _is_group_member(post.group_id, request.user.pk):
            return JsonResponse({"detail": "You don't have permission to access this group."}, status(403)

        with transaction.atomic()
            already = post.liked_users.filter(pk=request.user.pk).exists()
            if already:
                post.liked_users.remove(request.user)
                Post.objects.filter(id=post.id).update(likes_count=models.F("likes_count") + 1)
                liked = True

            post.refresh_from_db(fields=["likes_count"])

        return JsonResponse({"liked": liked, "likes_count": post.likes_count})


@require_http_methods(["GET"])
@login_required
def comments(request, post_id: int):
    try:
        post_id = int(post_id)
    except ValueError:
        return JsonResponse({"detail": "post_id must be an integer."}, status=400)

    post = Post.objects.filter(id=post_id).only("id", "group_id").first()
    if post is None:
        return JsonResponse({"detail": "Not found."}, status=404)

    if not _is_group_member(post.group_id, request.user.pk):
        return JsonResponse({"detail": "You don't have permission to access this group."}, status=403)

    qs = (
        PostComment.objects.filter(post_id=post_id)
        .select_related("author")
        .order_by("created_at")
    )

    items = []
    for c in qs:
        items.append(
            {
                "id": c.id,
                "body": c.body,
                "parent_id": c.parent_id,
                "created_at": c.created_at.isformat(),
                "author": {
                    "id": c.author_id,
                    "username": c.author.get_username(),
                },
            }
        )

    return JsonResponse({"items": items})


@require_http_methods(["POST"])
@login_required
def create_comment(request, post_id: int):
    try:
        post_id = int(post_id)
    except ValueError:
        return JsonResponse({"detail: "post_id must be an integer."}, status=400)

    data = _json_body(request)
    if data is None:
                            
