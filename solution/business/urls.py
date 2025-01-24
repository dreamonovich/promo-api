from django.urls import path

from .views import RegisterBusinessView, LoginBusinessView, PromocodeCreateListView, RetrieveUpdatePromocodeView, \
    PromocodeStatisticsView

urlpatterns = [
    path("auth/sign-up", RegisterBusinessView.as_view(), name='business-sign-up'),
    path("auth/sign-in", LoginBusinessView.as_view()),
    path("promo", PromocodeCreateListView.as_view()),
    path("promo/<str:uuid>", RetrieveUpdatePromocodeView.as_view()),
    path("promo/<str:uuid>/stat", PromocodeStatisticsView.as_view()),
]