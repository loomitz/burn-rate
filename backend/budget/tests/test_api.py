from datetime import date

from django.contrib.auth.models import User
from django.core import mail
from django.test import override_settings
from rest_framework.test import APITestCase

from budget.models import Account, Category, HouseholdMember, InstallmentPlan, Invitation, MerchantConcept, RecurringExpense


class BudgetApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )
        self.client.login(username="admin", password="testpass123")
        self.member = HouseholdMember.objects.create(name="Ana")
        self.account = Account.objects.create(name="Caja", account_type=Account.AccountType.CASH)
        self.category = Category.objects.create(
            name="Super",
            scope=Category.Scope.GLOBAL,
            monthly_budget_cents=200000,
        )

    def test_requires_login(self):
        self.client.logout()

        response = self.client.get("/api/categories/")

        self.assertEqual(response.status_code, 403)

    def test_auth_me_returns_null_without_session(self):
        self.client.logout()

        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["user"])

    def test_login_accepts_email(self):
        self.client.logout()

        response = self.client.post(
            "/api/auth/login/",
            {"email": "admin@example.com", "password": "testpass123"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["username"], "admin")

    def test_category_personal_requires_member(self):
        response = self.client.post(
            "/api/categories/",
            {
                "name": "Ropa",
                "scope": "personal",
                "monthly_budget_cents": 100000,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("member", response.data)

    def test_category_accepts_icon_and_color(self):
        response = self.client.post(
            "/api/categories/",
            {
                "name": "Mascotas",
                "scope": "global",
                "monthly_budget_cents": 100000,
                "color": "#ca8a04",
                "icon": "paw",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["color"], "#ca8a04")
        self.assertEqual(response.data["icon"], "paw")

    def test_transaction_expense_requires_category_and_account(self):
        response = self.client.post(
            "/api/transactions/",
            {
                "transaction_type": "expense",
                "merchant": "Prueba",
                "amount_cents": 5000,
                "date": "2026-04-25",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("category", response.data)

    def test_can_create_expense_and_get_budget_summary(self):
        response = self.client.post(
            "/api/transactions/",
            {
                "transaction_type": "expense",
                "merchant": "Super local",
                "amount_cents": 25000,
                "date": "2026-04-25",
                "account": self.account.id,
                "category": self.category.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["merchant"], "Super local")
        self.assertEqual(response.data["created_by_username"], "admin")

        summary = self.client.get("/api/budget/summary/?date=2026-04-25&scope=family")

        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.data["scope"], "family")
        self.assertEqual(summary.data["totals"]["spent_cents"], 25000)
        self.assertEqual(summary.data["categories"][0]["icon"], "tag")

    def test_expense_creates_merchant_concept_suggestion(self):
        first = self.client.post(
            "/api/transactions/",
            {
                "transaction_type": "expense",
                "merchant": " Super   Local ",
                "amount_cents": 25000,
                "date": "2026-04-25",
                "account": self.account.id,
                "category": self.category.id,
            },
            format="json",
        )
        second = self.client.post(
            "/api/transactions/",
            {
                "transaction_type": "expense",
                "merchant": "super local",
                "amount_cents": 12000,
                "date": "2026-04-26",
                "account": self.account.id,
                "category": self.category.id,
            },
            format="json",
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data["merchant"], "Super Local")
        self.assertEqual(second.status_code, 201)
        self.assertEqual(MerchantConcept.objects.count(), 1)
        concept = MerchantConcept.objects.get()
        self.assertEqual(concept.name, "Super Local")
        self.assertEqual(concept.usage_count, 2)

        suggestions = self.client.get("/api/merchant-concepts/?search=super")

        self.assertEqual(suggestions.status_code, 200)
        self.assertEqual(suggestions.data[0]["name"], "Super Local")
        self.assertEqual(suggestions.data[0]["usage_count"], 2)

    def test_can_create_recurring_and_confirm_expected_charge(self):
        recurring = RecurringExpense.objects.create(
            name="Internet",
            amount_cents=59900,
            category=self.category,
            account=self.account,
            start_date=date(2026, 4, 1),
            charge_day=1,
        )

        expected = self.client.get("/api/expected-charges/?period=2026-05")

        self.assertEqual(expected.status_code, 200)
        self.assertEqual(expected.data["charges"][0]["source_id"], recurring.id)

        confirmed = self.client.post(
            "/api/expected-charges/confirm/",
            {
                "source_type": "recurring",
                "source_id": recurring.id,
                "date": "2026-05-01",
                "account": self.account.id,
            },
            format="json",
        )

        self.assertEqual(confirmed.status_code, 201)
        self.assertEqual(confirmed.data["amount_cents"], 59900)

    def test_installment_plan_requires_valid_dates(self):
        response = self.client.post(
            "/api/installment-plans/",
            {
                "name": "Laptop",
                "total_amount_cents": 1200000,
                "category": self.category.id,
                "account": self.account.id,
                "start_date": "2026-06-01",
                "end_date": "2026-04-01",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("end_date", response.data)

    def test_installment_plan_generates_monthly_expected_charge(self):
        plan = InstallmentPlan.objects.create(
            name="Laptop",
            total_amount_cents=1200000,
            category=self.category,
            account=self.account,
            start_date=date(2026, 4, 21),
            end_date=date(2026, 6, 21),
        )

        expected = self.client.get("/api/expected-charges/?period=2026-05")

        self.assertEqual(expected.status_code, 200)
        self.assertEqual(expected.data["charges"][0]["source_id"], plan.id)
        self.assertEqual(expected.data["charges"][0]["amount_cents"], 400000)

    def test_installment_projection_endpoint_groups_current_and_future_payments(self):
        InstallmentPlan.objects.create(
            name="Laptop",
            total_amount_cents=1200000,
            category=self.category,
            account=self.account,
            start_date=date(2026, 4, 21),
            end_date=date(2026, 6, 21),
        )

        response = self.client.get("/api/installments/projection/?date=2026-04-25")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_total_cents"], 400000)
        self.assertEqual(len(response.data["periods"]), 7)
        self.assertEqual(response.data["periods"][0]["plans"][0]["name"], "Laptop")
        self.assertEqual(response.data["plans"][0]["remaining_payments"], 2)

    def test_non_admin_cannot_change_settings_accounts_people_or_categories(self):
        User.objects.create_user(username="reader", password="testpass123")
        self.client.logout()
        self.client.login(username="reader", password="testpass123")

        settings_response = self.client.put("/api/settings/", {"currency": "MXN", "cutoff_day": 15}, format="json")
        account_response = self.client.post(
            "/api/accounts/",
            {"name": "Debito reader", "account_type": "debit_card"},
            format="json",
        )
        member_response = self.client.post(
            "/api/household-members/",
            {"name": "Reader", "color": "#2563eb", "has_access": False},
            format="json",
        )
        category_response = self.client.post(
            "/api/categories/",
            {"name": "Servicios", "scope": "global", "monthly_budget_cents": 100000},
            format="json",
        )

        self.assertEqual(settings_response.status_code, 403)
        self.assertEqual(account_response.status_code, 403)
        self.assertEqual(member_response.status_code, 403)
        self.assertEqual(category_response.status_code, 403)

    def test_member_can_be_created_without_access(self):
        response = self.client.post(
            "/api/household-members/",
            {"name": "Luis", "color": "#2563eb", "has_access": False},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["access_enabled"])
        self.assertIsNone(response.data["user_username"])

    def test_member_can_be_created_with_admin_access(self):
        response = self.client.post(
            "/api/household-members/",
            {
                "name": "Sofia",
                "color": "#dc2626",
                "has_access": True,
                "username": "sofia",
                "email": "sofia@example.com",
                "password": "BurnRate!2345",
                "is_admin": True,
            },
            format="json",
        )

        user = User.objects.get(username="sofia")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["access_enabled"])
        self.assertTrue(response.data["user_is_admin"])
        self.assertTrue(user.is_staff)

    def test_non_cash_account_rejects_initial_balance(self):
        response = self.client.post(
            "/api/accounts/",
            {
                "name": "Debito",
                "account_type": "debit_card",
                "initial_balance_cents": 50000,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("initial_balance_cents", response.data)


class AuthBootstrapApiTests(APITestCase):
    def test_bootstrap_status_and_claim_create_first_admin_session(self):
        status_response = self.client.get("/api/bootstrap/status/")

        self.assertEqual(status_response.status_code, 200)
        self.assertTrue(status_response.data["needs_bootstrap"])
        self.assertTrue(status_response.data["can_claim"])

        claim_response = self.client.post(
            "/api/bootstrap/claim/",
            {
                "email": "Owner@Example.com",
                "full_name": "Olivia Owner",
                "display_name": "Oli",
                "password": "BurnRate!2345",
            },
            format="json",
        )

        self.assertEqual(claim_response.status_code, 201)
        self.assertEqual(claim_response.data["user"]["email"], "owner@example.com")
        self.assertTrue(claim_response.data["user"]["is_staff"])
        self.assertEqual(claim_response.data["member"]["name"], "Oli")
        user = User.objects.get(email="owner@example.com")
        self.assertTrue(user.is_superuser)
        self.assertEqual(HouseholdMember.objects.get(user=user).name, "Oli")

        me_response = self.client.get("/api/auth/me/")
        next_status = self.client.get("/api/bootstrap/status/")

        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.data["user"]["email"], "owner@example.com")
        self.assertFalse(next_status.data["needs_bootstrap"])

    def test_bootstrap_claim_rejects_when_staff_exists(self):
        User.objects.create_user(username="admin", email="admin@example.com", password="testpass123", is_staff=True)

        response = self.client.post(
            "/api/bootstrap/claim/",
            {
                "email": "owner@example.com",
                "full_name": "Owner Existing",
                "display_name": "Owner",
                "password": "BurnRate!2345",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)

    def test_bootstrap_claim_uses_password_validators(self):
        response = self.client.post(
            "/api/bootstrap/claim/",
            {
                "email": "owner@example.com",
                "full_name": "Owner Existing",
                "display_name": "Owner",
                "password": "123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)


class InvitationApiTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.client.login(username="admin", password="testpass123")

    def create_invitation(self, **overrides):
        payload = {
            "email": "guest@example.com",
            "full_name": "Guest User",
            "display_name": "Guest",
            "message": "Te invito a Burn Rate.",
            "expires_in_days": 5,
        }
        payload.update(overrides)
        return self.client.post("/api/invitations/", payload, format="json")

    def test_staff_can_create_list_resolve_and_accept_invitation(self):
        create_response = self.create_invitation(is_staff=False)

        self.assertEqual(create_response.status_code, 201)
        token = create_response.data["token"]
        invitation = Invitation.objects.get(email="guest@example.com")
        self.assertNotEqual(invitation.token_hash, token)
        self.assertEqual(len(invitation.token_hash), 64)
        self.assertEqual(create_response.data["status"], "pending")
        self.assertEqual(create_response.data["message"], "Te invito a Burn Rate.")
        self.assertFalse(create_response.data["is_admin"])
        self.assertFalse(create_response.data["email_sent"])

        list_response = self.client.get("/api/invitations/")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data[0]["email"], "guest@example.com")
        self.assertNotIn("token", list_response.data[0])

        self.client.logout()
        resolve_response = self.client.get(f"/api/invitations/resolve/?token={token}")
        accept_response = self.client.post(
            "/api/invitations/accept/",
            {
                "token": token,
                "email": "guest@example.com",
                "full_name": "Guest Accepted",
                "display_name": "Invitada",
                "password": "BurnRate!2345",
            },
            format="json",
        )

        self.assertEqual(resolve_response.status_code, 200)
        self.assertEqual(resolve_response.data["status"], "pending")
        self.assertEqual(resolve_response.data["display_name"], "Guest")
        self.assertEqual(resolve_response.data["message"], "Te invito a Burn Rate.")
        self.assertEqual(accept_response.status_code, 201)
        self.assertEqual(accept_response.data["user"]["email"], "guest@example.com")
        self.assertFalse(accept_response.data["user"]["is_staff"])
        self.assertEqual(accept_response.data["member"]["name"], "Invitada")
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "accepted")
        self.assertIsNotNone(invitation.accepted_by)

    @override_settings(
        BURN_RATE_SEND_INVITATION_EMAIL=True,
        BURN_RATE_INVITATION_ACCEPT_URL="https://app.example.test/accept/{token}",
        DEFAULT_FROM_EMAIL="noreply@example.test",
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_invitation_email_send_is_controlled_by_settings(self):
        response = self.create_invitation(email="mail@example.com")

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["email_sent"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(response.data["accept_url"], mail.outbox[0].body)
        self.assertIn(response.data["token"], mail.outbox[0].body)

    def test_non_staff_cannot_manage_invitations(self):
        User.objects.create_user(username="reader", password="testpass123")
        self.client.logout()
        self.client.login(username="reader", password="testpass123")

        list_response = self.client.get("/api/invitations/")
        create_response = self.create_invitation(email="reader-invite@example.com")

        self.assertEqual(list_response.status_code, 403)
        self.assertEqual(create_response.status_code, 403)

    def test_staff_can_revoke_invitation_and_accept_rejects_revoked_token(self):
        create_response = self.create_invitation(email="revoked@example.com")
        token = create_response.data["token"]
        invitation_id = create_response.data["id"]

        revoke_response = self.client.post(f"/api/invitations/{invitation_id}/revoke/")

        self.assertEqual(revoke_response.status_code, 200)
        self.assertEqual(revoke_response.data["status"], "revoked")

        self.client.logout()
        accept_response = self.client.post(
            "/api/invitations/accept/",
            {
                "token": token,
                "email": "revoked@example.com",
                "full_name": "Revoked User",
                "display_name": "Revoked",
                "password": "BurnRate!2345",
            },
            format="json",
        )

        self.assertEqual(accept_response.status_code, 400)
        self.assertFalse(User.objects.filter(email="revoked@example.com").exists())

    def test_invitation_accept_uses_password_validators(self):
        create_response = self.create_invitation(email="weak@example.com")

        self.client.logout()
        response = self.client.post(
            "/api/invitations/accept/",
            {
                "token": create_response.data["token"],
                "email": "weak@example.com",
                "full_name": "Weak Password",
                "display_name": "Weak",
                "password": "123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)

    def test_auth_refresh_returns_current_user(self):
        response = self.client.post("/api/auth/refresh/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["email"], "admin@example.com")
