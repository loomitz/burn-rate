from datetime import date, datetime, timezone as dt_timezone
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from budget.models import (
    Account,
    AppSettings,
    BudgetAllocation,
    Category,
    CategoryBudgetChange,
    CategoryOverspendRecord,
    ExpectedChargeDismissal,
    HouseholdMember,
    InstallmentPlan,
    RecurringExpense,
    Transaction,
)
from budget.services import (
    account_balance,
    auto_post_due_recurring_charges,
    build_off_budget_summary,
    build_budget_summary,
    card_cycle,
    card_cycle_for_offset,
    card_payments_summary,
    confirm_expected_charge,
    expected_charges_for_period,
    get_budget_period,
    installment_charge_for_period,
    installment_projection,
    last_closed_card_cycle,
    previous_budget_period,
    previous_card_cycle,
    project_budget_periods,
)


class BudgetPeriodTests(TestCase):
    def test_period_is_calendar_month(self):
        period = get_budget_period(date(2026, 4, 20))

        self.assertEqual(period.start, date(2026, 4, 1))
        self.assertEqual(period.end, date(2026, 4, 30))

    def test_first_day_of_month_belongs_to_its_own_month(self):
        period = get_budget_period(date(2026, 4, 1))

        self.assertEqual(period.start, date(2026, 4, 1))
        self.assertEqual(period.end, date(2026, 4, 30))

    def test_february_period_ends_on_day_28_when_not_leap(self):
        period = get_budget_period(date(2026, 2, 15))

        self.assertEqual(period.start, date(2026, 2, 1))
        self.assertEqual(period.end, date(2026, 2, 28))

    def test_february_period_ends_on_day_29_when_leap(self):
        period = get_budget_period(date(2028, 2, 15))

        self.assertEqual(period.start, date(2028, 2, 1))
        self.assertEqual(period.end, date(2028, 2, 29))

    def test_default_period_uses_configured_app_time_zone(self):
        settings = AppSettings.load()
        settings.time_zone = "America/Los_Angeles"
        settings.save()

        with patch("budget.timezones.timezone.now", return_value=datetime(2026, 5, 21, 6, 30, tzinfo=dt_timezone.utc)):
            period = get_budget_period()

        self.assertEqual(period.start, date(2026, 5, 1))
        self.assertEqual(period.end, date(2026, 5, 31))

    def test_previous_budget_period_handles_day_31_month_ends(self):
        period = previous_budget_period(get_budget_period(date(2026, 3, 15)))

        self.assertEqual(period.start, date(2026, 2, 1))
        self.assertEqual(period.end, date(2026, 2, 28))

    def test_project_budget_periods_handles_day_31_month_ends(self):
        periods = project_budget_periods(date(2026, 1, 31), months_ahead=3)

        self.assertEqual(
            [period.end for period in periods],
            [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30)],
        )


