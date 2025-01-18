from django.urls import path
from user.views import RegisterUserView, LoginUserView, RetrieveUpdateUserView

urlpatterns = [
    path("auth/sign-up", RegisterUserView.as_view()),
    path("auth/sign-in", LoginUserView.as_view()),
    path("profile", RetrieveUpdateUserView.as_view()),
]