from django.urls import path
from .views import (
    Timeline, CreatePostView, MyPost, UploadIconView, GroupPost, UploadGroupIconView, 
    JoinGroupView, JoinGroupRequestView, LeaveGroupView, DeleteGroupView, ToggleGroupLockView, 
    ApproveJoinRequestView, RejectJoinRequestView, CreateGroupView, SearchGroupView, 
    SearchProductsView, SearchCustomersView, SearchUsersView, UpdateUsernameView, RemoveMemberView
)

app_name = 'snsapp'

urlpatterns = [
    path('timeline/', Timeline.as_view(), name='timeline'),
    path('timeline/create/', CreatePostView.as_view(), name='create_post'),
    path('mypost/<str:custom_user_id>/', MyPost.as_view(), name='mypost'),
    path('mypost/<str:custom_user_id>/update_username/', UpdateUsernameView.as_view(), name='update_username'),
    path('upload_icon/', UploadIconView.as_view(), name='upload_icon'),
    path('upload_group_icon/<str:custom_id>/', UploadGroupIconView.as_view(), name='upload_group_icon'),
    path('create_group/', CreateGroupView.as_view(), name='create_group'),
    path('search_group/', SearchGroupView.as_view(), name='search_group'),
    path('search_group/<str:custom_id>/', SearchGroupView.as_view(), name='search_group_post'),
    path('search_products/', SearchProductsView.as_view(), name='search_products'),
    path('search_customers/', SearchCustomersView.as_view(), name='search_customers'),
    path('search_users/', SearchUsersView.as_view(), name='search_users'),
    path('group/<str:custom_id>/', GroupPost.as_view(), name='group_posts'),
    path('group/join/<str:custom_id>/', JoinGroupView.as_view(), name='join_group'),
    path('group/request_join/<str:custom_id>/', JoinGroupRequestView.as_view(), name='request_join_group'),
    path('group/leave/<str:custom_id>/', LeaveGroupView.as_view(), name='leave_group'),
    path('group/delete/<str:custom_id>/', DeleteGroupView.as_view(), name='delete_group'),
    path('group/remove_member/<str:custom_id>/<str:custom_user_id>/', RemoveMemberView.as_view(), name='remove_member'),
    path('toggle_group_lock/<str:custom_id>/', ToggleGroupLockView.as_view(), name='toggle_group_lock'),
    path('approve_join_request/<str:custom_id>/<str:request_id>/', ApproveJoinRequestView.as_view(), name='approve_join_request'),
    path('reject_join_request/<str:custom_id>/<str:request_id>/', RejectJoinRequestView.as_view(), name='reject_join_request'),
]