class CardCycleTests(TestCase):
    def test_cutoff_day_closes_the_cycle_inclusive(self):
        cycle = card_cycle(20, date(2026, 4, 20))

        self.assertEqual(cycle.start, date(2026, 3, 21))
        self.assertEqual(cycle.end, date(2026, 4, 20))

    def test_day_after_cutoff_opens_next_cycle(self):
        cycle = card_cycle(20, date(2026, 4, 21))

        self.assertEqual(cycle.start, date(2026, 4, 21))
        self.assertEqual(cycle.end, date(2026, 5, 20))

    def test_cycle_crosses_month_boundary(self):
        cycle = card_cycle(20, date(2026, 5, 5))

        self.assertEqual(cycle.start, date(2026, 4, 21))
        self.assertEqual(cycle.end, date(2026, 5, 20))

    def test_cutoff_28_next_to_non_leap_february_starts_on_march_first(self):
        cycle = card_cycle(28, date(2027, 3, 10))

        self.assertEqual(cycle.start, date(2027, 3, 1))
        self.assertEqual(cycle.end, date(2027, 3, 28))

    def test_cutoff_28_next_to_leap_february_starts_on_february_29(self):
        cycle = card_cycle(28, date(2028, 3, 10))

        self.assertEqual(cycle.start, date(2028, 2, 29))
        self.assertEqual(cycle.end, date(2028, 3, 28))

    def test_cutoff_28_cycle_containing_february_ends_on_february_28(self):
        cycle = card_cycle(28, date(2027, 2, 15))

        self.assertEqual(cycle.start, date(2027, 1, 29))
        self.assertEqual(cycle.end, date(2027, 2, 28))

    def test_last_closed_card_cycle_is_previous_to_the_open_one(self):
        cycle = last_closed_card_cycle(20, date(2026, 4, 25))

        self.assertEqual(cycle.start, date(2026, 3, 21))
        self.assertEqual(cycle.end, date(2026, 4, 20))

    def test_card_cycle_for_offset_moves_whole_cycles(self):
        cycle = card_cycle_for_offset(20, date(2026, 4, 25), 1)

        self.assertEqual(cycle.start, date(2026, 5, 21))
        self.assertEqual(cycle.end, date(2026, 6, 20))


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
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
        )
        BudgetAllocation.objects.filter(category=self.global_category, period_start__gte=date(2026, 4, 1)).update(
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
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
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

        record = CategoryOverspendRecord.objects.get(category=self.personal_category, period_start=date(2026, 3, 1))
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

    def test_tracking_only_category_is_excluded_from_budget_summary_allocations_and_card_payment(self):
        external = Category.objects.create(
            name="Tarjeta ajena",
            scope=Category.Scope.GLOBAL,
            budget_treatment=Category.BudgetTreatment.TRACKING_ONLY,
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPENSE,
            merchant="Compra externa",
            amount_cents=75000,
            date=date(2026, 4, 25),
            category=external,
            created_by=self.user,
        )

        summary = build_budget_summary(date(2026, 4, 25), scope="total")
        card_payment = card_payments_summary(date(2026, 4, 25))

        self.assertEqual(summary["totals"]["budget_cents"], 600000)
        self.assertEqual(summary["totals"]["spent_cents"], 0)
        self.assertNotIn(external.id, [item["category_id"] for item in summary["categories"]])
        self.assertFalse(BudgetAllocation.objects.filter(category=external).exists())
        self.assertEqual(card_payment["total_cents"], 0)
        self.assertEqual(account_balance(self.cash), 0)

    def test_off_budget_summary_tracks_manual_and_expected_debts_separately(self):
        external = Category.objects.create(
            name="Deuda no presupuestada",
            scope=Category.Scope.GLOBAL,
            budget_treatment=Category.BudgetTreatment.TRACKING_ONLY,
            icon="credit-card",
            color="#7c3aed",
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPENSE,
            merchant="Prestamo familiar",
            amount_cents=50000,
            date=date(2026, 4, 25),
            category=external,
            created_by=self.user,
        )
        RecurringExpense.objects.create(
            name="Pago externo mensual",
            merchant="Banco externo",
            amount_cents=12000,
            category=external,
            start_date=date(2026, 4, 21),
            charge_day=25,
        )
        InstallmentPlan.objects.create(
            name="Compra tarjeta ajena",
            merchant="Liverpool",
            total_amount_cents=240000,
            category=external,
            start_date=date(2026, 4, 21),
            end_date=date(2026, 5, 21),
        )

        summary = build_off_budget_summary(date(2026, 4, 25))

        self.assertEqual(summary["totals"]["spent_cents"], 50000)
        self.assertEqual(summary["totals"]["expected_cents"], 132000)
        self.assertEqual(summary["totals"]["total_cents"], 182000)
        self.assertEqual(summary["categories"][0]["category_name"], "Deuda no presupuestada")
        self.assertEqual(summary["categories"][0]["spent_cents"], 50000)
        self.assertEqual(summary["categories"][0]["expected_cents"], 132000)
        self.assertEqual(len(summary["expected_charges"]), 2)

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


class LiveWindowSummaryTests(TestCase):
    """Ventana viva: disponible = allocation - gasto no-tarjeta del mes - gasto vivo por tarjeta - expected."""

    def setUp(self):
        self.user = User.objects.create_user(username="admin", password="testpass123")
        self.cash = Account.objects.create(name="Caja", account_type=Account.AccountType.CASH)
        self.card = Account.objects.create(
            name="Tarjeta",
            account_type=Account.AccountType.CREDIT_CARD,
            cutoff_day=20,
        )
        self.food = Category.objects.create(
            name="Comida",
            scope=Category.Scope.GLOBAL,
            monthly_budget_cents=1000000,
            overspend_tracking_start_date=date(2026, 7, 1),
        )

    def expense(self, amount_cents, when, account, category=None):
        return Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPENSE,
            merchant="Gasto",
            amount_cents=amount_cents,
            date=when,
            account=account,
            category=category or self.food,
            created_by=self.user,
        )

    def summary_on(self, query_date, today):
        with patch("budget.services.app_localdate", return_value=today):
            return build_budget_summary(query_date, scope="family")

    def row_on(self, query_date, today, name="Comida"):
        summary = self.summary_on(query_date, today)
        return next(row for row in summary["categories"] if row["category_name"] == name)

    def test_live_window_current_month_before_cut(self):
        self.expense(500000, date(2026, 7, 10), self.card)
        self.expense(200000, date(2026, 7, 12), self.cash)

        row = self.row_on(date(2026, 7, 15), date(2026, 7, 15))

        self.assertEqual(row["available_cents"], 300000)
        self.assertEqual(row["spent_cents"], 700000)
        self.assertEqual(row["real_available_cents"], 300000)
        self.assertEqual(row["monthly_flow_cents"], 700000)
        self.assertEqual(len(row["live_windows"]), 2)
        windows = {window["kind"]: window for window in row["live_windows"]}
        self.assertEqual(windows["month"]["spent_cents"], 200000)
        self.assertEqual(windows["card"]["account_id"], self.card.id)
        self.assertEqual(windows["card"]["account_name"], "Tarjeta")
        self.assertEqual(windows["card"]["spent_cents"], 500000)
        self.assertEqual(windows["card"]["start"], date(2026, 6, 21))
        self.assertEqual(windows["card"]["end"], date(2026, 7, 20))

    def test_liberation_exactly_on_cut_day(self):
        self.expense(500000, date(2026, 7, 20), self.card)

        on_cut_day = self.row_on(date(2026, 7, 20), date(2026, 7, 20))
        day_after_cut = self.row_on(date(2026, 7, 20), date(2026, 7, 21))

        self.assertEqual(on_cut_day["available_cents"], 500000)
        self.assertEqual(day_after_cut["available_cents"], 1000000)
        self.assertEqual([window["kind"] for window in day_after_cut["live_windows"]], ["month"])

    def test_liberation_after_cut_keeps_month_spend(self):
        self.expense(500000, date(2026, 7, 10), self.card)
        self.expense(200000, date(2026, 7, 12), self.cash)

        row = self.row_on(date(2026, 7, 21), date(2026, 7, 21))

        self.assertEqual(row["available_cents"], 800000)
        self.assertEqual(row["spent_cents"], 200000)
        self.assertEqual(row["monthly_flow_cents"], 700000)
        self.assertEqual([window["kind"] for window in row["live_windows"]], ["month"])

    def test_post_cut_purchase_crosses_into_next_month(self):
        self.expense(500000, date(2026, 7, 10), self.card)
        self.expense(200000, date(2026, 7, 12), self.cash)
        self.expense(400000, date(2026, 7, 25), self.card)

        july = self.row_on(date(2026, 7, 28), date(2026, 7, 28))
        august = self.row_on(date(2026, 8, 5), date(2026, 8, 5))

        self.assertEqual(july["available_cents"], 400000)
        self.assertEqual(august["available_cents"], 600000)
        self.assertEqual(august["spent_cents"], 400000)
        self.assertEqual(august["monthly_flow_cents"], 0)
        card_window = next(window for window in august["live_windows"] if window["kind"] == "card")
        self.assertEqual(card_window["spent_cents"], 400000)
        self.assertEqual(card_window["start"], date(2026, 7, 21))
        self.assertEqual(card_window["end"], date(2026, 8, 20))

    def test_closing_snapshot_is_immutable(self):
        self.expense(500000, date(2026, 7, 10), self.card)
        self.expense(200000, date(2026, 7, 12), self.cash)
        self.expense(400000, date(2026, 7, 25), self.card)

        seen_from_august = self.row_on(date(2026, 7, 31), date(2026, 8, 10))
        seen_from_september = self.row_on(date(2026, 7, 31), date(2026, 9, 3))

        self.assertEqual(seen_from_august["available_cents"], 400000)
        self.assertEqual(seen_from_september["available_cents"], 400000)

    def test_february_cutoff_28_release(self):
        card28 = Account.objects.create(
            name="Tarjeta 28",
            account_type=Account.AccountType.CREDIT_CARD,
            cutoff_day=28,
        )
        self.expense(300000, date(2026, 2, 15), card28)

        february = self.row_on(date(2026, 2, 20), date(2026, 2, 20))
        march = self.row_on(date(2026, 3, 5), date(2026, 3, 5))

        self.assertEqual(february["available_cents"], 700000)
        self.assertEqual(march["available_cents"], 1000000)
        self.assertEqual([window["kind"] for window in march["live_windows"]], ["month"])

    def test_carryover_not_recharged_at_cut(self):
        travel = Category.objects.create(
            name="Viajes",
            scope=Category.Scope.GLOBAL,
            budget_behavior=Category.BudgetBehavior.CARRYOVER,
            carryover_initial_balance_cents=0,
            carryover_start_date=date(2026, 7, 1),
        )
        CategoryBudgetChange.objects.create(
            category=travel,
            amount_cents=1000000,
            effective_date=date(2026, 7, 1),
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 31),
        )
        self.expense(300000, date(2026, 7, 10), self.card, category=travel)

        before_cut = self.row_on(date(2026, 7, 15), date(2026, 7, 15), name="Viajes")
        after_cut = self.row_on(date(2026, 7, 25), date(2026, 7, 25), name="Viajes")

        self.assertEqual(before_cut["real_available_cents"], 700000)
        self.assertEqual(before_cut["live_windows"], [])
        self.assertEqual(after_cut["real_available_cents"], 700000)
        self.assertEqual(after_cut["spent_cents"], 300000)

    def test_overspend_record_uses_live_available_at_close(self):
        self.expense(1200000, date(2026, 7, 12), self.cash)

        self.summary_on(date(2026, 8, 5), date(2026, 8, 5))

        record = CategoryOverspendRecord.objects.get(category=self.food, period_start=date(2026, 7, 1))
        self.assertEqual(record.overspend_cents, 200000)
        self.assertEqual(record.budget_cents, 1000000)
        self.assertEqual(record.spent_cents, 1200000)

    def test_liberated_card_spend_does_not_create_overspend_record(self):
        self.expense(1200000, date(2026, 7, 5), self.card)

        self.summary_on(date(2026, 8, 5), date(2026, 8, 5))
        july_close = self.row_on(date(2026, 7, 31), date(2026, 8, 5))

        self.assertFalse(
            CategoryOverspendRecord.objects.filter(category=self.food, period_start=date(2026, 7, 1)).exists()
        )
        self.assertEqual(july_close["monthly_flow_cents"], 1200000)
        self.assertEqual(july_close["available_cents"], 1000000)


