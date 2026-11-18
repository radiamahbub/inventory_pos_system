"""Due (credit) sales, customer collections and ledger, and returns on due sales."""

from decimal import Decimal

from accounts.models import Role, User
from config.base_test import BaseAPITestCase
from customers.models import Customer
from inventory.models import MovementType, StockMovement
from sales.models import Sale


def D(value):
    return Decimal(str(value))


class DueSaleTests(BaseAPITestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="Rahim", phone="01711111111")
        self.product = self.make_product(sku="P1", name="Rice", cost="50.00", price="100.00", stock=50)

    def sell(self, qty=1, **extra):
        body = {"payment_method": "cash", "items": [{"product": self.product.pk, "quantity": qty}]}
        body.update(extra)
        return self.client.post("/api/sales/", body, format="json")

    def test_default_is_fully_paid(self):
        self.as_cashier()
        r = self.sell(2)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(D(r.data["paid_amount"]), D("200.00"))
        self.assertEqual(D(r.data["due_amount"]), D("0.00"))
        self.assertEqual(r.data["payment_status"], "paid")

    def test_due_sale_needs_a_customer(self):
        self.as_cashier()
        r = self.sell(2, paid_amount="50.00")
        self.assertEqual(r.status_code, 400)
        self.assertIn("customer", r.data)
        self.assertEqual(Sale.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 50)

    def test_paid_amount_cannot_exceed_total_or_be_negative(self):
        self.as_cashier()
        self.assertEqual(self.sell(1, customer=self.customer.pk, paid_amount="150.00").status_code, 400)
        self.assertEqual(self.sell(1, customer=self.customer.pk, paid_amount="-5").status_code, 400)

    def test_partial_and_unpaid_sales_show_due_and_customer_balance(self):
        self.as_cashier()
        r1 = self.sell(3, customer=self.customer.pk, paid_amount="100.00")  # total 300, due 200
        self.assertEqual(r1.status_code, 201, r1.data)
        self.assertEqual(D(r1.data["due_amount"]), D("200.00"))
        self.assertEqual(r1.data["payment_status"], "partial")
        r2 = self.sell(1, customer=self.customer.pk, paid_amount="0")  # total 100, due 100
        self.assertEqual(r2.data["payment_status"], "unpaid")

        detail = self.client.get(f"/api/customers/{self.customer.pk}/")
        self.assertEqual(D(detail.data["balance"]), D("300.00"))
        due_list = self.client.get("/api/customers/", {"has_due": "true"})
        self.assertEqual([c["id"] for c in due_list.data["results"]], [self.customer.pk])

        only_due = self.client.get("/api/sales/", {"payment_status": "due"})
        self.assertEqual(only_due.data["count"], 2)
        only_unpaid = self.client.get("/api/sales/", {"payment_status": "unpaid"})
        self.assertEqual(only_unpaid.data["count"], 1)

    def test_customer_without_due_is_not_listed_in_has_due(self):
        self.as_cashier()
        self.sell(1, customer=self.customer.pk)  # paid in full
        r = self.client.get("/api/customers/", {"has_due": "true"})
        self.assertEqual(r.data["count"], 0)

    def test_collect_payment_is_applied_to_oldest_invoice_first(self):
        self.as_cashier()
        first = self.sell(2, customer=self.customer.pk, paid_amount="0").data  # due 200
        second = self.sell(1, customer=self.customer.pk, paid_amount="0").data  # due 100
        r = self.client.post(
            f"/api/customers/{self.customer.pk}/payments/", {"amount": "250.00", "payment_method": "cash"}, format="json"
        )
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(r.data["reference"].startswith("PAY-"))

        s1 = Sale.objects.get(pk=first["id"])
        s2 = Sale.objects.get(pk=second["id"])
        self.assertEqual(s1.due_amount, D("0.00"))
        self.assertEqual(s2.due_amount, D("50.00"))
        detail = self.client.get(f"/api/customers/{self.customer.pk}/")
        self.assertEqual(D(detail.data["balance"]), D("50.00"))

    def test_cannot_collect_more_than_due_or_when_nothing_due(self):
        self.as_cashier()
        self.assertEqual(
            self.client.post(f"/api/customers/{self.customer.pk}/payments/", {"amount": "10"}, format="json").status_code,
            400,
        )
        self.sell(1, customer=self.customer.pk, paid_amount="40.00")  # due 60
        r = self.client.post(f"/api/customers/{self.customer.pk}/payments/", {"amount": "61.00"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("amount", r.data)
        self.assertEqual(
            self.client.post(f"/api/customers/{self.customer.pk}/payments/", {"amount": "0"}, format="json").status_code,
            400,
        )

    def test_ledger_has_running_balance_that_matches_customer_balance(self):
        self.as_cashier()
        self.sell(3, customer=self.customer.pk, paid_amount="100.00")  # +300 -100
        self.client.post(f"/api/customers/{self.customer.pk}/payments/", {"amount": "120.00"}, format="json")
        r = self.client.get(f"/api/customers/{self.customer.pk}/ledger/")
        self.assertEqual(r.status_code, 200, r.data)
        entries = r.data["entries"]
        self.assertEqual([e["type"] for e in entries], ["sale", "payment_at_sale", "collection"])
        self.assertEqual([D(e["balance"]) for e in entries], [D("300.00"), D("200.00"), D("80.00")])
        self.assertEqual(D(r.data["balance"]), D("80.00"))
        self.assertEqual(D(r.data["customer"]["balance"]), D("80.00"))

    def test_dashboard_shows_total_due(self):
        self.as_cashier()
        self.sell(2, customer=self.customer.pk, paid_amount="50.00")  # due 150
        self.as_admin()
        r = self.client.get("/api/dashboard/")
        self.assertEqual(D(r.data["total_due"]), D("150.00"))
        self.assertEqual(r.data["customers_with_due"], 1)

    def test_report_payment_breakdown_counts_only_money_received(self):
        self.as_cashier()
        self.sell(2, customer=self.customer.pk, paid_amount="50.00")
        self.as_admin()
        r = self.client.get("/api/reports/sales/daily/")
        methods = {m["payment_method"]: D(m["total"]) for m in r.data["payment_methods"]}
        self.assertEqual(methods["cash"], D("50.00"))


class DueReturnTests(BaseAPITestCase):
    def setUp(self):
        self.customer = Customer.objects.create(name="Karim")
        self.product = self.make_product(sku="R1", name="Oil", cost="60.00", price="100.00", stock=20)

    def make_sale(self, qty=2, **extra):
        body = {"payment_method": "cash", "items": [{"product": self.product.pk, "quantity": qty}]}
        body.update(extra)
        r = self.client.post("/api/sales/", body, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def do_return(self, sale, item_qty, **extra):
        item = sale["items"][0]["id"]
        body = {"items": [{"sale_item": item, "quantity": item_qty}]}
        body.update(extra)
        return self.client.post(f"/api/sales/{sale['id']}/returns/", body, format="json")

    def test_return_on_unpaid_sale_cancels_due_instead_of_refunding(self):
        self.as_cashier()
        sale = self.make_sale(2, customer=self.customer.pk, paid_amount="0")  # due 200
        r = self.do_return(sale, 1)
        self.assertEqual(D(r.data["refund_amount"]), D("0.00"))
        self.assertEqual(D(r.data["due_adjusted"]), D("100.00"))
        self.assertEqual(r.data["refund_method"], "")
        balance = self.client.get(f"/api/customers/{self.customer.pk}/").data["balance"]
        self.assertEqual(D(balance), D("100.00"))

    def test_return_on_partly_paid_sale_refunds_only_the_overpaid_part(self):
        self.as_cashier()
        sale = self.make_sale(2, customer=self.customer.pk, paid_amount="150.00")  # total 200, paid 150, due 50
        r = self.do_return(sale, 1)  # keeps goods worth 100, paid 150 -> refund 50, due 50 cancelled
        self.assertEqual(D(r.data["refund_amount"]), D("50.00"))
        self.assertEqual(D(r.data["due_adjusted"]), D("50.00"))
        balance = self.client.get(f"/api/customers/{self.customer.pk}/").data["balance"]
        self.assertEqual(D(balance), D("0.00"))
        ledger = self.client.get(f"/api/customers/{self.customer.pk}/ledger/").data
        self.assertEqual(D(ledger["entries"][-1]["balance"]), D("0.00"))

    def test_return_after_due_was_collected_refunds_the_collected_money(self):
        self.as_cashier()
        sale = self.make_sale(2, customer=self.customer.pk, paid_amount="0")  # due 200
        self.client.post(f"/api/customers/{self.customer.pk}/payments/", {"amount": "200.00"}, format="json")
        r = self.do_return(sale, 1)
        self.assertEqual(D(r.data["refund_amount"]), D("100.00"))
        self.assertEqual(D(r.data["due_adjusted"]), D("0.00"))
        balance = self.client.get(f"/api/customers/{self.customer.pk}/").data["balance"]
        self.assertEqual(D(balance), D("0.00"))
