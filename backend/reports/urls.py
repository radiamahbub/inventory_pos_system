from django.urls import path

from .views import (
    DailySalesReportView,
    FinancialSummaryView,
    LowStockReportView,
    MonthlySalesReportView,
    YearlySalesReportView,
)

urlpatterns = [
    path("sales/daily/", DailySalesReportView.as_view(), name="report-sales-daily"),
    path("sales/monthly/", MonthlySalesReportView.as_view(), name="report-sales-monthly"),
    path("sales/yearly/", YearlySalesReportView.as_view(), name="report-sales-yearly"),
    path("summary/", FinancialSummaryView.as_view(), name="report-summary"),
    path("low-stock/", LowStockReportView.as_view(), name="report-low-stock"),
]
