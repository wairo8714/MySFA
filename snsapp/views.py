from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from django.http import HttpResponseForbidden
from .models import Post, Group, JoinRequest
from .forms import GroupForm, PostForm, UserProfileForm
from accounts.models import CustomUser  
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.auth.models import Group as AuthGroup
from django.db.models import Q
from django.contrib import messages

class HomeView(LoginRequiredMixin, View):
    def get(self, request):
        # ユーザーがグループに所属しているか確認
        if request.user.groups.exists():
            return redirect('snsapp:timeline')

class Timeline(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'post/timeline.html'
    context_object_name = 'object_list'
    paginate_by = 10  

    def get_queryset(self):
        user = self.request.user
        custom_id = self.request.GET.get('custom_id')
        if custom_id:
            group = get_object_or_404(Group, custom_id=custom_id, users=user)  
            queryset = Post.objects.filter(group=group).distinct()  
        else:
            queryset = Post.objects.filter(user__groups__in=user.groups.all()).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        custom_id = self.request.GET.get('custom_id')
        context['user_groups'] = self.request.user.groups.all()  
        context['selected_group_id'] = custom_id
        context['form'] = PostForm(user=self.request.user)  
        queryset = self.get_queryset()
        paginator = Paginator(queryset, self.paginate_by)
        page = self.request.GET.get('page')
        try:
            object_list = paginator.page(page)
        except PageNotAnInteger:
            object_list = paginator.page(1)
        except EmptyPage:
            object_list = paginator.page(paginator.num_pages)
        
        context['object_list'] = object_list
        context['object_list_class_name'] = object_list.__class__.__name__ 
        return context
    
    def post(self, request, *args, **kwargs):
        if 'delete_post_id' in request.POST:
            post_id = request.POST.get('delete_post_id')
            post = get_object_or_404(Post, id=post_id, user=request.user)
            post.delete()
            return redirect('snsapp:timeline')
        
        form = PostForm(request.POST, request.FILES, user=request.user)
        
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            if not post.group:
                last_group = request.user.groups.last()
                if last_group:
                    post.group = last_group
            post.save()
            return redirect('snsapp:timeline')
        else:
            self.object_list = self.get_queryset()
            context = self.get_context_data()
            context['form'] = form
            context['selected_group_id'] = self.request.GET.get('custom_id')
            return self.render_to_response(context)

class MyPost(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'post/mypost.html'
    context_object_name = 'posts'
    paginate_by = 10  

    def get_queryset(self):
        custom_user_id = self.kwargs['custom_user_id']
        user = get_object_or_404(CustomUser, custom_user_id=custom_user_id)
        queryset = Post.objects.filter(user=user)
        custom_id = self.request.GET.get('custom_id')
        if custom_id:
            queryset = queryset.filter(group__id=custom_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        custom_user_id = self.kwargs['custom_user_id']
        context['displayed_user'] = get_object_or_404(CustomUser, custom_user_id=custom_user_id)
        context['current_user'] = self.request.user
        context['form'] = UserProfileForm(instance=self.request.user)
        queryset = self.get_queryset()
        paginator = Paginator(queryset, self.paginate_by)
        page = self.request.GET.get('page')
        try:
            object_list = paginator.page(page)
        except PageNotAnInteger:
            object_list = paginator.page(1)
        except EmptyPage:
            object_list = paginator.page(paginator.num_pages)
        
        context['object_list'] = object_list
        context['object_list_class_name'] = object_list.__class__.__name__ 
        return context

    def post(self, request, *args, **kwargs):
        if 'delete_post_id' in request.POST:
            post_id = request.POST.get('delete_post_id')
            post = get_object_or_404(Post, id=post_id, user=request.user)
            post.delete()
            return redirect('snsapp:mypost', custom_user_id=request.user.custom_user_id)
        
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('snsapp:mypost', custom_user_id=request.user.custom_user_id)
        context = self.get_context_data()
        context['form'] = form
        return render(request, self.template_name, context)
    
@method_decorator(login_required, name='dispatch')
class UploadIconView(View):
    def post(self, request, *args, **kwargs):
        user = request.user
        default_image_path = 'default_images/ic013.png'
        
        if 'profile_image' in request.FILES:
            # 既存の画像がデフォルト画像でない場合のみ削除
            if user.profile_image and user.profile_image.name != default_image_path:
                user.profile_image.delete(save=False)  # 既存の画像を削除
            
            # 新しい画像を設定
            user.profile_image = request.FILES['profile_image']
        else:
            # 画像がアップロードされていない場合、デフォルト画像を設定
            if not user.profile_image:
                user.profile_image = default_image_path  # デフォルト画像を設定

        user.save()
        custom_user_id = user.custom_user_id
        return redirect('snsapp:mypost', custom_user_id=custom_user_id)
    
class UpdateUsernameView(View):
    def post(self, request, *args, **kwargs):
        user = request.user
        user.username = request.POST.get('username')
        user.save()
        return redirect('snsapp:mypost', custom_user_id=user.custom_user_id)

class GroupPost(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'group/grouppost.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        group = get_object_or_404(Group, custom_id=self.kwargs['custom_id'])
        return Post.objects.filter(group=group).distinct()  

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = get_object_or_404(Group, custom_id=self.kwargs['custom_id'])
        user = self.request.user
        creator = group.creator 
        members = group.users.all()

        context['group'] = group
        context['is_member'] = user.groups.filter(id=group.id).exists()
        context['creator'] = creator  
        context['members'] = members
        context['member_count'] = members.count()
        context['user_has_requested'] = JoinRequest.objects.filter(user=user, group=group).exists()
        context['join_requests'] = JoinRequest.objects.filter(group=group)
        queryset = self.get_queryset()
        paginator = Paginator(queryset, self.paginate_by)
        page = self.request.GET.get('page')
        try:
            object_list = paginator.page(page)
        except PageNotAnInteger:
            object_list = paginator.page(1)
        except EmptyPage:
            object_list = paginator.page(paginator.num_pages)
        
        context['object_list'] = object_list
        context['object_list_class_name'] = object_list.__class__.__name__
        return context
    
    def post(self, request, *args, **kwargs):
        if 'delete_post_id' in request.POST:
            post_id = request.POST.get('delete_post_id')
            post = get_object_or_404(Post, id=post_id, user=request.user)
            post.delete()
            return redirect('snsapp:group_posts', custom_id=self.kwargs['custom_id'])
    
@method_decorator(login_required, name='dispatch')
class UploadGroupIconView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs['custom_id'])
        default_image_path = 'default_images/702.png'
        
        if 'icon' in request.FILES:
            if group.icon and group.icon.name != default_image_path:
                group.icon.delete(save=False)
            group.icon = request.FILES['icon']
        else:
            if not group.icon:
                group.icon = default_image_path

        group.save()
        custom_id = group.custom_id
        return redirect('snsapp:group_posts', custom_id=custom_id)
    
class ToggleGroupLockView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs['custom_id'])
        if request.user in group.users.all():
            group.is_locked = not group.is_locked
            group.save()
        return redirect('snsapp:group_posts', custom_id=group.custom_id)

class JoinGroupView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs['custom_id'])
        request.user.groups.add(group)
        group.users.add(request.user)
        return redirect('snsapp:group_posts', custom_id=kwargs['custom_id'])
    
class JoinGroupRequestView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs['custom_id'])
        
        if request.user in group.users.all():
            return redirect('snsapp:group_posts', custom_id=group.custom_id)
        
        if group.is_locked:
            if not JoinRequest.objects.filter(user=request.user, group=group).exists():
                JoinRequest.objects.create(user=request.user, group=group)
            return redirect('snsapp:group_posts', custom_id=group.custom_id)
        else:
            request.user.groups.add(group)
            group.users.add(request.user)
            return redirect('snsapp:group_posts', custom_id=group.custom_id)
        
