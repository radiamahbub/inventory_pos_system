from django.contrib import admin

from .models import Sale, SaleItem, SaleReturn, SaleReturnItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    can_delete = False
    readonly_fields = ("product", "quantity", "unit_price", "unit_cost", "line_total")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "sale_date", "customer", "grand_total", "payment_method", "created_by")
    list_filter = ("payment_method",)
    search_fields = ("invoice_number", "customer__name")
    inlines = [SaleItemInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class SaleReturnItemInline(admin.TabularInline):
    model = SaleReturnItem
    extra = 0
    can_delete = False
    readonly_fields = ("sale_item", "product", "quantity", "unit_price", "unit_cost", "line_total")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SaleReturn)
class SaleReturnAdmin(admin.ModelAdmin):
    list_display = ("return_number", "sale", "return_date", "total_amount", "refund_amount", "due_adjusted")
    search_fields = ("return_number", "sale__invoice_number")
    inlines = [SaleReturnItemInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
