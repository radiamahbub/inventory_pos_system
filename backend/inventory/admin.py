from django.contrib import admin

from .models import StockMovement


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("created_at", "product", "movement_type", "quantity_change", "quantity_after", "reference")
    list_filter = ("movement_type",)
    search_fields = ("product__name", "product__sku", "reference")

    # ইতিহাস অপরিবর্তনীয়: admin panel থেকেও বদলানো/মোছা যাবে না
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
