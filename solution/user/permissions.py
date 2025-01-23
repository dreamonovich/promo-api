from rest_framework.permissions import BasePermission

from user.models import User


def get_user(uuid) -> User:
    return User.objects.get(uuid=uuid)

class IsUserAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.model_type == "USER"

class IsCommentOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method == "GET":
            return False
        return obj.user == get_user(request.user.uuid)
