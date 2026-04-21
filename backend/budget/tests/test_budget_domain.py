from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from budget.models import Account, Category, HouseholdMember, InstallmentPlan, RecurringExpense, Transaction
from budget.services import build_budget_summary, expected_charges_for_period, get_budget_period, installment_projection


class BudgetPeriodTests(TestCase):
    def test_cutoff_day_twenty_includes_day_twenty_as_period_end(self):
        period = get_budget_period(date(2026, 4, 20), cutoff_day=20)

        self.assertEqual(period.start, date(2026, 3, 21))
        self.assertEqual(period.end, date(2026, 4, 20))

    def test_day_after_cutoff_starts_next_period(self):
        period = get_budget_period(date(2026, 4, 21), cutoff_day=20)

        self.assertEqual(period.start, date(2026, 4, 21))
        self.assertEqual(period.end, date(2026, 5, 20))


class BudgetSummaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="admin", password="testpass123")
        self.member = HouseholdMember.objects.create(name="Ana", color="#dc2626")
        self.cash = Account.objects.create(name="Caja", account_type=Account.AccountType.CASH)
        self.global_category = Category.objects.create(
            name="Super",
            scope=Category.Scope.GLOBAL,
            monthly_budget_cents=500000,
        )
        self.personal_category = Category.objects.create(
            name="Ropa",
            scope=Category.Scope.PERSONAL,
            member=self.member,
            monthly_budget_cents=100000,
        )

    def test_summary_shows_negative_available_when_overspent(self):
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPENSE,
            merchant="Tienda de ropa",
            amount_cents=125000,
            date=date(2026, 4, 25),
            account=self.cash,
            category=self.personal_category,
            created_by=self.user,
        )

        summary = build_budget_summary(date(2026, 4, 25), scope="member", member_id=self.member.id)

        self.assertEqual(summary["totals"]["budget_cents"], 100000)
        self.assertEqual(summary["totals"]["spent_cents"], 125000)
        self.assertEqual(summary["totals"]["available_cents"], -25000)
        self.assertTrue(summary["categories"][0]["is_overspent"])

    def test_family_summary_excludes_personal_categories(self):
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPENSE,
            merchant="Tienda personal",
            amount_cents=30000,
            date=date(2026, 4, 25),
            account=self.cash,
            category=self.personal_category,
            created_by=self.user,
        )

        summary = build_budget_summary(date(2026, 4, 25), scope="family")

        self.assertEqual(len(summary["categories"]), 1)
        self.assertEqual(summary["categories"][0]["category_name"], "Super")
        self.assertEqual(summary["categories"][0]["member"], None)
        self.assertEqual(summary["breakdown"][0]["label"], "Familia")
        self.assertEqual(summary["totals"]["spent_cents"], 0)

    def test_total_summary_combines_family_and_personal_budgets(self):
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPENSE,
            merchant="Super local",
            amount_cents=150000,
            date=date(2026, 4, 25),
            account=self.cash,
            category=self.global_category,
            created_by=self.user,
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPENSE,
            merchant="Boutique",
            amount_cents=40000,
            date=date(2026, 4, 25),
            account=self.cash,
            category=self.personal_category,
            created_by=self.user,
        )

        summary = build_budget_summary(date(2026, 4, 25), scope="total")

        self.assertEqual(summary["totals"]["budget_cents"], 600000)
        self.assertEqual(summary["totals"]["spent_cents"], 190000)
        self.assertEqual(len(summary["breakdown"]), 2)

    def test_budget_allocations_preserve_historical_budget(self):
        build_budget_summary(date(2026, 4, 25), scope="family")
        self.global_category.monthly_budget_cents = 800000
        self.global_category.save()

        same_period = build_budget_summary(date(2026, 4, 26), scope="family")
        next_period = build_budget_summary(date(2026, 5, 25), scope="family")

        self.assertEqual(same_period["totals"]["budget_cents"], 500000)
        self.assertEqual(next_period["totals"]["budget_cents"], 800000)

    def test_transfer_and_income_do_not_affect_budget_spend(self):
        bank = Account.objects.create(name="Debito", account_type=Account.AccountType.BANK)
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.INCOME,
            amount_cents=100000,
            date=date(2026, 4, 25),
            destination_account=bank,
            created_by=self.user,
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.TRANSFER,
            amount_cents=50000,
            date=date(2026, 4, 25),
            account=bank,
            destination_account=self.cash,
            created_by=self.user,
        )

        summary = build_budget_summary(date(2026, 4, 25), scope="total")

        self.assertEqual(summary["totals"]["spent_cents"], 0)

    def test_only_cash_accounts_can_have_initial_balance(self):
        cash = Account.objects.create(
            name="Sobre",
            account_type=Account.AccountType.CASH,
            initial_balance_cents=50000,
        )

        with self.assertRaisesMessage(ValidationError, "Solo las cuentas de efectivo pueden tener saldo inicial."):
            Account.objects.create(
                name="Debito con saldo",
                account_type=Account.AccountType.DEBIT_CARD,
                initial_balance_cents=50000,
            )

        self.assertEqual(cash.initial_balance_cents, 50000)


class ExpectedChargeTests(TestCase):
    def setUp(self):
        self.member = HouseholdMember.objects.create(name="Luis", color="#2563eb")
        self.card = Account.objects.create(name="Tarjeta dorada", account_type=Account.AccountType.CREDIT_CARD)
        self.category = Category.objects.create(
            name="Streaming",
            scope=Category.Scope.PERSONAL,
            member=self.member,
            monthly_budget_cents=200000,
        )

    def test_recurring_expense_generates_expected_charge_for_active_period(self):
        RecurringExpense.objects.create(
            name="Netflix",
            amount_cents=29900,
            category=self.category,
            account=self.card,
            start_date=date(2026, 4, 1),
            charge_day=5,
        )

        charges = expected_charges_for_period(get_budget_period(date(2026, 4, 25)))

        self.assertEqual(len(charges), 1)
        self.assertEqual(charges[0].name, "Netflix")
        self.assertEqual(charges[0].amount_cents, 29900)

    def test_installment_plan_consumes_only_monthly_payment(self):
        InstallmentPlan.objects.create(
            name="Laptop",
            total_amount_cents=1200000,
            category=self.category,
            account=self.card,
            start_date=date(2026, 4, 21),
            end_date=date(2026, 6, 21),
        )

        summary = build_budget_summary(date(2026, 4, 25), scope="member", member_id=self.member.id)

        self.assertEqual(summary["totals"]["expected_cents"], 400000)
        self.assertEqual(summary["categories"][0]["expected_cents"], 400000)

    def test_installment_projection_includes_current_and_next_six_periods(self):
        InstallmentPlan.objects.create(
            name="Laptop",
            total_amount_cents=1200000,
            category=self.category,
            account=self.card,
            start_date=date(2026, 4, 21),
            end_date=date(2026, 6, 21),
        )

        projection = installment_projection(date(2026, 4, 25))

        self.assertEqual(len(projection["periods"]), 7)
        self.assertEqual(projection["current_total_cents"], 400000)
        self.assertEqual(projection["periods"][0]["total_cents"], 400000)
        self.assertEqual(projection["periods"][1]["total_cents"], 400000)
        self.assertEqual(projection["periods"][2]["total_cents"], 400000)
        self.assertEqual(projection["periods"][3]["total_cents"], 0)
        self.assertEqual(projection["plans"][0]["current_payment_number"], 1)
        self.assertEqual(projection["plans"][0]["remaining_payments"], 2)
