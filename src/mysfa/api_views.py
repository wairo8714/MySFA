import json

from django.core.paginator import Paginator
from django.db import models, transaction
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import GroupMembership, Post, PostComment


def _require_auth(request):
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )
    return None


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


@require_http_methods(["GET", "HEAD"])
def health(request):
    return JsonResponse({"ok": True})


@require_http_methods(["GET"])
def me(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

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
def groups(request):
    unauth = _require_auth(request)
    if unauth:
        return unauth

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


@require_http_methods(["GET", "POST"])
def posts(request):
    unauth = _require_auth(request)
    if unauth:
        return unauth

    if request.method == "POST":
        data = _json_body(request)
        if data is None:
            return JsonResponse({"detail": "Invalid JSON."}, status=400)

        group_id = data.get("group_id")
        contents = (data.get("contents") or "").strip()

        if not isinstance(group_id, int) or group_id <= 0:
            return JsonResponse(
                {"detail": "group_id is required and must be an integer."},
                status=400,
            )

        if not contents:
            return JsonResponse({"detail": "contents is required."}, status=400)

        if not _is_group_member(group_id, request.user.pk):
            return JsonResponse(
                {"detail": "You do not have permission to access this group."},
                status=403,
            )

        status = data.get("status") or Post.Status.NEGOTIATING
        allowed_status = {c[0] for c in Post.Status.choices}
        if status not in allowed_status:
            return JsonResponse({"detail": "Invalid status."}, status=400)

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

    # GET: list
    try:
        group_id = int(request.GET.get("group_id", "0"))
    except ValueError:
        return JsonResponse({"detail": "group_id must be an integer."}, status=400)

    if group_id <= 0:
        return JsonResponse({"detail": "group_id is required."}, status=400)

    if not _is_group_member(group_id, request.user.pk):
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
        .order_by("-created_at")
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


@require_http_methods(["POST"])
def toggle_like(request, post_id: int):
    unauth = _require_auth(request)
    if unauth:
        return unauth

    post = (
        Post.objects.select_related("group")
        .filter(id=post_id)
        .only("id", "group_id", "likes_count")
        .first()
    )
    if post is None:
        return JsonResponse({"detail": "Not found."}, status=404)

    if not _is_group_member(post.group_id, request.user.pk):
        return JsonResponse({"detail": "You do not have permission to access this group."}, status=403)

    with transaction.atomic():
        post = Post.objects.select_for_update().get(id=post.id)
        already = post.liked_users.filter(pk=request.user.pk).exists()
        if already:
            post.liked_users.remove(request.user)
            Post.objects.filter(id=post.id).update(likes_count=models.F("likes_count") - 1)
            liked = False
        else:
            post.liked_users.add(request.user)
            Post.objects.filter(id=post.id).update(likes_count=models.F("likes_count") + 1)
            liked = True

        post.refresh_from_db(fields=["likes_count"])

    return JsonResponse({"liked": liked, "likes_count": post.likes_count})


@require_http_methods(["GET", "POST"])
def comments(request, post_id: int):
    unauth = _require_auth(request)
    if unauth:
        return unauth

    post = Post.objects.filter(id=post_id).only("id", "group_id").first()
    if post is None:
        return JsonResponse({"detail": "Not found."}, status=404)

    if not _is_group_member(post.group_id, request.user.pk):
        return JsonResponse({"detail": "You do not have permission to access this group."}, status=403)

    if request.method == "POST":
        data = _json_body(request)
        if data is None:
            return JsonResponse({"detail": "Invalid JSON."}, status=400)

        body = (data.get("body") or "").strip()
        parent_id = data.get("parent_id")

        if not body:
            return JsonResponse({"detail": "body is required."}, status=400)

        parent = None
        if parent_id is not None:
            if not isinstance(parent_id, int):
                return JsonResponse({"detail": "parent_id must be an integer."}, status=400)
            parent = PostComment.objects.filter(id=parent_id, post_id=post_id).first()
            if parent is None:
                return JsonResponse({"detail": "parent comment not found."}, status=400)

        c = PostComment.objects.create(
            post_id=post_id,
            author_id=request.user.pk,
            body=body,
            parent=parent,
        )

        return JsonResponse(
            {
                "id": c.id,
                "created_at": c.created_at.isoformat(),
            },
            status=201,
        )

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
                "created_at": c.created_at.isoformat(),
                "author": {
                    "id": c.author_id,
                    "username": c.author.get_username(),
                },
            }
        )

    return JsonResponse({"items": items})
