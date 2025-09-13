from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView

from accounts.models import CustomUser

from .forms import GroupForm, PostForm, UserProfileForm
from .models import Group, JoinRequest, Post


class Timeline(LoginRequiredMixin, ListView):
    model = Post
    template_name = "post/timeline.html"
    context_object_name = "object_list"
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        custom_id = self.request.GET.get("custom_id")
        user_groups = Group.objects.filter(users=user)

        if custom_id:
            group = get_object_or_404(Group, custom_id=custom_id, users=user)
            queryset = Post.objects.filter(group=group).distinct()
        else:
            queryset = Post.objects.filter(group__in=user_groups).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        custom_id = self.request.GET.get("custom_id")
        context["user_groups"] = Group.objects.filter(users=self.request.user)
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
            if custom_id:
                return redirect(f"mysfa:timeline?custom_id={custom_id}")
            return redirect("mysfa:timeline")

        form = PostForm(request.POST, request.FILES, user=request.user)

        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            if not post.group:
                last_group = request.user.groups.last()
                if last_group:
                    post.group = last_group
            if "image" in request.FILES:
                post.image = request.FILES["image"]
            post.save()

            if custom_id:
                return redirect(f"mysfa:timeline?custom_id={custom_id}")
            return redirect("mysfa:timeline")
        else:
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
                group = Group.objects.get(custom_id=custom_id)
                queryset = queryset.filter(group=group)
            except Group.DoesNotExist:
                queryset = Post.objects.none()
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

        from .models import Group

        user_groups = Group.objects.filter(users=context["displayed_user"])
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
        custom_user_id = user.custom_user_id
        return redirect("mysfa:mypost", custom_user_id=custom_user_id)


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
        group = get_object_or_404(Group, custom_id=self.kwargs["custom_id"])
        return Post.objects.filter(group=group).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = get_object_or_404(Group, custom_id=self.kwargs["custom_id"])
        user = self.request.user
        creator = group.creator
        members = group.users.all()

        context["group"] = group
        context["is_member"] = user.groups.filter(id=group.id).exists()
        context["creator"] = creator
        context["members"] = members
        context["member_count"] = members.count()
        context["user_has_requested"] = JoinRequest.objects.filter(
            user=user, group=group
        ).exists()
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

        # その他のPOSTリクエストはGETビューを呼び出し
        return self.get(request, *args, **kwargs)


@method_decorator(login_required, name="dispatch")
class UploadGroupIconView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs["custom_id"])
        default_image_path = "default_images/702.png"

        if "icon" in request.FILES:
            if group.icon and group.icon.name != default_image_path:
                group.icon.delete(save=False)
            group.icon = request.FILES["icon"]
        else:
            if not group.icon:
                group.icon = default_image_path

        group.save()
        custom_id = group.custom_id
        return redirect("mysfa:group_posts", custom_id=custom_id)


class ToggleGroupLockView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs["custom_id"])
        if request.user in group.users.all():
            group.is_locked = not group.is_locked
            group.save()
        return redirect("mysfa:group_posts", custom_id=group.custom_id)


class JoinGroupView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs["custom_id"])
        request.user.groups.add(group)
        group.users.add(request.user)
        return redirect("mysfa:group_posts", custom_id=kwargs["custom_id"])


class JoinGroupRequestView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs["custom_id"])

        if request.user in group.users.all():
            return redirect("mysfa:group_posts", custom_id=group.custom_id)

        if group.is_locked:
            if not JoinRequest.objects.filter(user=request.user, group=group).exists():
                JoinRequest.objects.create(user=request.user, group=group)
            return redirect("mysfa:group_posts", custom_id=group.custom_id)
        else:
            request.user.groups.add(group)
            group.users.add(request.user)
            return redirect("mysfa:group_posts", custom_id=group.custom_id)


