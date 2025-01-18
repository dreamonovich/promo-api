from django.urls import path
from django.urls.conf import include

urlpatterns = [
    path("api/", include("core.urls")),
    path("api/business/", include("business.urls")),
    path("api/user/", include("user.urls")),
]
