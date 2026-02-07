from __future__ import annotations

from datetime import datetime
from typing import Any

from django.contrib.auth import get_user_model

from ..models import Group, GroupMembership, IndustryMaster, Post, ProductMaster


def create_user(
    *,
    custom_user_id: str = "U001",
    username: str = "User",
    email: str = "u@example.com",
    password: str = "pass12345",
    question: str = "q",
    answer: str = "a",
    **extra: Any,
):
    User = get_user_model()
    return User.objects.create_user(
        custom_user_id=custom_user_id,
        username=username,
        email=email,
        password=password,
        question=question,
        answer=answer,
        **extra,
    )


def create_group(
    *, name: str = "G1", creator, is_active: bool = True, is_locked: bool = False
):
    g = Group.objects.create(
        name=name, creator=creator, is_active=is_active, is_locked=is_locked
    )
    g.users.add(creator)
    GroupMembership.objects.get_or_create(
        group=g,
        user=creator,
        defaults={"role": GroupMembership.Role.OWNER, "is_active": True},
    )
    return g


def add_member(*, group: Group, user, role: str = GroupMembership.Role.MEMBER):
    group.users.add(user)
    m, _ = GroupMembership.objects.update_or_create(
        group=group,
        user=user,
        defaults={"role": role, "is_active": True},
    )
    return m


def create_product(
    *,
    group: Group,
    product_code: str = "P001",
    name: str = "Product",
    category_main: str | None = None,
    category_sub: str | None = None,
    is_active: bool = True,
):
    return ProductMaster.objects.create(
        group=group,
        product_code=product_code,
        name=name,
        category_main=category_main,
        category_sub=category_sub,
        is_active=is_active,
    )


def create_industry(*, group: Group, name: str = "Industry", is_active: bool = True):
    return IndustryMaster.objects.create(group=group, name=name, is_active=is_active)


def create_post(
    *,
    user,
    group: Group,
    contents: str = "hello",
    product: ProductMaster | None = None,
    industry: IndustryMaster | None = None,
    status: str = Post.Status.NEGOTIATING,
    created_at: datetime | None = None,
):
    post = Post.objects.create(
        user=user,
        group=group,
        contents=contents,
        product=product,
        industry=industry,
        status=status,
    )
    if created_at is not None:
        Post.objects.filter(pk=post.pk).update(created_at=created_at)
        post.refresh_from_db()
    return post
