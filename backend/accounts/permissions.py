from rest_framework.permissions import BasePermission, IsAuthenticated


class IsAuthenticatedUser(IsAuthenticated):
    """Allows a verified user resolved from a MongoDB access token."""


class IsAdministrator(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")


class IsOwnerOrAdministrator(BasePermission):
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, dict):
            owner_id = str(obj.get("user_id", obj.get("owner_id", obj.get("_id", obj.get("id", "")))))
        else:
            owner_id = str(getattr(obj, "user_id", getattr(obj, "owner_id", getattr(obj, "id", ""))))
        return bool(request.user and request.user.is_authenticated and
                    (request.user.role == "admin" or request.user.id == owner_id))
