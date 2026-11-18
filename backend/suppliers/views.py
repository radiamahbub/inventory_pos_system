from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets

from accounts.permissions import IsAdminOrReadOnly

from .models import Supplier
from .serializers import SupplierSerializer


@extend_schema_view(
    list=extend_schema(tags=["Suppliers"]),
    retrieve=extend_schema(tags=["Suppliers"]),
    create=extend_schema(tags=["Suppliers"]),
    update=extend_schema(tags=["Suppliers"]),
    partial_update=extend_schema(tags=["Suppliers"]),
    destroy=extend_schema(tags=["Suppliers"], description="Fails with 409 if the supplier has purchases."),
)
class SupplierViewSet(viewsets.ModelViewSet):
    """Admin: full CRUD. Cashier: read-only."""

    queryset = Supplier.objects.all().order_by("name")
    serializer_class = SupplierSerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ["name", "contact_person", "phone", "email"]
    ordering_fields = ["name", "created_at"]
