"""Sales returns / refunds."""

from decimal import Decimal

from accounts.models import Role, User
from config.base_test import BaseAPITestCase
from inventory.models import MovementType, StockMovement
from sales.models import Sale


def D(value):
    return Decimal(str(value))


class SaleReturnTests(BaseAPITestCase):
    def setUp(self):
        self.product = self.make_product(sku="R1", name="Oil", cost="60.00", price="100.00", stock=20)

    def make_sale(self, qty=2, **extra):
        body = {"payment_method": "cash", "items": [{"product": self.product.pk, "quantity": qty}]}
        body.update(extra)
        r = self.client.post("/api/sales/", body, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def do_return(self, sale, qty, **extra):
        body = {"items": [{"sale_item": sale["items"][0]["id"], "quantity": qty}]}
        body.update(extra)
        return self.client.post(f"/api/sales/{sale['id']}/returns/", body, format="json")

    def test_full_return_refunds_and_restores_stock(self):
        self.as_cashier()
        sale = self.make_sale(2)  # stock 18
        r = self.do_return(sale, 2, reason="Wrong item")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(r.data["return_number"].startswith("RET-"))
        self.assertEqual(D(r.data["total_amount"]), D("200.00"))
        self.assertEqual(r.data["refund_method"], "cash")  # defaults to the original payment method
        self.assertEqual(r.data["reason"], "Wrong item")

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 20)
        move = StockMovement.objects.get(movement_type=MovementType.RETURN)
        self.assertEqual((move.quantity_change, move.reference, move.created_by), (2, r.data["return_number"], self.cashier))

        detail = self.client.get(f"/api/sales/{sale['id']}/").data
        self.assertEqual(detail["return_status"], "full")
        self.assertEqual(D(detail["returned_total"]), D("200.00"))
        self.assertEqual(D(detail["net_total"]), D("0.00"))
        self.assertEqual(detail["items"][0]["returned_quantity"], 2)
        self.assertEqual(detail["items"][0]["returnable_quantity"], 0)
        self.assertEqual(len(detail["returns"]), 1)

    def test_partial_returns_accumulate_and_cannot_exceed_quantity(self):
        self.as_cashier()
        sale = self.make_sale(3)
        self.assertEqual(self.do_return(sale, 1).status_code, 201)
        self.assertEqual(self.client.get(f"/api/sales/{sale['id']}/").data["return_status"], "partial")
        over = self.do_return(sale, 3)
        self.assertEqual(over.status_code, 400)
        self.assertIn("left to return", over.data["items"][0])
        self.assertEqual(self.do_return(sale, 2).status_code, 201)
        self.assertEqual(self.client.get(f"/api/sales/{sale['id']}/").data["return_status"], "full")
        self.assertEqual(self.do_return(sale, 1).status_code, 400)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 20)

    def test_invoice_discount_is_spread_over_returned_items(self):
        self.as_cashier()
        sale = self.make_sale(2, discount="20.00")  # subtotal 200, total 180
        self.assertEqual(D(self.do_return(sale, 1).data["total_amount"]), D("90.00"))
        self.assertEqual(D(self.do_return(sale, 1).data["total_amount"]), D("90.00"))
        detail = self.client.get(f"/api/sales/{sale['id']}/").data
        self.assertEqual(D(detail["returned_total"]), D("180.00"))  # never more than the grand total

    def test_rounding_never_refunds_more_than_grand_total(self):
        p = self.make_product(sku="R3", name="Odd", price="10.00", stock=10)
        self.as_cashier()
        r = self.client.post(
            "/api/sales/", {"payment_method": "cash", "discount": "0.01", "items": [{"product": p.pk, "quantity": 3}]}, format="json"
        )
        sale = r.data  # subtotal 30.00, total 29.99
        item = sale["items"][0]["id"]
        for _ in range(3):
            self.client.post(f"/api/sales/{sale['id']}/returns/", {"items": [{"sale_item": item, "quantity": 1}]}, format="json")
        self.assertEqual(D(self.client.get(f"/api/sales/{sale['id']}/").data["returned_total"]), D("29.99"))

    def test_refund_method_can_be_chosen(self):
        self.as_cashier()
        sale = self.make_sale(1)
        self.assertEqual(self.do_return(sale, 1, refund_method="mobile_banking").data["refund_method"], "mobile_banking")
        sale2 = self.make_sale(1)
        self.assertEqual(self.do_return(sale2, 1, refund_method="bitcoin").status_code, 400)

    def test_item_from_another_invoice_is_rejected(self):
        self.as_cashier()
        a, b = self.make_sale(1), self.make_sale(1)
        r = self.client.post(
            f"/api/sales/{a['id']}/returns/", {"items": [{"sale_item": b["items"][0]["id"], "quantity": 1}]}, format="json"
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("does not belong", r.data["items"][0])

    def test_duplicate_item_lines_and_empty_items_are_rejected(self):
        self.as_cashier()
        sale = self.make_sale(3)
        item = sale["items"][0]["id"]
        dup = self.client.post(
            f"/api/sales/{sale['id']}/returns/",
            {"items": [{"sale_item": item, "quantity": 1}, {"sale_item": item, "quantity": 1}]}, format="json",
        )
        self.assertEqual(dup.status_code, 400)
        self.assertEqual(self.client.post(f"/api/sales/{sale['id']}/returns/", {"items": []}, format="json").status_code, 400)
        self.assertEqual(self.do_return(sale, 0).status_code, 400)

    def test_failed_return_changes_nothing(self):
        self.as_cashier()
        sale = self.make_sale(1)
        self.do_return(sale, 5)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 19)
        self.assertFalse(StockMovement.objects.filter(movement_type=MovementType.RETURN).exists())
        self.assertEqual(Sale.objects.get(pk=sale["id"]).returned_total, 0)

    def test_cashier_cannot_return_another_cashiers_sale_but_admin_can(self):
        self.as_cashier()
        sale = self.make_sale(1)
        other = User.objects.create_user("cashier2", password=self.password, role=Role.CASHIER)
        self.client.force_authenticate(other)
        self.assertEqual(self.do_return(sale, 1).status_code, 404)
        self.as_admin()
        self.assertEqual(self.do_return(sale, 1).status_code, 201)

    def test_login_required(self):
        self.assertEqual(self.client.post("/api/sales/1/returns/", {}, format="json").status_code, 401)
        self.assertEqual(self.client.get("/api/returns/").status_code, 401)

    def test_returns_list_is_scoped_by_role_and_filterable(self):
        self.as_cashier()
        sale = self.make_sale(2)
        self.do_return(sale, 1)
        other = User.objects.create_user("cashier3", password=self.password, role=Role.CASHIER)
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get("/api/returns/").data["count"], 0)
        self.as_cashier()
        self.assertEqual(self.client.get("/api/returns/").data["count"], 1)
        self.as_admin()
        row = self.client.get("/api/returns/").data["results"][0]
        self.assertEqual(row["invoice_number"], sale["invoice_number"])
        self.assertEqual(self.client.get("/api/returns/", {"sale": sale["id"]}).data["count"], 1)
        self.assertEqual(self.client.get("/api/returns/", {"search": sale["invoice_number"]}).data["count"], 1)
        self.assertEqual(len(self.client.get(f"/api/returns/{row['id']}/").data["items"]), 1)

    def test_sales_list_filters_by_return_status(self):
        self.as_cashier()
        s1, s2 = self.make_sale(1), self.make_sale(1)
        self.do_return(s1, 1)
        self.assertEqual(self.client.get("/api/sales/", {"return_status": "full"}).data["count"], 1)
        self.assertEqual(self.client.get("/api/sales/", {"return_status": "none"}).data["count"], 1)
        self.assertEqual(self.client.get("/api/sales/", {"return_status": "weird"}).data["count"], 0)

    def test_reports_subtract_returns_and_reverse_cost(self):
        self.as_cashier()
        sale = self.make_sale(2)  # sales 200, cost 120
        self.do_return(sale, 1)  # return 100, cost 60
        self.as_admin()
        r = self.client.get("/api/reports/sales/daily/")
        self.assertEqual(D(r.data["grand_total"]), D("200.00"))
        self.assertEqual(D(r.data["returns_total"]), D("100.00"))
        self.assertEqual(D(r.data["net_sales"]), D("100.00"))
        self.assertEqual(D(r.data["cost_of_goods_sold"]), D("60.00"))
        self.assertEqual(D(r.data["estimated_profit"]), D("40.00"))
        summary = self.client.get("/api/reports/summary/").data
        self.assertEqual((D(summary["net_sales"]), D(summary["estimated_profit"])), (D("100.00"), D("40.00")))

    def test_stock_movement_history_shows_return(self):
        self.as_cashier()
        self.do_return(self.make_sale(1), 1)
        self.as_admin()
        r = self.client.get("/api/inventory/movements/", {"movement_type": "return"})
        self.assertEqual(r.data["count"], 1)
