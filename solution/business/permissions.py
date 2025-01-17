from rest_framework.permissions import BasePermission
from .models import Business

class IsBusinessAuthenticated(BasePermission):

    def has_permission(self, request, view):
        return request.user.is_authenticated and isinstance(request.user, Business)

class IsPromocodeOwner(BasePermission):

    def has_object_permission(self, request, view, obj):
        return obj.company == request.user