class ApproveJoinRequestView(View):
    def post(self, request, custom_id, request_id):
        group = get_object_or_404(Group, custom_id=custom_id)
        join_request = get_object_or_404(JoinRequest, user__custom_user_id=request_id, group=group)
        group.users.add(join_request.user)
        join_request.delete()
        return redirect('snsapp:group_posts', custom_id=custom_id)

class RejectJoinRequestView(View):
    def post(self, request, custom_id, request_id):
        group = get_object_or_404(Group, custom_id=custom_id)
        join_request = get_object_or_404(JoinRequest, user__custom_user_id=request_id, group=group)
        join_request.delete()
        return redirect('snsapp:group_posts', custom_id=custom_id)

class LeaveGroupView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs['custom_id'])
        request.user.groups.remove(group)
        group.users.remove(request.user)
        return redirect('home')
    
class DeleteGroupView(View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs['custom_id'])
        creator = group.users.first()  
        if request.user == creator:
            group.delete()
            return redirect('home')
        else:
            return HttpResponseForbidden("グループの作成者のみ削除を行うことができます。")


class RemoveMemberView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, custom_id=kwargs['custom_id'])
        user_to_remove = get_object_or_404(CustomUser, custom_user_id=kwargs['custom_user_id'])

        if request.user == group.creator and user_to_remove in group.users.all():
            group.users.remove(user_to_remove)
            messages.success(request, f'{user_to_remove.username}をグループから退会させました。')
        else:
            messages.error(request, 'この操作を行う権限がありません。')

        return redirect('snsapp:group_posts', custom_id=kwargs['custom_id'])

