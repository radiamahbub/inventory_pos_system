from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import Role, User
from config.base_test import BaseAPITestCase


class AuthTests(BaseAPITestCase):
    def login(self, username="admin1", password=None):
        return self.client.post(
            "/api/auth/login/", {"username": username, "password": password or self.password}, format="json"
        )

    def test_login_returns_tokens_and_user_with_role(self):
        r = self.login()
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
        self.assertIn("refresh", r.data)
        self.assertEqual(r.data["user"]["role"], "admin")
        self.assertNotIn("password", r.data["user"])

    def test_login_wrong_password_fails(self):
        self.assertEqual(self.login(password="wrong").status_code, 401)

    def test_inactive_user_cannot_login(self):
        self.cashier.is_active = False
        self.cashier.save()
        self.assertEqual(self.login("cashier1").status_code, 401)

    def test_access_token_works_on_protected_endpoint(self):
        access = self.login().data["access"]
        r = self.client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["username"], "admin1")

    def test_protected_endpoint_requires_login(self):
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)
        self.assertEqual(self.client.get("/api/products/").status_code, 401)

    def test_refresh_returns_new_access_token(self):
        refresh = self.login().data["refresh"]
        r = self.client.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)

    def test_logout_blacklists_refresh_token(self):
        refresh = self.login().data["refresh"]
        r = self.client.post("/api/auth/logout/", {"refresh": refresh}, format="json")
        self.assertEqual(r.status_code, 205)
        again = self.client.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(again.status_code, 401)

    def test_logout_with_invalid_token_returns_400(self):
        r = self.client.post("/api/auth/logout/", {"refresh": "not-a-token"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_change_password(self):
        self.client.force_authenticate(self.cashier)
        bad = self.client.post(
            "/api/auth/change-password/", {"old_password": "nope", "new_password": "NewStrong#2026"}, format="json"
        )
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post(
            "/api/auth/change-password/",
            {"old_password": self.password, "new_password": "NewStrong#2026"},
            format="json",
        )
        self.assertEqual(ok.status_code, 200)
        self.cashier.refresh_from_db()
        self.assertTrue(self.cashier.check_password("NewStrong#2026"))


class UserManagementTests(BaseAPITestCase):
    def test_cashier_cannot_manage_users(self):
        self.as_cashier()
        self.assertEqual(self.client.get("/api/users/").status_code, 403)
        r = self.client.post("/api/users/", {"username": "x", "password": "StrongPass123!"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_admin_can_create_user_with_role(self):
        self.as_admin()
        r = self.client.post(
            "/api/users/",
            {"username": "newcashier", "password": "StrongPass123!", "role": "cashier", "email": "n@example.com"},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertNotIn("password", r.data)
        user = User.objects.get(username="newcashier")
        self.assertEqual(user.role, Role.CASHIER)
        self.assertTrue(user.check_password("StrongPass123!"))

    def test_weak_password_rejected(self):
        self.as_admin()
        r = self.client.post("/api/users/", {"username": "weak", "password": "123"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("password", r.data)

    def test_duplicate_username_rejected(self):
        self.as_admin()
        r = self.client.post("/api/users/", {"username": "cashier1", "password": "StrongPass123!"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_filter_users_by_role(self):
        self.as_admin()
        r = self.client.get("/api/users/?role=cashier")
        self.assertEqual([u["username"] for u in r.data["results"]], ["cashier1"])
        self.assertEqual(self.client.get("/api/users/?role=boss").status_code, 400)

    def test_admin_can_update_role_and_reset_password(self):
        self.as_admin()
        r = self.client.patch(
            f"/api/users/{self.cashier.pk}/", {"role": "admin", "password": "ResetPass#2026"}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.cashier.refresh_from_db()
        self.assertEqual(self.cashier.role, Role.ADMIN)
        self.assertTrue(self.cashier.check_password("ResetPass#2026"))

    def test_admin_cannot_delete_self(self):
        self.as_admin()
        self.assertEqual(self.client.delete(f"/api/users/{self.admin.pk}/").status_code, 400)

    def test_cannot_demote_or_deactivate_last_admin(self):
        self.as_admin()
        r = self.client.patch(f"/api/users/{self.admin.pk}/", {"role": "cashier"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client.patch(f"/api/users/{self.admin.pk}/", {"is_active": False}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_admin_can_delete_cashier_without_records(self):
        self.as_admin()
        self.assertEqual(self.client.delete(f"/api/users/{self.cashier.pk}/").status_code, 204)

    def test_cannot_delete_user_with_records(self):
        self.make_product(stock=5)  # movement created_by admin
        other = User.objects.create_user("admin2", password=self.password, role=Role.ADMIN)
        self.client.force_authenticate(other)
        r = self.client.delete(f"/api/users/{self.admin.pk}/")
        self.assertEqual(r.status_code, 400)
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())


class SuperuserRoleTests(APITestCase):
    def test_createsuperuser_gets_admin_role(self):
        user = User.objects.create_superuser("root", "root@example.com", "StrongPass123!")
        self.assertEqual(user.role, Role.ADMIN)


class RegistrationTests(BaseAPITestCase):
    url = "/api/auth/register/"

    def setUp(self):
        super().setUp()
        cache.clear()  # throttle counter রিসেট

    def payload(self, **kw):
        data = {
            "username": "rahim",
            "first_name": "Rahim",
            "last_name": "Uddin",
            "email": "rahim@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
        }
        data.update(kw)
        return data

    def login(self, username="rahim"):
        return self.client.post("/api/auth/login/", {"username": username, "password": "StrongPass123!"}, format="json")

    def test_register_creates_inactive_cashier_awaiting_approval(self):
        r = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.data["requires_approval"])
        self.assertNotIn("password", r.data["user"])
        user = User.objects.get(username="rahim")
        self.assertEqual(user.role, Role.CASHIER)
        self.assertFalse(user.is_active)
        self.assertTrue(user.check_password("StrongPass123!"))

    def test_pending_user_cannot_login_until_admin_approves(self):
        self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(self.login().status_code, 401)

        self.as_admin()
        pending = User.objects.get(username="rahim")
        self.assertEqual(self.client.patch(f"/api/users/{pending.pk}/", {"is_active": True}, format="json").status_code, 200)

        self.client.force_authenticate(None)
        self.assertEqual(self.login().status_code, 200)

    def test_role_in_payload_is_ignored(self):
        r = self.client.post(self.url, self.payload(role="admin", is_active=True, is_superuser=True), format="json")
        self.assertEqual(r.status_code, 201)
        user = User.objects.get(username="rahim")
        self.assertEqual(user.role, Role.CASHIER)
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_superuser)

    @override_settings(SELF_REGISTRATION_AUTO_APPROVE=True)
    def test_auto_approve_setting_activates_account(self):
        r = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertFalse(r.data["requires_approval"])
        self.assertEqual(self.login().status_code, 200)

    def test_duplicate_username_is_case_insensitive(self):
        r = self.client.post(self.url, self.payload(username="CASHIER1"), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("username", r.data)

    def test_password_mismatch_and_weak_password_rejected(self):
        mismatch = self.client.post(self.url, self.payload(confirm_password="Different#123"), format="json")
        self.assertEqual(mismatch.status_code, 400)
        self.assertIn("confirm_password", mismatch.data)
        weak = self.client.post(self.url, self.payload(password="123", confirm_password="123"), format="json")
        self.assertEqual(weak.status_code, 400)
        self.assertIn("password", weak.data)
        self.assertFalse(User.objects.filter(username="rahim").exists())

    def test_first_name_required(self):
        r = self.client.post(self.url, self.payload(first_name=""), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("first_name", r.data)

    @override_settings(SELF_REGISTRATION_ENABLED=False)
    def test_registration_can_be_disabled(self):
        r = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(r.status_code, 403)
        status = self.client.get("/api/auth/registration-status/")
        self.assertEqual(status.status_code, 200)
        self.assertFalse(status.data["enabled"])
        self.assertFalse(User.objects.filter(username="rahim").exists())

    def test_registration_status_is_public(self):
        r = self.client.get("/api/auth/registration-status/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["enabled"])
        self.assertTrue(r.data["requires_approval"])

    def test_register_ignores_invalid_auth_header(self):
        r = self.client.post(self.url, self.payload(), format="json", HTTP_AUTHORIZATION="Bearer expired.token.value")
        self.assertEqual(r.status_code, 201)
