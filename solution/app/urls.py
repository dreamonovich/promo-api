from django.urls import path
from django.urls.conf import include

from app import views

a = "api"
urlpatterns = [
    path(f"{a}/ping", views.ping),
    path("api/business/", include("business.urls")),
]
