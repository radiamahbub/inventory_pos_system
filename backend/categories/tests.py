from categories.models import Category
from config.base_test import BaseAPITestCase


class CategoryTests(BaseAPITestCase):
    def test_admin_crud(self):
        self.as_admin()
        r = self.client.post("/api/categories/", {"name": "Beverages", "description": "Drinks"}, format="json")
        self.assertEqual(r.status_code, 201)
        pk = r.data["id"]
        r = self.client.patch(f"/api/categories/{pk}/", {"name": "Drinks"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["name"], "Drinks")
        self.assertEqual(self.client.get("/api/categories/").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/categories/{pk}/").status_code, 204)

    def test_name_must_be_unique_case_insensitive(self):
        self.as_admin()
        r = self.client.post("/api/categories/", {"name": "general"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("name", r.data)

    def test_can_update_category_without_changing_name(self):
        self.as_admin()
        r = self.client.patch(f"/api/categories/{self.category.pk}/", {"description": "x"}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_blank_name_rejected(self):
        self.as_admin()
        self.assertEqual(self.client.post("/api/categories/", {"name": "   "}, format="json").status_code, 400)

    def test_cashier_is_read_only(self):
        self.as_cashier()
        self.assertEqual(self.client.get("/api/categories/").status_code, 200)
        self.assertEqual(self.client.post("/api/categories/", {"name": "X"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/categories/{self.category.pk}/").status_code, 403)

    def test_cannot_delete_category_with_products(self):
        self.make_product()
        self.as_admin()
        r = self.client.delete(f"/api/categories/{self.category.pk}/")
        self.assertEqual(r.status_code, 409)
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_list_includes_product_count_and_search(self):
        self.make_product()
        Category.objects.create(name="Snacks")
        self.as_admin()
        r = self.client.get("/api/categories/?search=gen")
        self.assertEqual(len(r.data["results"]), 1)
        self.assertEqual(r.data["results"][0]["product_count"], 1)
