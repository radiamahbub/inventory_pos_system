from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "selling_price", "stock_quantity", "min_stock_level", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "sku")
    readonly_fields = ("stock_quantity",)
