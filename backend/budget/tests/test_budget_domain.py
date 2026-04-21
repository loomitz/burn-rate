from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from budget.models import (
    Account,
    BudgetAllocation,
    Category,
    CategoryBudgetChange,
    CategoryOverspendRecord,
    HouseholdMember,
    InstallmentPlan,
    RecurringExpense,
    Transaction,
)
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

    def test_category_budget_change_applies_from_effective_cycle_only(self):
        previous_period = build_budget_summary(date(2026, 3, 25), scope="family")
        current_period = build_budget_summary(date(2026, 4, 25), scope="family")
        self.assertEqual(previous_period["totals"]["budget_cents"], 500000)
        self.assertEqual(current_period["totals"]["budget_cents"], 500000)

        self.global_category.monthly_budget_cents = 800000
        self.global_category.save()
        CategoryBudgetChange.objects.create(
            category=self.global_category,
            amount_cents=800000,
            effective_date=date(2026, 4, 25),
            period_start=date(2026, 4, 21),
            period_end=date(2026, 5, 20),
        )
        BudgetAllocation.objects.filter(category=self.global_category, period_start__gte=date(2026, 4, 21)).update(
            amount_cents=800000
        )

        previous_after_change = build_budget_summary(date(2026, 3, 25), scope="family")
        current_after_change = build_budget_summary(date(2026, 4, 25), scope="family")

        self.assertEqual(previous_after_change["totals"]["budget_cents"], 500000)
        self.assertEqual(current_after_change["totals"]["budget_cents"], 800000)

    def test_carryover_category_tracks_real_balance_and_projected_available(self):
        travel = Category.objects.create(
            name="Viajes",
            scope=Category.Scope.GLOBAL,
            monthly_budget_cents=100000,
            budget_behavior=Category.BudgetBehavior.CARRYOVER,
            carryover_initial_balance_cents=10000,
            carryover_start_date=date(2026, 3, 21),
        )
        CategoryBudgetChange.objects.create(
            category=travel,
            amount_cents=100000,
            effective_date=date(2026, 3, 21),
            period_start=date(2026, 3, 21),
            period_end=date(2026, 4, 20),
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPENSE,
            merchant="Hotel",
            amount_cents=30000,
            date=date(2026, 4, 25),
            account=self.cash,
            category=travel,
            created_by=self.user,
        )
        RecurringExpense.objects.create(
            name="Apartado viaje",
            merchant="Agencia",
            amount_cents=40000,
            category=travel,
            account=self.cash,
            start_date=date(2026, 4, 21),
            charge_day=28,
        )

        summary = build_budget_summary(date(2026, 4, 25), scope="family")
        row = next(category for category in summary["categories"] if category["category_name"] == "Viajes")

        self.assertEqual(row["budget_behavior"], Category.BudgetBehavior.CARRYOVER)
        self.assertEqual(row["carryover_real_balance_cents"], 180000)
        self.assertEqual(row["real_available_cents"], 180000)
        self.assertEqual(row["expected_cents"], 40000)
        self.assertEqual(row["projected_available_cents"], 140000)
        self.assertEqual(row["available_cents"], 140000)

    def test_monthly_categories_record_closed_cycle_overspend_history(self):
        self.personal_category.overspend_tracking_start_date = date(2026, 3, 21)
        self.personal_category.save()
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPENSE,
            merchant="Boutique",
            amount_cents=125000,
            date=date(2026, 3, 25),
            account=self.cash,
            category=self.personal_category,
            created_by=self.user,
        )

        summary = build_budget_summary(date(2026, 4, 25), scope="member", member_id=self.member.id)
        row = summary["categories"][0]

        record = CategoryOverspendRecord.objects.get(category=self.personal_category, period_start=date(2026, 3, 21))
        self.assertEqual(record.overspend_cents, 25000)
        self.assertEqual(row["overspend_count"], 1)
        self.assertEqual(row["overspend_total_cents"], 25000)
        self.assertEqual(row["last_overspend_cents"], 25000)

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
            merchant="Netflix",
            amount_cents=29900,
            category=self.category,
            account=self.card,
            start_date=date(2026, 4, 1),
            charge_day=5,
        )

        charges = expected_charges_for_period(get_budget_period(date(2026, 4, 25)))

        self.assertEqual(len(charges), 1)
        self.assertEqual(charges[0].name, "Netflix")
        self.assertEqual(charges[0].merchant, "Netflix")
        self.assertEqual(charges[0].amount_cents, 29900)

    def test_installment_plan_consumes_only_monthly_payment(self):
        InstallmentPlan.objects.create(
            name="Laptop",
            merchant="Liverpool",
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
            merchant="Liverpool",
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
        self.assertEqual(projection["plans"][0]["merchant"], "Liverpool")
        self.assertEqual(projection["plans"][0]["remaining_payments"], 2)

    def test_installment_plan_can_start_from_existing_payment_number(self):
        plan = InstallmentPlan.objects.create(
            name="Laptop heredada",
            merchant="Liverpool",
            total_amount_cents=1200000,
            category=self.category,
            account=self.card,
            start_date=date(2026, 4, 21),
            end_date=date(2026, 12, 21),
            first_payment_number=4,
        )

        projection = installment_projection(date(2026, 4, 25))

        self.assertEqual(plan.installments_count, 12)
        self.assertEqual(projection["current_total_cents"], 100000)
        self.assertEqual(projection["plans"][0]["current_payment_number"], 4)
        self.assertEqual(projection["plans"][0]["payments_total"], 12)
        self.assertEqual(projection["plans"][0]["remaining_payments"], 8)

    def test_installment_plan_can_round_up_required_payment_to_next_peso(self):
        plan = InstallmentPlan.objects.create(
            name="Amazon MSI redondeado",
            merchant="Amazon",
            total_amount_cents=271438,
            category=self.category,
            account=self.card,
            start_date=date(2026, 4, 21),
            end_date=date(2027, 3, 21),
            round_up_monthly_payment=True,
        )

        first_period_charges = expected_charges_for_period(get_budget_period(date(2026, 4, 25)))
        final_period_charges = expected_charges_for_period(get_budget_period(date(2027, 3, 25)))
        projection = installment_projection(date(2026, 4, 25), months_ahead=12)

        self.assertEqual(plan.installments_count, 12)
        self.assertEqual(plan.monthly_amount_cents, 22700)
        self.assertEqual(first_period_charges[0].amount_cents, 22700)
        self.assertEqual(final_period_charges[0].amount_cents, 21738)
        self.assertEqual(projection["periods"][0]["total_cents"], 22700)
        self.assertEqual(projection["periods"][11]["total_cents"], 21738)
        self.assertTrue(projection["plans"][0]["round_up_monthly_payment"])
