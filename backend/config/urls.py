from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter

from accounts.views import UserViewSet
from categories.views import CategoryViewSet
from config.shop import ShopInfoView
from customers.views import CustomerViewSet
from inventory.views import CurrentStockViewSet, StockMovementViewSet
from products.views import ProductViewSet
from purchases.views import PurchaseViewSet
from sales.views import SaleReturnViewSet, SaleViewSet
from suppliers.views import SupplierViewSet


def health_check(request):
    """সার্ভার চালু আছে কিনা দেখার জন্য সহজ endpoint।"""
    return JsonResponse({"status": "ok", "service": "inventory-pos-backend"})


# সব ModelViewSet এক জায়গায় register (DefaultRouter /api/ এ API root পেজও দেয়)
router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("customers", CustomerViewSet, basename="customer")
router.register("purchases", PurchaseViewSet, basename="purchase")
router.register("sales", SaleViewSet, basename="sale")
router.register("returns", SaleReturnViewSet, basename="sale-return")
router.register("inventory/stock", CurrentStockViewSet, basename="inventory-stock")
router.register("inventory/movements", StockMovementViewSet, basename="inventory-movement")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/shop/", ShopInfoView.as_view(), name="shop-info"),
    # Auth
    path("api/auth/", include("accounts.urls")),
    # Business APIs
    path("api/inventory/", include("inventory.urls")),
    path("api/reports/", include("reports.urls")),
    path("api/dashboard/", include("dashboard.urls")),
    path("api/", include(router.urls)),
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
