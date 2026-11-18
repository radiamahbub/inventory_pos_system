from django.urls import path

from .views import StockAdjustmentView

urlpatterns = [
    path("adjust/", StockAdjustmentView.as_view(), name="inventory-adjust"),
]
