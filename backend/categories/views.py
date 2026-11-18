from django.db.models import Count
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets

from accounts.permissions import IsAdminOrReadOnly

from .models import Category
from .serializers import CategorySerializer


@extend_schema_view(
    list=extend_schema(tags=["Categories"]),
    retrieve=extend_schema(tags=["Categories"]),
    create=extend_schema(tags=["Categories"]),
    update=extend_schema(tags=["Categories"]),
    partial_update=extend_schema(tags=["Categories"]),
    destroy=extend_schema(tags=["Categories"], description="Fails with 409 if products use this category."),
)
class CategoryViewSet(viewsets.ModelViewSet):
    """Admin: full CRUD. Cashier: read-only."""

    queryset = Category.objects.annotate(product_count=Count("products")).order_by("name")
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
