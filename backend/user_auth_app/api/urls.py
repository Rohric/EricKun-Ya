from django.urls import path

from .views import (
    EmailCheckView,
    LoginView,
    LogoutView,
    RegistrationView,
    UserDetailView,
    UserListView,
    UserProfileDetail,
    UserProfileList,
)

urlpatterns = [
    path("profiles/", UserProfileList.as_view(), name="userprofile-list"),
    path("profiles/<int:pk>/", UserProfileDetail.as_view(), name="userprofile-detail"),
    path("users/", UserListView.as_view()),
    path("users/<int:pk>/", UserDetailView.as_view(), name="user-detail"),
    path("registration/", RegistrationView.as_view(), name="registration"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("email-check/", EmailCheckView.as_view(), name="email-check"),
]
