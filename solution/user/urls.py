from django.urls import path
from user.views import RegisterUserView, LoginUserView, RetrieveUpdateUserView, FeedView, RetrievePromocodeForUserView, \
    LikePromocodeView, CreateListCommentView, RetrieveUpdateDeleteCommentView

urlpatterns = [
    path("auth/sign-up", RegisterUserView.as_view()),
    path("auth/sign-in", LoginUserView.as_view()),
    path("profile", RetrieveUpdateUserView.as_view()),
    path("feed", FeedView.as_view()),
    path("promo/<str:uuid>", RetrievePromocodeForUserView.as_view()),
    path("promo/<str:uuid>/like", LikePromocodeView.as_view()),
    path("promo/<str:uuid>/comments", CreateListCommentView.as_view()),
    path("promo/<str:promo_uuid>/comments/<str:comment_uuid>", RetrieveUpdateDeleteCommentView.as_view()),
]