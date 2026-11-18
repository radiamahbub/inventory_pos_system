from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Role


def _active(user):
    return bool(user and user.is_authenticated and user.is_active)


class IsAdminRole(BasePermission):
    """শুধু Admin।"""

    message = "Only Admin users can perform this action."

    def has_permission(self, request, view):
        return _active(request.user) and request.user.role == Role.ADMIN


class IsAdminOrCashier(BasePermission):
    """Admin অথবা Cashier (লগইন করা যেকোনো বৈধ ইউজার)।"""

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        return _active(request.user) and request.user.role in (Role.ADMIN, Role.CASHIER)


class IsAdminOrReadOnly(BasePermission):
    """পড়া (GET) সবার জন্য, লেখা (POST/PUT/PATCH/DELETE) শুধু Admin-এর জন্য।"""

    message = "Only Admin users can modify this resource."

    def has_permission(self, request, view):
        if not _active(request.user):
            return False
        if request.method in SAFE_METHODS:
            return request.user.role in (Role.ADMIN, Role.CASHIER)
        return request.user.role == Role.ADMIN
