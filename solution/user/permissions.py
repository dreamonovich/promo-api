from rest_framework.permissions import BasePermission

from user.models import User


def get_user(uuid) -> User:
    return User.objects.get(uuid=uuid)

class IsUserAuthenticated(BasePermission):

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.model_type == "USER"