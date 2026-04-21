from datetime import date

from django.contrib.auth.models import User
from django.core import mail
from django.test import override_settings
from rest_framework.test import APITestCase

from budget.models import (
    Account,
    AppSettings,
    Category,
    CategoryBudgetChange,
    ExpectedChargeDismissal,
    HouseholdMember,
    InstallmentPlan,
    Invitation,
    MerchantConcept,
    RecurringExpense,
    Transaction,
)


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
        self.assertEqual(response.data["budget_behavior"], Category.BudgetBehavior.MONTHLY_RESET)

    def test_category_can_be_created_as_carryover_budget(self):
        response = self.client.post(
            "/api/categories/",
            {
                "name": "Viajes",
                "scope": "global",
                "monthly_budget_cents": 250000,
                "budget_behavior": Category.BudgetBehavior.CARRYOVER,
                "carryover_initial_balance_cents": -50000,
                "carryover_start_date": "2026-04-21",
                "color": "#0284c7",
                "icon": "plane",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["budget_behavior"], Category.BudgetBehavior.CARRYOVER)
        self.assertEqual(response.data["carryover_initial_balance_cents"], -50000)
        self.assertEqual(response.data["carryover_start_date"], "2026-04-21")
        self.assertTrue(CategoryBudgetChange.objects.filter(category_id=response.data["id"], amount_cents=250000).exists())

    def test_carryover_category_requires_initial_balance_and_start_date(self):
        response = self.client.post(
            "/api/categories/",
            {
                "name": "Viajes",
                "scope": "global",
                "monthly_budget_cents": 250000,
                "budget_behavior": Category.BudgetBehavior.CARRYOVER,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("carryover_initial_balance_cents", response.data)

    def test_category_can_be_updated_by_admin(self):
        response = self.client.patch(
            f"/api/categories/{self.category.id}/",
            {
                "name": "Super y despensa",
                "monthly_budget_cents": 250000,
                "budget_effective_date": "2026-04-21",
                "color": "#0284c7",
                "icon": "shopping-cart",
                "is_active": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Super y despensa")
        self.assertEqual(response.data["monthly_budget_cents"], 250000)
        self.assertEqual(response.data["color"], "#0284c7")
        self.assertEqual(response.data["icon"], "shopping-cart")
        self.assertFalse(response.data["is_active"])
        self.assertTrue(CategoryBudgetChange.objects.filter(category=self.category, amount_cents=250000).exists())

    def test_category_budget_change_requires_effective_date(self):
        response = self.client.patch(
            f"/api/categories/{self.category.id}/",
            {"monthly_budget_cents": 250000},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("budget_effective_date", response.data)

    def test_category_budget_can_be_decreased_with_effective_date(self):
        response = self.client.patch(
            f"/api/categories/{self.category.id}/",
            {"monthly_budget_cents": 150000, "budget_effective_date": "2026-04-21"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["monthly_budget_cents"], 150000)
        self.assertTrue(CategoryBudgetChange.objects.filter(category=self.category, amount_cents=150000).exists())

    def test_category_budget_behavior_cannot_be_changed_after_create(self):
        response = self.client.patch(
            f"/api/categories/{self.category.id}/",
            {
                "budget_behavior": Category.BudgetBehavior.CARRYOVER,
                "carryover_initial_balance_cents": 0,
                "carryover_start_date": "2026-04-21",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("budget_behavior", response.data)

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
            merchant="Telmex",
            amount_cents=59900,
            category=self.category,
            account=self.account,
            start_date=date(2026, 4, 1),
            charge_day=1,
        )

        expected = self.client.get("/api/expected-charges/?period=2026-05")

        self.assertEqual(expected.status_code, 200)
        self.assertEqual(expected.data["charges"][0]["source_id"], recurring.id)
        self.assertEqual(expected.data["charges"][0]["merchant"], "Telmex")

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
        self.assertEqual(confirmed.data["merchant"], "Telmex")
        self.assertEqual(confirmed.data["amount_cents"], 59900)

    def test_recurring_expense_api_accepts_shared_merchant(self):
        response = self.client.post(
            "/api/recurring-expenses/",
            {
                "name": "Internet mensual",
                "merchant": "Telmex",
                "amount_cents": 59900,
                "category": self.category.id,
                "account": self.account.id,
                "start_date": "2026-04-01",
                "charge_day": 1,
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["merchant"], "Telmex")
        self.assertTrue(MerchantConcept.objects.filter(name="Telmex").exists())

    def test_recurring_expense_update_only_allows_name_and_merchant(self):
        recurring = RecurringExpense.objects.create(
            name="Internet",
            merchant="Telmex",
            amount_cents=59900,
            category=self.category,
            account=self.account,
            start_date=date(2026, 4, 1),
            charge_day=1,
        )

        response = self.client.patch(
            f"/api/recurring-expenses/{recurring.id}/",
            {"name": "Internet casa", "merchant": "Telmex Hogar"},
            format="json",
        )
        blocked_response = self.client.patch(
            f"/api/recurring-expenses/{recurring.id}/",
            {"amount_cents": 70000, "start_date": "2026-05-01"},
            format="json",
        )

        recurring.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(recurring.name, "Internet casa")
        self.assertEqual(recurring.merchant, "Telmex Hogar")
        self.assertEqual(blocked_response.status_code, 400)
        self.assertEqual(set(blocked_response.data["fields"]), {"amount_cents", "start_date"})
        self.assertEqual(recurring.amount_cents, 59900)
        self.assertEqual(recurring.start_date, date(2026, 4, 1))

    def test_can_delete_recurring_expense_without_deleting_confirmed_transactions(self):
        recurring = RecurringExpense.objects.create(
            name="Internet",
            merchant="Telmex",
            amount_cents=59900,
            category=self.category,
            account=self.account,
            start_date=date(2026, 4, 1),
            charge_day=1,
        )
        dismissal = ExpectedChargeDismissal.objects.create(
            source_type=ExpectedChargeDismissal.SourceType.RECURRING,
            source_id=recurring.id,
            period_start=date(2026, 5, 1),
            created_by=self.user,
        )
        transaction = Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPECTED_CHARGE,
            merchant="Telmex",
            amount_cents=59900,
            date=date(2026, 5, 1),
            account=self.account,
            category=self.category,
            recurring_expense=recurring,
            created_by=self.user,
        )

        response = self.client.delete(f"/api/recurring-expenses/{recurring.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(RecurringExpense.objects.filter(id=recurring.id).exists())
        self.assertFalse(ExpectedChargeDismissal.objects.filter(id=dismissal.id).exists())
        transaction.refresh_from_db()
        self.assertIsNone(transaction.recurring_expense_id)
        self.assertEqual(transaction.merchant, "Telmex")

    def test_non_admin_cannot_delete_recurring_expense(self):
        recurring = RecurringExpense.objects.create(
            name="Internet",
            merchant="Telmex",
            amount_cents=59900,
            category=self.category,
            account=self.account,
            start_date=date(2026, 4, 1),
            charge_day=1,
        )
        User.objects.create_user(username="reader", password="testpass123")
        self.client.logout()
        self.client.login(username="reader", password="testpass123")

        response = self.client.delete(f"/api/recurring-expenses/{recurring.id}/")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(RecurringExpense.objects.filter(id=recurring.id).exists())

    def test_installment_plan_requires_valid_dates(self):
        response = self.client.post(
            "/api/installment-plans/",
            {
                "name": "Laptop",
                "merchant": "Liverpool",
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
            merchant="Liverpool",
            total_amount_cents=1200000,
            category=self.category,
            account=self.account,
            start_date=date(2026, 4, 21),
            end_date=date(2026, 6, 21),
        )

        expected = self.client.get("/api/expected-charges/?period=2026-05")

        self.assertEqual(expected.status_code, 200)
        self.assertEqual(expected.data["charges"][0]["source_id"], plan.id)
        self.assertEqual(expected.data["charges"][0]["merchant"], "Liverpool")
        self.assertEqual(expected.data["charges"][0]["amount_cents"], 400000)

    def test_installment_plan_accepts_existing_payment_number(self):
        response = self.client.post(
            "/api/installment-plans/",
            {
                "name": "Laptop heredada",
                "merchant": "Liverpool",
                "total_amount_cents": 1200000,
                "category": self.category.id,
                "account": self.account.id,
                "start_date": "2026-04-21",
                "end_date": "2026-12-21",
                "first_payment_number": 4,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["merchant"], "Liverpool")
        self.assertEqual(response.data["first_payment_number"], 4)
        self.assertEqual(response.data["installments_count"], 12)
        self.assertEqual(response.data["monthly_amount_cents"], 100000)
        self.assertTrue(MerchantConcept.objects.filter(name="Liverpool").exists())

    def test_installment_plan_accepts_months_count_from_first_payment_date(self):
        response = self.client.post(
            "/api/installment-plans/",
            {
                "name": "Amazon heredada",
                "merchant": "Amazon",
                "total_amount_cents": 1200000,
                "category": self.category.id,
                "account": self.account.id,
                "start_date": "2025-06-25",
                "months_count": 12,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["end_date"], "2026-05-25")
        self.assertEqual(response.data["first_payment_number"], 1)
        self.assertEqual(response.data["installments_count"], 12)

        projection = self.client.get("/api/installments/projection/?date=2026-04-25")

        self.assertEqual(projection.data["plans"][0]["current_payment_number"], 11)
        self.assertEqual(projection.data["plans"][0]["remaining_payments"], 1)

    def test_installment_plan_accepts_rounded_up_required_payment(self):
        response = self.client.post(
            "/api/installment-plans/",
            {
                "name": "Amazon MSI redondeado",
                "merchant": "Amazon",
                "total_amount_cents": 271438,
                "category": self.category.id,
                "account": self.account.id,
                "start_date": "2026-04-21",
                "months_count": 12,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["round_up_monthly_payment"])
        self.assertEqual(response.data["installments_count"], 12)
        self.assertEqual(response.data["monthly_amount_cents"], 22700)

        first_expected = self.client.get("/api/expected-charges/?date=2026-04-25")
        final_expected = self.client.get("/api/expected-charges/?date=2027-03-25")

        self.assertEqual(first_expected.data["charges"][0]["amount_cents"], 22700)
        self.assertEqual(final_expected.data["charges"][0]["amount_cents"], 21738)

    def test_installment_plan_update_allows_name_merchant_and_category(self):
        target_category = Category.objects.create(
            name="Tecnologia",
            scope=Category.Scope.GLOBAL,
            monthly_budget_cents=300000,
        )
        plan = InstallmentPlan.objects.create(
            name="Laptop",
            merchant="Liverpool",
            total_amount_cents=1200000,
            category=self.category,
            account=self.account,
            start_date=date(2026, 4, 21),
            end_date=date(2026, 6, 21),
        )

        response = self.client.patch(
            f"/api/installment-plans/{plan.id}/",
            {"name": "Laptop trabajo", "merchant": "Liverpool Online", "category": target_category.id},
            format="json",
        )
        blocked_response = self.client.patch(
            f"/api/installment-plans/{plan.id}/",
            {"total_amount_cents": 900000, "start_date": "2026-05-21"},
            format="json",
        )

        plan.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(plan.name, "Laptop trabajo")
        self.assertEqual(plan.merchant, "Liverpool Online")
        self.assertEqual(plan.category_id, target_category.id)
        self.assertEqual(blocked_response.status_code, 400)
        self.assertEqual(set(blocked_response.data["fields"]), {"start_date", "total_amount_cents"})
        self.assertEqual(plan.total_amount_cents, 1200000)
        self.assertEqual(plan.start_date, date(2026, 4, 21))

    def test_can_delete_installment_plan_without_deleting_confirmed_transactions(self):
        plan = InstallmentPlan.objects.create(
            name="Laptop",
            merchant="Liverpool",
            total_amount_cents=1200000,
            category=self.category,
            account=self.account,
            start_date=date(2026, 4, 21),
            end_date=date(2026, 6, 21),
        )
        dismissal = ExpectedChargeDismissal.objects.create(
            source_type=ExpectedChargeDismissal.SourceType.INSTALLMENT,
            source_id=plan.id,
            period_start=date(2026, 5, 1),
            created_by=self.user,
        )
        transaction = Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPECTED_CHARGE,
            merchant="Liverpool",
            amount_cents=400000,
            date=date(2026, 5, 21),
            account=self.account,
            category=self.category,
            installment_plan=plan,
            created_by=self.user,
        )

        response = self.client.delete(f"/api/installment-plans/{plan.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(InstallmentPlan.objects.filter(id=plan.id).exists())
        self.assertFalse(ExpectedChargeDismissal.objects.filter(id=dismissal.id).exists())
        transaction.refresh_from_db()
        self.assertIsNone(transaction.installment_plan_id)
        self.assertEqual(transaction.merchant, "Liverpool")

    def test_non_admin_cannot_delete_installment_plan(self):
        plan = InstallmentPlan.objects.create(
            name="Laptop",
            merchant="Liverpool",
            total_amount_cents=1200000,
            category=self.category,
            account=self.account,
            start_date=date(2026, 4, 21),
            end_date=date(2026, 6, 21),
        )
        User.objects.create_user(username="reader", password="testpass123")
        self.client.logout()
        self.client.login(username="reader", password="testpass123")

        response = self.client.delete(f"/api/installment-plans/{plan.id}/")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(InstallmentPlan.objects.filter(id=plan.id).exists())

    def test_installment_projection_endpoint_groups_current_and_future_payments(self):
        InstallmentPlan.objects.create(
            name="Laptop",
            merchant="Liverpool",
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
        self.assertEqual(response.data["periods"][0]["plans"][0]["merchant"], "Liverpool")
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

    def test_member_admin_flag_implies_access(self):
        response = self.client.post(
            "/api/household-members/",
            {
                "name": "Nuez",
                "color": "#9333ea",
                "has_access": False,
                "username": "nuez",
                "email": "nuez@example.com",
                "password": "BurnRate!2345",
                "is_admin": True,
            },
            format="json",
        )

        user = User.objects.get(username="nuez")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["access_enabled"])
        self.assertTrue(response.data["user_is_admin"])
        self.assertTrue(user.is_staff)

    def test_member_update_can_link_existing_unassigned_user(self):
        user = User.objects.create_user(username="nuez", email="nuez@example.com", password="BurnRate!2345")
        member = HouseholdMember.objects.create(name="Nuez", color="#9333ea")

        response = self.client.patch(
            f"/api/household-members/{member.id}/",
            {
                "has_access": True,
                "username": "nuez",
                "email": "nuez@example.com",
                "is_admin": True,
            },
            format="json",
        )

        user.refresh_from_db()
        member.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(member.user, user)
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

    def test_account_can_be_updated_with_color_and_active_state(self):
        response = self.client.patch(
            f"/api/accounts/{self.account.id}/",
            {
                "name": "Caja casa",
                "color": "#2563eb",
                "initial_balance_cents": 35000,
                "is_active": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Caja casa")
        self.assertEqual(response.data["color"], "#2563eb")
        self.assertEqual(response.data["initial_balance_cents"], 35000)
        self.assertFalse(response.data["is_active"])


class AuthBootstrapApiTests(APITestCase):
    def test_onboarding_status_checks_database_and_initial_config(self):
        response = self.client.get("/api/onboarding/status/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["ready"])
        self.assertTrue(response.data["database"]["connected"])
        self.assertTrue(response.data["migrations"]["applied"])
        self.assertEqual(response.data["migrations"]["pending_count"], 0)
        self.assertTrue(response.data["initial_config"]["needs_first_admin"])
        self.assertFalse(response.data["initial_config"]["has_users"])
        self.assertIn("password_configured", response.data["database"]["configured"])
        self.assertEqual(AppSettings.objects.count(), 0)

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
        self.assertEqual(create_response.data["full_name"], "")
        self.assertEqual(create_response.data["display_name"], "")
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
        self.assertEqual(resolve_response.data["display_name"], "")
        self.assertEqual(accept_response.status_code, 201)
        self.assertEqual(accept_response.data["user"]["email"], "guest@example.com")
        self.assertFalse(accept_response.data["user"]["is_staff"])
        self.assertEqual(accept_response.data["member"]["name"], "Invitada")
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "accepted")
        self.assertEqual(invitation.full_name, "Guest Accepted")
        self.assertEqual(invitation.display_name, "Invitada")
        self.assertIsNotNone(invitation.accepted_by)

    def test_staff_only_needs_email_and_admin_flag_to_create_invitation(self):
        response = self.create_invitation(email="admin-invite@example.com", is_admin=True)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["email"], "admin-invite@example.com")
        self.assertEqual(response.data["full_name"], "")
        self.assertEqual(response.data["display_name"], "")
        self.assertTrue(response.data["is_admin"])

        invitation = Invitation.objects.get(email="admin-invite@example.com")
        self.assertEqual(invitation.full_name, "")
        self.assertEqual(invitation.display_name, "")
        self.assertTrue(invitation.is_staff)

    def test_invitation_accept_links_existing_unassigned_member(self):
        create_response = self.create_invitation(email="nuez@example.com", is_admin=True)
        token = create_response.data["token"]
        existing_member = HouseholdMember.objects.create(name="Nuez", color="#9333ea")

        self.client.logout()
        accept_response = self.client.post(
            "/api/invitations/accept/",
            {
                "token": token,
                "email": "nuez@example.com",
                "full_name": "Nuez Admin",
                "display_name": "Nuez",
                "password": "BurnRate!2345",
            },
            format="json",
        )

        existing_member.refresh_from_db()
        user = User.objects.get(email="nuez@example.com")
        self.assertEqual(accept_response.status_code, 201)
        self.assertEqual(accept_response.data["member"]["id"], existing_member.id)
        self.assertEqual(existing_member.user, user)
        self.assertTrue(user.is_staff)
        self.assertEqual(HouseholdMember.objects.filter(name__iexact="Nuez").count(), 1)

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
        pending_response = self.create_invitation(email="reader-delete@example.com")
        invitation_id = pending_response.data["id"]
        User.objects.create_user(username="reader", password="testpass123")
        self.client.logout()
        self.client.login(username="reader", password="testpass123")

        list_response = self.client.get("/api/invitations/")
        create_response = self.create_invitation(email="reader-invite@example.com")
        delete_response = self.client.delete(f"/api/invitations/{invitation_id}/")

        self.assertEqual(list_response.status_code, 403)
        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)

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

    def test_staff_can_delete_unaccepted_invitation(self):
        create_response = self.create_invitation(email="delete-me@example.com")
        token = create_response.data["token"]
        invitation_id = create_response.data["id"]

        delete_response = self.client.delete(f"/api/invitations/{invitation_id}/")
        resolve_response = self.client.get(f"/api/invitations/resolve/?token={token}")

        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(Invitation.objects.filter(pk=invitation_id).exists())
        self.assertEqual(resolve_response.status_code, 404)

    def test_staff_cannot_delete_accepted_invitation(self):
        create_response = self.create_invitation(email="accepted-delete@example.com")
        token = create_response.data["token"]
        invitation_id = create_response.data["id"]
        self.client.logout()
        accept_response = self.client.post(
            "/api/invitations/accept/",
            {
                "token": token,
                "email": "accepted-delete@example.com",
                "full_name": "Accepted Delete",
                "display_name": "Accepted",
                "password": "BurnRate!2345",
            },
            format="json",
        )
        self.client.logout()
        self.client.login(username="admin", password="testpass123")

        delete_response = self.client.delete(f"/api/invitations/{invitation_id}/")

        self.assertEqual(accept_response.status_code, 201)
        self.assertEqual(delete_response.status_code, 400)
        self.assertTrue(Invitation.objects.filter(pk=invitation_id).exists())

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