class CreatePostView(LoginRequiredMixin, View):
    def get(self, request):
        form = PostForm(user=request.user)
        timeline_posts = Post.objects.filter(user__groups__in=request.user.groups.all()).distinct()
        paginator = Paginator(timeline_posts, 10)
        page = request.GET.get('page')
        posts = paginator.get_page(page)
        context = {
            'form': form,
            'posts': posts,
            'page_number': page,
            'total_pages': paginator.num_pages,
        }
        return render(request, 'post/timeline.html', context)

    def post(self, request):
        form = PostForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            if not post.group:
                last_group = request.user.groups.last()
                if last_group:
                    post.group = last_group
            post.save()
            return redirect('snsapp:timeline')
        else:
            timeline_posts = Post.objects.filter(user__groups__in=request.user.groups.all()).distinct()
            paginator = Paginator(timeline_posts, 10)
            page = request.GET.get('page')
            posts = paginator.get_page(page)
            context = {
                'form': form,
                'posts': posts,
                'page_number': page,
                'total_pages': paginator.num_pages,
            }
            return render(request, 'post/timeline.html', context)

class CreateGroupView(View):
    def get(self, request):
        form = GroupForm()
        return render(request, 'group/create_group.html', {'form': form})
    
    def post(self, request):
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.custom_id = group.generate_unique_id()
            group.is_locked = request.POST.get('is_locked') == 'on'
            group.creator = request.user
            group.save()
            group.users.add(request.user)
            request.user.groups.add(group)
            return redirect('snsapp:group_posts', custom_id=group.custom_id)
        return render(request, 'group/create_group.html', {'form': form})

class SearchGroupView(LoginRequiredMixin,View):
    def get(self, request):
        query = request.GET.get('q', '')
        groups = Group.objects.filter(name__icontains=query)
        for group in groups:
            group.is_member = group.users.filter(custom_user_id=request.user.custom_user_id).exists()
        return render(request, 'group/search_group.html', {'groups': groups, 'query': query})

    def post(self, request, custom_id):
        group = Group.objects.get(custom_id=custom_id)
        request.user.groups.add(group)
        group.users.add(request.user)
        return redirect('snsapp:timeline') 

class SearchProductsView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '')
        selected_group_id = request.GET.get('custom_id')
        user_groups = request.user.groups.all()
        page = request.GET.get('page', 1)

        if query:
            if selected_group_id:
                posts = Post.objects.filter(
                    product_name__icontains=query, 
                    group__id=selected_group_id,
                    group__in=user_groups
                )
            else:
                posts = Post.objects.filter(
                    product_name__icontains=query, 
                    group__in=user_groups
                )
        else:
            posts = []

        paginator = Paginator(posts, 10)
        try:
            object_list = paginator.page(page)
        except PageNotAnInteger:
            object_list = paginator.page(1)
        except EmptyPage:
            object_list = paginator.page(paginator.num_pages)

        context = {
            'query': query,
            'object_list': object_list,
            'user_groups': user_groups,
            'selected_group_id': selected_group_id,
        }
        return render(request, 'post/search_products.html', context)

    def post(self, request):
        if 'delete_post_id' in request.POST:
            post_id = request.POST.get('delete_post_id')
            post = get_object_or_404(Post, id=post_id, user=request.user)
            post.delete()
            return redirect('snsapp:search_products')
    
class SearchCustomersView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '')
        selected_group_id = request.GET.get('custom_id')
        user_groups = request.user.groups.all()
        page = request.GET.get('page', 1)

        if query:
            if selected_group_id:
                customers = Post.objects.filter(
                    customer_category__icontains=query,
                    group__id=selected_group_id,
                    group__in=user_groups
                )
            else:
                customers = Post.objects.filter(
                    customer_category__icontains=query,
                    group__in=user_groups
                )
        else:
            customers = []

        paginator = Paginator(customers, 10)
        try:
            object_list = paginator.page(page)
        except PageNotAnInteger:
            object_list = paginator.page(1)
        except EmptyPage:
            object_list = paginator.page(paginator.num_pages)

        context = {
            'query': query,
            'object_list': object_list,
            'user_groups': user_groups,
            'selected_group_id': selected_group_id,
        }
        return render(request, 'post/search_customers.html', context)

    def post(self, request):
        if 'delete_post_id' in request.POST:
            post_id = request.POST.get('delete_post_id')
            post = get_object_or_404(Post, id=post_id, user=request.user)
            post.delete()
            return redirect('snsapp:search_customers')
        
class SearchUsersView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '')
        page = request.GET.get('page', 1)

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
            'query': query,
            'object_list': object_list,
        }
        return render(request, 'post/search_users.html', context)