class ExpectedChargeTests(TestCase):
    def setUp(self):
        self.member = HouseholdMember.objects.create(name="Luis", color="#2563eb")
        self.card = Account.objects.create(
            name="Tarjeta dorada",
            account_type=Account.AccountType.CREDIT_CARD,
            cutoff_day=20,
        )
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

    def test_auto_charge_recurring_posts_due_transaction_once(self):
        recurring = RecurringExpense.objects.create(
            name="Netflix",
            merchant="Netflix",
            amount_cents=29900,
            category=self.category,
            account=self.card,
            start_date=date(2026, 4, 1),
            charge_day=5,
            auto_charge=True,
        )

        first_run = auto_post_due_recurring_charges(date(2026, 4, 25))
        second_run = auto_post_due_recurring_charges(date(2026, 4, 25))

        self.assertEqual(len(first_run), 1)
        self.assertEqual(len(second_run), 0)
        transaction = Transaction.objects.get(recurring_expense=recurring)
        self.assertEqual(transaction.transaction_type, Transaction.TransactionType.EXPENSE)
        self.assertEqual(transaction.date, date(2026, 4, 5))
        self.assertEqual(transaction.account, self.card)
        self.assertEqual(transaction.amount_cents, 29900)

    def test_auto_charge_does_not_backfill_previous_calendar_months(self):
        recurring = RecurringExpense.objects.create(
            name="Netflix",
            merchant="Netflix",
            amount_cents=29900,
            category=self.category,
            account=self.card,
            start_date=date(2026, 2, 1),
            charge_day=5,
            auto_charge=True,
        )

        created = auto_post_due_recurring_charges(date(2026, 4, 25))

        self.assertEqual(len(created), 1)
        transaction = Transaction.objects.get(recurring_expense=recurring)
        self.assertEqual(transaction.date, date(2026, 4, 5))

    def test_auto_charge_requires_configured_account(self):
        recurring = RecurringExpense(
            name="Netflix",
            merchant="Netflix",
            amount_cents=29900,
            category=self.category,
            start_date=date(2026, 4, 1),
            charge_day=5,
            auto_charge=True,
        )

        with self.assertRaises(ValidationError):
            recurring.full_clean()

    def test_installment_plan_consumes_only_monthly_payment(self):
        InstallmentPlan.objects.create(
            name="Laptop",
            merchant="Liverpool",
            total_amount_cents=1200000,
            category=self.category,
            account=self.card,
            start_date=date(2026, 4, 10),
            end_date=date(2026, 6, 10),
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
            start_date=date(2026, 4, 10),
            end_date=date(2026, 6, 10),
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
            start_date=date(2026, 4, 10),
            end_date=date(2026, 12, 10),
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
            start_date=date(2026, 4, 10),
            end_date=date(2027, 3, 10),
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

    def test_interest_free_payment_summary_groups_cycle_card_purchases_and_installments_by_credit_card(self):
        other_card = Account.objects.create(
            name="Tarjeta azul",
            account_type=Account.AccountType.CREDIT_CARD,
            cutoff_day=20,
        )
        debit = Account.objects.create(name="Debito", account_type=Account.AccountType.DEBIT_CARD)
        plan = InstallmentPlan.objects.create(
            name="Laptop",
            merchant="Liverpool",
            total_amount_cents=600000,
            category=self.category,
            account=self.card,
            start_date=date(2026, 4, 21),
            end_date=date(2026, 6, 21),
        )
        InstallmentPlan.objects.create(
            name="Celular",
            merchant="Apple",
            total_amount_cents=300000,
            category=self.category,
            account=other_card,
            start_date=date(2026, 4, 21),
            end_date=date(2026, 6, 21),
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPENSE,
            merchant="Super",
            amount_cents=100000,
            date=date(2026, 4, 25),
            account=self.card,
            category=self.category,
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPENSE,
            merchant="Ciclo anterior",
            amount_cents=50000,
            date=date(2026, 4, 20),
            account=self.card,
            category=self.category,
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPENSE,
            merchant="Pago confirmado MSI",
            amount_cents=200000,
            date=date(2026, 4, 25),
            account=self.card,
            category=self.category,
            installment_plan=plan,
        )
        Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPENSE,
            merchant="Debito",
            amount_cents=70000,
            date=date(2026, 4, 25),
            account=debit,
            category=self.category,
        )

        summary = card_payments_summary(date(2026, 4, 25))
        rows = {row["account_name"]: row for row in summary["cards"]}

        self.assertNotIn("period", summary)
        self.assertEqual(set(rows), {"Tarjeta dorada", "Tarjeta azul"})
        dorada = rows["Tarjeta dorada"]
        self.assertEqual(dorada["open_cycle"]["start"], date(2026, 4, 21))
        self.assertEqual(dorada["open_cycle"]["end"], date(2026, 5, 20))
        self.assertEqual(dorada["open_cycle"]["purchase_cents"], 100000)
        self.assertEqual(dorada["open_cycle"]["installment_cents"], 200000)
        self.assertEqual(dorada["open_cycle"]["total_cents"], 300000)
        self.assertEqual(dorada["closed_cycle"]["start"], date(2026, 3, 21))
        self.assertEqual(dorada["closed_cycle"]["end"], date(2026, 4, 20))
        self.assertEqual(dorada["closed_cycle"]["purchase_cents"], 50000)
        self.assertEqual(dorada["closed_cycle"]["installment_cents"], 0)
        self.assertEqual(dorada["closed_cycle"]["total_cents"], 50000)
        azul = rows["Tarjeta azul"]
        self.assertEqual(azul["open_cycle"]["purchase_cents"], 0)
        self.assertEqual(azul["open_cycle"]["installment_cents"], 100000)
        self.assertEqual(azul["open_cycle"]["total_cents"], 100000)
        self.assertEqual(azul["closed_cycle"]["total_cents"], 0)
        self.assertEqual(summary["total_cents"], 50000)

    def test_card_installment_is_numbered_by_card_cycles_across_month_boundary(self):
        plan = InstallmentPlan.objects.create(
            name="Pantalla",
            merchant="Liverpool",
            total_amount_cents=900000,
            category=self.category,
            account=self.card,
            start_date=date(2026, 4, 21),
            end_date=date(2026, 6, 21),
        )

        first_cycle = card_cycle(20, date(2026, 4, 21))
        second_cycle = card_cycle_for_offset(20, date(2026, 4, 21), 1)
        third_cycle = card_cycle_for_offset(20, date(2026, 4, 21), 2)

        first_payment = installment_charge_for_period(plan, first_cycle)
        self.assertEqual(first_payment["payment_number"], 1)
        self.assertEqual(first_payment["amount_cents"], 300000)
        self.assertEqual(installment_charge_for_period(plan, second_cycle)["payment_number"], 2)
        self.assertEqual(installment_charge_for_period(plan, third_cycle)["payment_number"], 3)
        self.assertIsNone(installment_charge_for_period(plan, previous_card_cycle(20, first_cycle)))

    def test_card_installment_expected_charge_lands_in_corte_month(self):
        plan = InstallmentPlan.objects.create(
            name="Pantalla",
            merchant="Liverpool",
            total_amount_cents=900000,
            category=self.category,
            account=self.card,
            start_date=date(2026, 4, 21),
            end_date=date(2026, 6, 21),
        )

        april = expected_charges_for_period(get_budget_period(date(2026, 4, 25)))
        may = expected_charges_for_period(get_budget_period(date(2026, 5, 25)))
        july = expected_charges_for_period(get_budget_period(date(2026, 7, 25)))

        self.assertNotIn(plan.id, [charge.source_id for charge in april if charge.source_type == "installment"])
        may_charge = next(charge for charge in may if charge.source_id == plan.id)
        self.assertEqual(may_charge.payment_number, 1)
        self.assertEqual(may_charge.amount_cents, 300000)
        july_charge = next(charge for charge in july if charge.source_id == plan.id)
        self.assertEqual(july_charge.payment_number, 3)
        self.assertEqual(july_charge.amount_cents, 300000)

    def test_non_card_installment_uses_calendar_month_numbering(self):
        plan = InstallmentPlan.objects.create(
            name="Pantalla sin tarjeta",
            merchant="Liverpool",
            total_amount_cents=900000,
            category=self.category,
            start_date=date(2026, 4, 21),
            end_date=date(2026, 6, 21),
        )

        april = expected_charges_for_period(get_budget_period(date(2026, 4, 25)))

        april_charge = next(charge for charge in april if charge.source_id == plan.id)
        self.assertEqual(april_charge.payment_number, 1)
        self.assertEqual(april_charge.amount_cents, 300000)

    def test_installment_projection_month_mode_breaks_down_by_card(self):
        InstallmentPlan.objects.create(
            name="Pantalla",
            merchant="Liverpool",
            total_amount_cents=900000,
            category=self.category,
            account=self.card,
            start_date=date(2026, 4, 10),
            end_date=date(2026, 6, 10),
        )
        InstallmentPlan.objects.create(
            name="Colchon sin tarjeta",
            merchant="Costco",
            total_amount_cents=200000,
            category=self.category,
            start_date=date(2026, 4, 10),
            end_date=date(2026, 5, 10),
        )

        projection = installment_projection(date(2026, 4, 25))

        self.assertEqual(projection["mode"], "month")
        self.assertIsNone(projection["account"])
        self.assertEqual(projection["periods"][0]["key"], "2026-04")
        self.assertEqual(projection["periods"][0]["total_cents"], 400000)
        cards = {row["account_id"]: row["total_cents"] for row in projection["periods"][0]["cards"]}
        self.assertEqual(cards[self.card.id], 300000)
        self.assertEqual(cards[None], 100000)
        first_plan = projection["periods"][0]["plans"][0]
        self.assertIn("account", first_plan)
        self.assertIn("owner", first_plan)

    def test_installment_projection_account_filter_uses_real_card_cycles(self):
        InstallmentPlan.objects.create(
            name="Pantalla",
            merchant="Liverpool",
            total_amount_cents=900000,
            category=self.category,
            account=self.card,
            start_date=date(2026, 4, 21),
            end_date=date(2026, 6, 21),
        )

        projection = installment_projection(date(2026, 4, 25), months_ahead=3, account_id=self.card.id)

        self.assertEqual(projection["mode"], "cycle")
        self.assertEqual(projection["account"]["id"], self.card.id)
        self.assertEqual(projection["account"]["cutoff_day"], 20)
        self.assertEqual(projection["current_period_key"], "2026-05-20")
        self.assertEqual(projection["periods"][0]["start"], date(2026, 4, 21))
        self.assertEqual(projection["periods"][0]["end"], date(2026, 5, 20))
        self.assertEqual(projection["periods"][0]["total_cents"], 300000)
        self.assertEqual(projection["periods"][1]["key"], "2026-06-20")
        self.assertEqual(projection["periods"][1]["total_cents"], 300000)
        self.assertEqual(projection["periods"][2]["key"], "2026-07-20")
        self.assertEqual(projection["periods"][2]["total_cents"], 300000)
        self.assertEqual(projection["periods"][3]["key"], "2026-08-20")
        self.assertEqual(projection["periods"][3]["total_cents"], 0)

    def test_dismissed_card_installment_is_anchored_to_cycle(self):
        plan = InstallmentPlan.objects.create(
            name="Pantalla",
            merchant="Liverpool",
            total_amount_cents=900000,
            category=self.category,
            account=self.card,
            start_date=date(2026, 4, 21),
            end_date=date(2026, 6, 21),
        )
        may_period = get_budget_period(date(2026, 5, 25))

        self.assertIn(plan.id, [charge.source_id for charge in expected_charges_for_period(may_period)])

        cycle_dismissal = ExpectedChargeDismissal.objects.create(
            source_type="installment", source_id=plan.id, period_start=date(2026, 4, 21)
        )
        self.assertNotIn(plan.id, [charge.source_id for charge in expected_charges_for_period(may_period)])

        cycle_dismissal.delete()
        ExpectedChargeDismissal.objects.create(
            source_type="installment", source_id=plan.id, period_start=date(2026, 5, 1)
        )
        self.assertNotIn(plan.id, [charge.source_id for charge in expected_charges_for_period(may_period)])

    def test_confirming_card_installment_in_cycle_is_idempotent(self):
        user = User.objects.create_user(username="confirmador", password="testpass123")
        plan = InstallmentPlan.objects.create(
            name="Pantalla",
            merchant="Liverpool",
            total_amount_cents=900000,
            category=self.category,
            account=self.card,
            start_date=date(2026, 4, 21),
            end_date=date(2026, 6, 21),
        )

        transaction = confirm_expected_charge("installment", plan.id, date(2026, 4, 25), self.card, user)

        self.assertEqual(transaction.amount_cents, 300000)
        self.assertEqual(transaction.date, date(2026, 4, 25))
        may_charges = expected_charges_for_period(get_budget_period(date(2026, 5, 25)))
        self.assertNotIn(plan.id, [charge.source_id for charge in may_charges])


