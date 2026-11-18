from rest_framework.permissions import BasePermission

from accounts.models import Role


class CustomerPermission(BasePermission):
    """Cashier customer তৈরি/দেখা/আপডেট করতে পারে (POS-এ লাগে); delete শুধু Admin।"""

    message = "Only Admin users can delete customers."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_active):
            return False
        if request.method == "DELETE":
            return user.role == Role.ADMIN
        return user.role in (Role.ADMIN, Role.CASHIER)
