import datetime
from decimal import Decimal

from django.utils import timezone

from config.base_test import BaseAPITestCase
from purchases.services import create_purchase
from sales.models import Sale
from sales.services import create_sale
from suppliers.models import Supplier


def dhaka(y, m, d, hour=12):
    return timezone.make_aware(datetime.datetime(y, m, d, hour, 0))


class ReportTests(BaseAPITestCase):
    def make_sale(self, product, qty, when=None, discount="0", method="cash"):
        sale = create_sale(
            customer=None, items=[{"product": product, "quantity": qty}], discount=Decimal(discount),
            payment_method=method, note="", user=self.cashier,
        )
        if when:
            Sale.objects.filter(pk=sale.pk).update(sale_date=when)
        return sale

    def setUp(self):
        self.product = self.make_product(cost="50.00", price="80.00", stock=100)

    def test_reports_are_admin_only(self):
        self.as_cashier()
        for url in (
            "/api/reports/sales/daily/", "/api/reports/sales/monthly/", "/api/reports/sales/yearly/",
            "/api/reports/summary/", "/api/reports/low-stock/", "/api/dashboard/",
        ):
            self.assertEqual(self.client.get(url).status_code, 403, url)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/reports/summary/").status_code, 401)

    def test_daily_report_totals_and_profit(self):
        self.make_sale(self.product, 2, discount="10.00", method="cash")  # 160-10 = 150, cost 100
        self.make_sale(self.product, 1, method="card")  # 80, cost 50
        self.make_sale(self.product, 5, when=dhaka(2020, 1, 1))  # another day
        self.as_admin()
        r = self.client.get("/api/reports/sales/daily/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["sales_count"], 2)
        self.assertEqual(Decimal(r.data["subtotal"]), Decimal("240.00"))
        self.assertEqual(Decimal(r.data["discount"]), Decimal("10.00"))
        self.assertEqual(Decimal(r.data["grand_total"]), Decimal("230.00"))
        self.assertEqual(Decimal(r.data["cost_of_goods_sold"]), Decimal("150.00"))
        self.assertEqual(Decimal(r.data["estimated_profit"]), Decimal("80.00"))
        methods = {m["payment_method"]: Decimal(m["total"]) for m in r.data["payment_methods"]}
        self.assertEqual(methods, {"cash": Decimal("150.00"), "card": Decimal("80.00")})

    def test_daily_report_for_specific_date_and_empty_day(self):
        self.make_sale(self.product, 1, when=dhaka(2026, 3, 15))
        self.as_admin()
        r = self.client.get("/api/reports/sales/daily/?date=2026-03-15")
        self.assertEqual(r.data["sales_count"], 1)
        r = self.client.get("/api/reports/sales/daily/?date=2026-03-16")
        self.assertEqual(r.data["sales_count"], 0)
        self.assertEqual(Decimal(r.data["grand_total"]), Decimal("0.00"))
        self.assertEqual(self.client.get("/api/reports/sales/daily/?date=15-03-2026").status_code, 400)

    def test_late_night_sale_counts_on_local_dhaka_date(self):
        # 00:00 Dhaka on the 16th is 18:00 UTC on the 15th: it must still count as the 16th (local date).
        self.make_sale(self.product, 1, when=dhaka(2026, 3, 16, 0))
        self.as_admin()
        self.assertEqual(self.client.get("/api/reports/sales/daily/?date=2026-03-16").data["sales_count"], 1)
        self.assertEqual(self.client.get("/api/reports/sales/daily/?date=2026-03-15").data["sales_count"], 0)

    def test_monthly_report(self):
        self.make_sale(self.product, 1, when=dhaka(2026, 3, 15))
        self.make_sale(self.product, 2, when=dhaka(2026, 3, 15))
        self.make_sale(self.product, 1, when=dhaka(2026, 3, 20))
        self.make_sale(self.product, 1, when=dhaka(2026, 4, 1))
        self.as_admin()
        r = self.client.get("/api/reports/sales/monthly/?year=2026&month=3")
        self.assertEqual(r.data["sales_count"], 3)
        self.assertEqual(Decimal(r.data["grand_total"]), Decimal("320.00"))
        self.assertEqual(
            [(d["day"], d["sales_count"], Decimal(d["grand_total"])) for d in r.data["daily"]],
            [(15, 2, Decimal("240.00")), (20, 1, Decimal("80.00"))],
        )
        self.assertEqual(self.client.get("/api/reports/sales/monthly/?month=13").status_code, 400)
        self.assertEqual(self.client.get("/api/reports/sales/monthly/?year=abc").status_code, 400)

    def test_yearly_report(self):
        self.make_sale(self.product, 1, when=dhaka(2026, 3, 15))
        self.make_sale(self.product, 1, when=dhaka(2026, 4, 1))
        self.make_sale(self.product, 1, when=dhaka(2026, 4, 2))
        self.make_sale(self.product, 1, when=dhaka(2025, 12, 31))
        self.as_admin()
        r = self.client.get("/api/reports/sales/yearly/?year=2026")
        self.assertEqual(r.data["sales_count"], 3)
        self.assertEqual([(m["month"], m["sales_count"]) for m in r.data["monthly"]], [(3, 1), (4, 2)])
        self.assertEqual(Decimal(r.data["estimated_profit"]), Decimal("90.00"))

    def test_financial_summary_total_sales_purchases_profit(self):
        supplier = Supplier.objects.create(name="S")
        create_purchase(
            supplier=supplier, purchase_date=timezone.localdate(), note="",
            items=[{"product": self.product, "quantity": 10, "unit_price": Decimal("50.00")}], user=self.admin,
        )
        self.make_sale(self.product, 3)  # revenue 240, cost 150
        self.as_admin()
        r = self.client.get("/api/reports/summary/")
        self.assertEqual(Decimal(r.data["total_sales"]), Decimal("240.00"))
        self.assertEqual(Decimal(r.data["total_purchases"]), Decimal("500.00"))
        self.assertEqual(Decimal(r.data["estimated_profit"]), Decimal("90.00"))
        self.assertEqual(r.data["purchases_count"], 1)

    def test_financial_summary_date_range(self):
        self.make_sale(self.product, 1, when=dhaka(2026, 1, 10))
        self.make_sale(self.product, 1, when=dhaka(2026, 2, 10))
        self.as_admin()
        r = self.client.get("/api/reports/summary/?start_date=2026-02-01&end_date=2026-02-28")
        self.assertEqual(r.data["sales_count"], 1)
        bad = self.client.get("/api/reports/summary/?start_date=2026-03-01&end_date=2026-02-01")
        self.assertEqual(bad.status_code, 400)

    def test_low_stock_report(self):
        self.make_product(sku="L1", name="Low", stock=2, min_stock=10)
        self.as_admin()
        r = self.client.get("/api/reports/low-stock/")
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(r.data["results"][0]["name"], "Low")
        self.assertEqual(r.data["results"][0]["shortage"], 8)


class DashboardTests(BaseAPITestCase):
    def test_dashboard_numbers(self):
        from customers.models import Customer

        product = self.make_product(cost="10.00", price="25.00", stock=3, min_stock=5)
        Supplier.objects.create(name="S")
        Customer.objects.create(name="C")
        self.client.force_authenticate(self.cashier)
        self.client.post(
            "/api/sales/", {"payment_method": "cash", "items": [{"product": product.pk, "quantity": 2}]}, format="json"
        )
        self.as_admin()
        r = self.client.get("/api/dashboard/")
        self.assertEqual(r.status_code, 200)
        d = r.data
        self.assertEqual(
            (d["total_products"], d["total_categories"], d["total_customers"], d["total_suppliers"]), (1, 1, 1, 1)
        )
        self.assertEqual(d["today_sales"]["sales_count"], 1)
        self.assertEqual(Decimal(d["today_sales"]["total"]), Decimal("50.00"))
        self.assertEqual(Decimal(d["monthly_sales"]["total"]), Decimal("50.00"))
        self.assertEqual(d["low_stock_count"], 1)
        self.assertEqual(d["low_stock_products"][0]["stock_quantity"], 1)
        self.assertEqual(len(d["recent_sales"]), 1)

    def test_dashboard_empty_database(self):
        self.as_admin()
        r = self.client.get("/api/dashboard/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["today_sales"]["sales_count"], 0)
        self.assertEqual(Decimal(r.data["monthly_sales"]["total"]), Decimal("0.00"))
        self.assertEqual(r.data["recent_sales"], [])