class ApproveJoinRequestView(View):
    def post(self, request, custom_id, request_id):
        group = get_object_or_404(Group, custom_id=custom_id)
        join_request = get_object_or_404(
            JoinRequest, user__custom_user_id=request_id, group=group
        )
        group.users.add(join_request.user)
        join_request.delete()
        return redirect("mysfa:group_posts", custom_id=custom_id)


class RejectJoinRequestView(View):
    def post(self, request, custom_id, request_id):
        group = get_object_or_404(Group, custom_id=custom_id)
        join_request = get_object_or_404(
            JoinRequest, user__custom_user_id=request_id, group=group
        )
        join_request.delete()
        return redirect("mysfa:group_posts", custom_id=custom_id)


class LeaveGroupView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs["custom_id"])
        request.user.groups.remove(group)
        group.users.remove(request.user)
        return redirect("home")


class DeleteGroupView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs["custom_id"])
        creator = group.users.first()
        if request.user == creator:
            group.delete()
            return redirect("home")
        else:
            return HttpResponseForbidden(
                "グループの作成者のみ削除を行うことができます。"
            )


class RemoveMemberView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs["custom_id"])
        user_to_remove = get_object_or_404(
            CustomUser, custom_user_id=kwargs["custom_user_id"]
        )

        if request.user == group.creator and user_to_remove in group.users.all():
            group.users.remove(user_to_remove)
            messages.success(
                request, f"{user_to_remove.username}をグループから退会させました。"
            )
        else:
            messages.error(request, "この操作を行う権限がありません。")

        return redirect("mysfa:group_posts", custom_id=kwargs["custom_id"])


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
        groups = Group.objects.filter(name__icontains=query)
        for group in groups:
            group.is_member = group.users.filter(
                custom_user_id=request.user.custom_user_id
            ).exists()
        return render(
            request, "group/search_group.html", {"groups": groups, "query": query}
        )

    def post(self, request, custom_id):
        group = Group.objects.get(custom_id=custom_id)
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
                posts = Post.objects.filter(
                    product_name__icontains=query, group__in=user_groups
                )
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
                customers = Post.objects.filter(
                    customer_category__icontains=query, group__in=user_groups
                )
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
            post.delete()
            return redirect("mysfa:search_customers")


