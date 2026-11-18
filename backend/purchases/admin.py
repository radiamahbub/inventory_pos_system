from django.contrib import admin

from .models import Purchase, PurchaseItem


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0
    can_delete = False
    readonly_fields = ("product", "quantity", "unit_price", "line_total")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("reference_no", "supplier", "purchase_date", "total_amount", "created_by")
    search_fields = ("reference_no", "supplier__name")
    inlines = [PurchaseItemInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
