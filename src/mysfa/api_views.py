from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required

from .models import Post, GroupMembership

def health(request):
    return JsonResponse({"ok": True})


from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import GroupMembership, Post


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
