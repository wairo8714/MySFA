from django.urls import path

from .views import (
    ApproveJoinRequestView,
    CreateGroupView,
    DeleteGroupView,
    GroupPost,
    JoinGroupRequestView,
    JoinGroupView,
    LeaveGroupView,
    LikePostView,
    MyPost,
    RejectJoinRequestView,
    RemoveMemberView,
    SalesReportView,
    SearchCustomersView,
    SearchGroupView,
    SearchProductsView,
    SearchUsersView,
    TestReportView,
    Timeline,
    ToggleGroupLockView,
    UpdateUsernameView,
    UploadGroupIconView,
    UploadIconView,
)

app_name = "mysfa"

urlpatterns = [
    path("timeline/", Timeline.as_view(), name="timeline"),
    path("mypost/<str:custom_user_id>/", MyPost.as_view(), name="mypost"),
    path(
        "mypost/<str:custom_user_id>/update_username/",
        UpdateUsernameView.as_view(),
        name="update_username",
    ),
    path("upload_icon/", UploadIconView.as_view(), name="upload_icon"),
    path(
        "upload_group_icon/<str:custom_id>/",
        UploadGroupIconView.as_view(),
        name="upload_group_icon",
    ),
    path("create_group/", CreateGroupView.as_view(), name="create_group"),
    path("search_group/", SearchGroupView.as_view(), name="search_group"),
    path(
        "search_group/<str:custom_id>/",
        SearchGroupView.as_view(),
        name="search_group_post",
    ),
    path("group/<str:custom_id>/", GroupPost.as_view(), name="group_posts"),
    path("group/join/<str:custom_id>/", JoinGroupView.as_view(), name="join_group"),
    path(
        "group/request_join/<str:custom_id>/",
        JoinGroupRequestView.as_view(),
        name="request_join_group",
    ),
    path("group/leave/<str:custom_id>/", LeaveGroupView.as_view(), name="leave_group"),
    path(
        "group/delete/<str:custom_id>/", DeleteGroupView.as_view(), name="delete_group"
    ),
    path(
        "group/remove_member/<str:custom_id>/<str:custom_user_id>/",
        RemoveMemberView.as_view(),
        name="remove_member",
    ),
    path(
        "toggle_group_lock/<str:custom_id>/",
        ToggleGroupLockView.as_view(),
        name="toggle_group_lock",
    ),
    path(
        "approve_join_request/<str:custom_id>/<str:request_id>/",
        ApproveJoinRequestView.as_view(),
        name="approve_join_request",
    ),
    path(
        "reject_join_request/<str:custom_id>/<str:request_id>/",
        RejectJoinRequestView.as_view(),
        name="reject_join_request",
    ),
    path("search_products/", SearchProductsView.as_view(), name="search_products"),
    path("search_customers/", SearchCustomersView.as_view(), name="search_customers"),
    path("search_users/", SearchUsersView.as_view(), name="search_users"),
    path("like-post/<int:post_id>/", LikePostView.as_view(), name="like_post"),
    path("test-report/", TestReportView.as_view(), name="test_report"),
    path("sales-report/", SalesReportView.as_view(), name="sales_report"),
    path(
        "sales-report/<str:user_id>/",
        SalesReportView.as_view(),
        name="user_sales_report",
    ),
    path(
        "sales-report/group/<str:group_id>/",
        SalesReportView.as_view(),
        name="group_sales_report",
    ),
]