class CardPaymentsSummaryTests(TestCase):
    def setUp(self):
        self.ana = HouseholdMember.objects.create(name="Ana", color="#2563eb")
        self.beto = HouseholdMember.objects.create(name="Beto", color="#dc2626")
        self.oro = Account.objects.create(
            name="Oro", account_type=Account.AccountType.CREDIT_CARD, cutoff_day=20, owner=self.ana
        )
        self.azul = Account.objects.create(
            name="Azul", account_type=Account.AccountType.CREDIT_CARD, cutoff_day=5, owner=self.beto
        )
        self.category = Category.objects.create(
            name="Compras", scope=Category.Scope.GLOBAL, monthly_budget_cents=500000
        )

    def expense(self, amount_cents, when, account, **kwargs):
        return Transaction.objects.create(
            transaction_type=Transaction.TransactionType.EXPENSE,
            merchant="Comercio",
            amount_cents=amount_cents,
            date=when,
            account=account,
            category=kwargs.pop("category", self.category),
            **kwargs,
        )

    def test_last_closed_and_open_cycle_around_cutoff_day(self):
        self.expense(30000, date(2026, 4, 20), self.oro)

        on_cutoff = card_payments_summary(date(2026, 4, 20))
        after_cutoff = card_payments_summary(date(2026, 4, 21))

        oro_on = next(row for row in on_cutoff["cards"] if row["account_id"] == self.oro.id)
        self.assertEqual(oro_on["open_cycle"]["start"], date(2026, 3, 21))
        self.assertEqual(oro_on["open_cycle"]["end"], date(2026, 4, 20))
        self.assertEqual(oro_on["open_cycle"]["purchase_cents"], 30000)
        self.assertEqual(oro_on["closed_cycle"]["start"], date(2026, 2, 21))
        self.assertEqual(oro_on["closed_cycle"]["end"], date(2026, 3, 20))
        self.assertEqual(oro_on["closed_cycle"]["purchase_cents"], 0)
        self.assertEqual(on_cutoff["total_cents"], 0)

        oro_after = next(row for row in after_cutoff["cards"] if row["account_id"] == self.oro.id)
        self.assertEqual(oro_after["closed_cycle"]["start"], date(2026, 3, 21))
        self.assertEqual(oro_after["closed_cycle"]["end"], date(2026, 4, 20))
        self.assertEqual(oro_after["closed_cycle"]["purchase_cents"], 30000)
        self.assertEqual(oro_after["open_cycle"]["start"], date(2026, 4, 21))
        self.assertEqual(oro_after["open_cycle"]["purchase_cents"], 0)
        self.assertEqual(after_cutoff["total_cents"], 30000)

    def test_card_payments_summary_groups_closed_open_and_owners(self):
        tracking = Category.objects.create(
            name="Externa",
            scope=Category.Scope.GLOBAL,
            budget_treatment=Category.BudgetTreatment.TRACKING_ONLY,
        )
        plan = InstallmentPlan.objects.create(
            name="Laptop",
            merchant="Liverpool",
            total_amount_cents=600000,
            category=self.category,
            account=self.oro,
            start_date=date(2026, 3, 21),
            end_date=date(2026, 5, 21),
        )
        self.expense(30000, date(2026, 4, 10), self.oro)
        self.expense(50000, date(2026, 5, 1), self.oro)
        self.expense(99999, date(2026, 5, 1), self.oro, category=tracking)
        self.expense(12345, date(2026, 5, 1), self.oro, installment_plan=plan)
        self.expense(20000, date(2026, 4, 20), self.azul)
        self.expense(40000, date(2026, 5, 8), self.azul)

        summary = card_payments_summary(date(2026, 5, 10))

        rows = {row["account_name"]: row for row in summary["cards"]}
        self.assertEqual(summary["total_cents"], 250000)
        oro = rows["Oro"]
        self.assertEqual(oro["closed_cycle"]["start"], date(2026, 3, 21))
        self.assertEqual(oro["closed_cycle"]["end"], date(2026, 4, 20))
        self.assertEqual(oro["closed_cycle"]["purchase_cents"], 30000)
        self.assertEqual(oro["closed_cycle"]["installment_cents"], 200000)
        self.assertEqual(oro["closed_cycle"]["total_cents"], 230000)
        self.assertEqual(oro["open_cycle"]["start"], date(2026, 4, 21))
        self.assertEqual(oro["open_cycle"]["end"], date(2026, 5, 20))
        self.assertEqual(oro["open_cycle"]["purchase_cents"], 50000)
        self.assertEqual(oro["open_cycle"]["installment_cents"], 200000)
        self.assertEqual(oro["open_cycle"]["total_cents"], 250000)
        self.assertEqual(oro["owner"]["name"], "Ana")
        azul = rows["Azul"]
        self.assertEqual(azul["closed_cycle"]["start"], date(2026, 4, 6))
        self.assertEqual(azul["closed_cycle"]["end"], date(2026, 5, 5))
        self.assertEqual(azul["closed_cycle"]["purchase_cents"], 20000)
        self.assertEqual(azul["closed_cycle"]["total_cents"], 20000)
        self.assertEqual(azul["open_cycle"]["purchase_cents"], 40000)
        self.assertEqual(azul["open_cycle"]["total_cents"], 40000)
        owners = {(bucket["member"] or {}).get("name"): bucket for bucket in summary["owners"]}
        self.assertEqual(owners["Ana"]["total_cents"], 230000)
        self.assertEqual(owners["Ana"]["account_ids"], [self.oro.id])
        self.assertEqual(owners["Beto"]["total_cents"], 20000)
        self.assertEqual(owners["Beto"]["account_ids"], [self.azul.id])
