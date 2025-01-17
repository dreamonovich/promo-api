from django.urls import path

from .views import RegisterBusinessView, LoginBusinessView, PromocodeView, RetrievePromocodeView

urlpatterns = [
    path("auth/sign-up", RegisterBusinessView.as_view()),
    path("auth/sign-in", LoginBusinessView.as_view()),
    path("promo", PromocodeView.as_view()),
    path("promo/<str:uuid>", RetrievePromocodeView.as_view()),
]