class SearchUsersView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get("q", "")
        page = request.GET.get("page", 1)

        if query:
            users = CustomUser.objects.filter(
                Q(username__icontains=query) | Q(custom_user_id__icontains=query)
            )
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
        print("=== LIKE REQUEST DEBUG ===")
        print(f"User: {request.user.username}")
        print(f"Post ID: {post_id}")
        print(f"Request method: {request.method}")

        try:
            post = get_object_or_404(Post, id=post_id)
            print(f"Post found: {post.product_name}")
            print(f"Current likes count: {post.likes_count}")

            if request.user in post.liked_users.all():
                post.liked_users.remove(request.user)
                post.likes_count -= 1
                status = "unliked"
                print("User unliked the post")
            else:
                post.liked_users.add(request.user)
                post.likes_count += 1
                status = "liked"
                print("User liked the post")

            post.save()

            print(f"Updated likes count: {post.likes_count}")
            print("=== END DEBUG ===")

            return JsonResponse(
                {
                    "status": status,
                    "count": post.likes_count,
                    "message": f"Post {status} successfully",
                }
            )

        except Exception as e:
            print(f"Error occurred: {str(e)}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


@method_decorator(login_required, name="dispatch")
class TestReportView(View):
    def get(self, request):
        print("=== TEST REPORT VIEW CALLED ===")
        return JsonResponse({"message": "Test view working"})


@method_decorator(login_required, name="dispatch")
class SalesReportView(View):
    def get(self, request, user_id=None, group_id=None):
        print("=== SALES REPORT VIEW CALLED ===")
        print(f"User ID: {user_id}")
        print(f"Group ID: {group_id}")

        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")
        selected_group_id = request.GET.get("custom_id")  # グループ選択のID

        print(f"Start date: {start_date_str}")
        print(f"End date: {end_date_str}")
        print(f"Selected group ID: {selected_group_id}")

        if not start_date_str or not end_date_str:
            return JsonResponse({"error": "開始日と終了日が必要です"}, status=400)

        try:
            start_date = datetime.strptime(start_date_str, "%Y/%m/%d").date()
            end_date = datetime.strptime(end_date_str, "%Y/%m/%d").date()
            print(f"Parsed start date: {start_date}")
            print(f"Parsed end date: {end_date}")
        except ValueError as e:
            print(f"Date parsing error: {e}")
            return JsonResponse({"error": "日付形式が正しくありません"}, status=400)

        if group_id:
            print(f"Processing group sales report for group: {group_id}")
            try:
                group = Group.objects.get(custom_id=group_id)
                posts = Post.objects.filter(
                    group=group,
                    created_at__date__gte=start_date,
                    created_at__date__lte=end_date,
                )
                print(
                    f"Found {posts.count()} posts in group {group_id} "
                    f"between {start_date} and {end_date}"
                )
            except Group.DoesNotExist:
                print(f"Group {group_id} not found")
                return JsonResponse({"error": "グループが見つかりません"}, status=404)
        else:
            print(f"Processing user sales report for user: {user_id}")
            try:
                user = CustomUser.objects.get(custom_user_id=user_id)

                if selected_group_id:
                    # 特定のグループが選択されている場合
                    try:
                        selected_group = Group.objects.get(custom_id=selected_group_id)
                        posts = Post.objects.filter(
                            user=user,
                            group=selected_group,
                            created_at__date__gte=start_date,
                            created_at__date__lte=end_date,
                        )
                        print(
                            f"Found {posts.count()} posts by user {user_id} "
                            f"in group {selected_group_id} between "
                            f"{start_date} and {end_date}"
                        )
                    except Group.DoesNotExist:
                        print(f"Selected group {selected_group_id} not found")
                        return JsonResponse(
                            {"error": "選択されたグループが見つかりません"}, status=404
                        )
                else:
                    # グループが選択されていない場合（デフォルト：全グループ）
                    # ユーザーが所属しているグループの投稿をすべて取得
                    user_groups = user.groups.all()
                    posts = Post.objects.filter(
                        group__in=user_groups,
                        created_at__date__gte=start_date,
                        created_at__date__lte=end_date,
                    )
                    print(
                        f"Found {posts.count()} posts from user's groups "
                        f"{[g.name for g in user_groups]} between "
                        f"{start_date} and {end_date}"
                    )

            except CustomUser.DoesNotExist:
                print(f"User {user_id} not found")
                return JsonResponse({"error": "ユーザーが見つかりません"}, status=404)

        product_counts = {}
        customer_counts = {}

        for post in posts:
            print(
                f"Processing post {post.id}: {post.product_name} - "
                f"{post.customer_category} - {post.created_at}"
            )

            if post.product_name:
                product_counts[post.product_name] = (
                    product_counts.get(post.product_name, 0) + 1
                )

            if post.customer_category:
                customer_counts[post.customer_category] = (
                    customer_counts.get(post.customer_category, 0) + 1
                )

        print(f"Product counts: {product_counts}")
        print(f"Customer counts: {customer_counts}")

        product_data = [
            {"product_name": name, "count": count}
            for name, count in product_counts.items()
        ]
        customer_data = [
            {"customer_category": category, "count": count}
            for category, count in customer_counts.items()
        ]

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
                top_customers.append(
                    {"customer_category": "その他", "count": other_count}
                )
            customer_data = top_customers

        response_data = {
            "product_data": product_data,
            "customer_data": customer_data,
            "start_date": start_date_str,
            "end_date": end_date_str,
            "total_posts": posts.count(),
        }

        print(f"Final response data: {response_data}")
        return JsonResponse(response_data)
