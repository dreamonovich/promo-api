from rest_framework.permissions import BasePermission
from .models import Business

def get_user(uuid):
    return Business.objects.get(uuid=uuid)

class IsBusinessAuthenticated(BasePermission):

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.model_type == 'BUSINESS'

class IsPromocodeOwner(BasePermission):

    def has_object_permission(self, request, view, obj):
        return obj.company == get_user(request.user.uuid)
