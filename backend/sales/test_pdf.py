"""PDF invoice and 80 mm receipt."""

import unittest

from accounts.models import Role, User
from config.base_test import BaseAPITestCase
from customers.models import Customer

try:
    import reportlab  # noqa: F401
except ImportError:  # pragma: no cover
    reportlab = None


@unittest.skipIf(reportlab is None, "reportlab is not installed")
class PdfTests(BaseAPITestCase):
    def setUp(self):
        self.product = self.make_product(sku="PDF-1", name="Tea & Biscuit <b>", price="45.50", stock=10)
        self.as_cashier()
        customer = Customer.objects.create(name="Nasrin", phone="01800000000")
        r = self.client.post(
            "/api/sales/",
            {
                "payment_method": "cash", "customer": customer.pk, "paid_amount": "20.00", "note": "Gift & wrap",
                "items": [{"product": self.product.pk, "quantity": 2}],
            },
            format="json",
        )
        self.sale = r.data

    def test_invoice_pdf(self):
        r = self.client.get(f"/api/sales/{self.sale['id']}/invoice-pdf/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))
        self.assertIn(self.sale["invoice_number"], r["Content-Disposition"])

    def test_receipt_pdf_is_80mm_wide(self):
        r = self.client.get(f"/api/sales/{self.sale['id']}/receipt-pdf/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b"%PDF"))
        # 80 mm = 226.77 pt
        self.assertIn(b"226.7", r.content)

    def test_pdf_after_a_return_still_renders(self):
        item = self.sale["items"][0]["id"]
        self.client.post(f"/api/sales/{self.sale['id']}/returns/", {"items": [{"sale_item": item, "quantity": 1}]}, format="json")
        self.assertEqual(self.client.get(f"/api/sales/{self.sale['id']}/invoice-pdf/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/sales/{self.sale['id']}/receipt-pdf/").status_code, 200)

    def test_other_cashier_cannot_download(self):
        other = User.objects.create_user("cashier9", password=self.password, role=Role.CASHIER)
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(f"/api/sales/{self.sale['id']}/invoice-pdf/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/sales/{self.sale['id']}/receipt-pdf/").status_code, 404)

    def test_shop_info_endpoint(self):
        r = self.client.get("/api/shop/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("name", r.data)
