from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta

from django.db import transaction as db_transaction
from django.db.models import Q, Sum

from .models import (
    Account,
    BudgetAllocation,
    Category,
    CategoryBudgetChange,
    CategoryOverspendRecord,
    ExpectedChargeDismissal,
    InstallmentPlan,
    RecurringExpense,
    Transaction,
)
from .timezones import app_localdate


SPEND_TYPES = [Transaction.TransactionType.EXPENSE, Transaction.TransactionType.EXPECTED_CHARGE]
PAYMENT_SAFETY_DAYS = 3


@dataclass(frozen=True)
class BudgetPeriod:
    start: date
    end: date


@dataclass(frozen=True)
class CardPaymentDates:
    payment_due_date: date
    safe_payment_date: date


@dataclass(frozen=True)
class LiveWindow:
    kind: str  # "month" | "card"
    start: date
    end: date
    spent_cents: int
    account_id: int | None = None
    account_name: str | None = None


@dataclass(frozen=True)
class LiveBudgetResult:
    allocation_cents: int
    month_spent_cents: int
    card_spent_cents: int
    expected_cents: int
    monthly_flow_cents: int
    windows: list[LiveWindow]
    is_carryover: bool
    carryover_balance_cents: int | None

    @property
    def live_spent_cents(self) -> int:
        return self.month_spent_cents + self.card_spent_cents

    @property
    def real_available_cents(self) -> int:
        if self.is_carryover:
            return self.carryover_balance_cents or 0
        return self.allocation_cents - self.live_spent_cents

    @property
    def available_cents(self) -> int:
        return self.real_available_cents - self.expected_cents

    @property
    def spent_cents(self) -> int:
        return self.monthly_flow_cents if self.is_carryover else self.live_spent_cents


@dataclass(frozen=True)
class ExpectedCharge:
    key: str
    source_type: str
    source_id: int
    name: str
    merchant: str
    amount_cents: int
    date: date
    period_start: date
    period_end: date
    category: Category
    account: Account | None
    payments_total: int | None = None
    payment_number: int | None = None
    total_amount_cents: int | None = None


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, value.day)


def day_in_period(period: BudgetPeriod, day: int) -> date:
    candidate = date(period.start.year, period.start.month, min(day, 28))
    if candidate < period.start:
        candidate = add_months(candidate, 1)
    return candidate


def month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def iter_month_starts(start: date, end: date):
    current = month_start(start)
    final = month_start(end)
    while current <= final:
        yield current
        current = add_months(current, 1)


def charge_dates_for_recurring_expense(recurring: RecurringExpense, as_of: date, earliest: date | None = None):
    end = min(as_of, recurring.end_date) if recurring.end_date else as_of
    start = max(recurring.start_date, earliest) if earliest else recurring.start_date
    if end < start:
        return
    for month in iter_month_starts(start, end):
        charge_date = date(month.year, month.month, recurring.charge_day)
        if charge_date < start or charge_date > end:
            continue
        yield charge_date


def month_period(value: date) -> BudgetPeriod:
    start = date(value.year, value.month, 1)
    end = date(value.year, value.month, monthrange(value.year, value.month)[1])
    return BudgetPeriod(start=start, end=end)


def get_budget_period(value: date | None = None) -> BudgetPeriod:
    return month_period(value or app_localdate())


def project_budget_periods(value: date | None = None, months_ahead: int = 6) -> list[BudgetPeriod]:
    current_period = get_budget_period(value)
    return [get_budget_period(add_months(current_period.start, offset)) for offset in range(months_ahead + 1)]


def previous_budget_period(period: BudgetPeriod) -> BudgetPeriod:
    return month_period(add_months(period.start, -1))


def period_key(period: BudgetPeriod) -> tuple[date, date]:
    return period.start, period.end


def iter_budget_periods(start_period: BudgetPeriod, end_period: BudgetPeriod):
    period = start_period
    while period_key(period) <= period_key(end_period):
        yield period
        period = month_period(add_months(period.start, 1))


def card_cycle(cutoff_day: int, value: date | None = None) -> BudgetPeriod:
    """Ciclo de tarjeta que CONTIENE `value`; el dia del corte cierra el ciclo (inclusive)."""
    value = value or app_localdate()
    if not 1 <= cutoff_day <= 28:
        raise ValueError("cutoff_day must be between 1 and 28")
    this_cutoff = date(value.year, value.month, cutoff_day)
    if value <= this_cutoff:
        end = this_cutoff
        start = add_months(this_cutoff, -1) + timedelta(days=1)
    else:
        start = this_cutoff + timedelta(days=1)
        end = add_months(this_cutoff, 1)
    return BudgetPeriod(start=start, end=end)


def previous_card_cycle(cutoff_day: int, cycle: BudgetPeriod) -> BudgetPeriod:
    return card_cycle(cutoff_day, cycle.start - timedelta(days=1))


def last_closed_card_cycle(cutoff_day: int, as_of: date | None = None) -> BudgetPeriod:
    """Ultimo ciclo cuyo corte ya cerro respecto de `as_of` (el previo al que contiene `as_of`).

    El dia EXACTO del corte cuenta como ciclo aun abierto (cierra al final de ese dia).
    """
    as_of = as_of or app_localdate()
    return previous_card_cycle(cutoff_day, card_cycle(cutoff_day, as_of))


def card_cycle_for_offset(cutoff_day: int, value: date, offset: int) -> BudgetPeriod:
    """Ciclo a `offset` ciclos del que contiene `value` (offset de ciclos == offset de meses)."""
    base = card_cycle(cutoff_day, value)
    return card_cycle(cutoff_day, add_months(base.end, offset))


def card_payment_dates(cycle: BudgetPeriod, payment_due_day: int) -> CardPaymentDates:
    """Resolve el primer limite posterior al corte y el pago preventivo tres dias antes."""
    if not 1 <= payment_due_day <= 31:
        raise ValueError("payment_due_day must be between 1 and 31")

    due_day = min(payment_due_day, monthrange(cycle.end.year, cycle.end.month)[1])
    payment_due_date = date(cycle.end.year, cycle.end.month, due_day)
    if payment_due_date <= cycle.end:
        next_month = add_months(cycle.end.replace(day=1), 1)
        due_day = min(payment_due_day, monthrange(next_month.year, next_month.month)[1])
        payment_due_date = date(next_month.year, next_month.month, due_day)

    return CardPaymentDates(
        payment_due_date=payment_due_date,
        safe_payment_date=payment_due_date - timedelta(days=PAYMENT_SAFETY_DAYS),
    )


def budget_amount_for_period(category: Category, period: BudgetPeriod) -> int:
    changes = CategoryBudgetChange.objects.filter(category=category).order_by("period_start", "created_at")
    latest_change = changes.filter(period_start__lte=period.start).order_by("-period_start", "-created_at").first()
    if latest_change:
        return latest_change.amount_cents
    first_change = changes.first()
    if first_change:
        return first_change.amount_cents
    return category.monthly_budget_cents


def ensure_category_allocation(category: Category, period: BudgetPeriod) -> BudgetAllocation:
    allocation, _ = BudgetAllocation.objects.get_or_create(
        category=category,
        period_start=period.start,
        period_end=period.end,
        defaults={"amount_cents": budget_amount_for_period(category, period)},
    )
    return allocation


def ensure_allocations(period: BudgetPeriod) -> None:
    for category in Category.objects.filter(
        is_active=True,
        budget_treatment=Category.BudgetTreatment.BUDGETED,
    ):
        ensure_category_allocation(category, period)


def record_category_budget_change(
    category: Category,
    amount_cents: int,
    effective_date: date,
    previous_amount_cents: int | None = None,
) -> CategoryBudgetChange:
    effective_period = get_budget_period(effective_date)
    today = app_localdate()
    current_period = get_budget_period(today)
    has_changes = CategoryBudgetChange.objects.filter(category=category).exists()

    if previous_amount_cents is not None and not has_changes and period_key(effective_period) > period_key(current_period):
        CategoryBudgetChange.objects.create(
            category=category,
            amount_cents=previous_amount_cents,
            effective_date=today,
            period_start=current_period.start,
            period_end=current_period.end,
        )

    change = CategoryBudgetChange.objects.create(
        category=category,
        amount_cents=amount_cents,
        effective_date=effective_date,
        period_start=effective_period.start,
        period_end=effective_period.end,
    )
    # Recalcula cada allocation afectada respetando la historia completa de cambios:
    # un cambio programado a futuro sigue gobernando sus periodos aunque este cambio
    # tenga efecto anterior. Pocas allocations por categoria; el loop es suficiente.
    for allocation in BudgetAllocation.objects.filter(category=category, period_start__gte=effective_period.start):
        amount = budget_amount_for_period(category, BudgetPeriod(start=allocation.period_start, end=allocation.period_end))
        if allocation.amount_cents != amount:
            allocation.amount_cents = amount
            allocation.save(update_fields=["amount_cents"])
    return change


def categories_for_scope(scope: str, member_id: int | None = None):
    queryset = Category.objects.filter(
        is_active=True,
        budget_treatment=Category.BudgetTreatment.BUDGETED,
    )
    if scope in ["family", "global"]:
        return queryset.filter(scope=Category.Scope.GLOBAL)
    if scope == "member":
        return queryset.filter(scope=Category.Scope.PERSONAL, member_id=member_id)
    if scope == "total":
        return queryset
    return queryset


def category_real_spend(category: Category, start_date: date, end_date: date) -> int:
    return (
        Transaction.objects.filter(
            transaction_type__in=[Transaction.TransactionType.EXPENSE, Transaction.TransactionType.EXPECTED_CHARGE],
            category=category,
            date__gte=start_date,
            date__lte=end_date,
        ).aggregate(total=Sum("amount_cents"))["total"]
        or 0
    )


def carryover_balance_for_period(category: Category, period: BudgetPeriod) -> int:
    if category.carryover_start_date is None:
        return 0
    start_period = get_budget_period(category.carryover_start_date)
    if period_key(period) < period_key(start_period):
        return category.carryover_initial_balance_cents

    credited = 0
    for credit_period in iter_budget_periods(start_period, period):
        credited += ensure_category_allocation(category, credit_period).amount_cents

    spent = category_real_spend(category, category.carryover_start_date, period.end)
    return category.carryover_initial_balance_cents + credited - spent


def resolve_as_of(period: BudgetPeriod, today: date | None = None) -> date:
    """Fecha de calculo de la ventana viva: hoy si el periodo es el mes actual; si no, fin de mes.

    Mes pasado -> foto de cierre inmutable; mes futuro -> proyeccion de cierre.
    """
    today = today or app_localdate()
    if period.start <= today <= period.end:
        return today
    return period.end


def active_credit_cards() -> list[Account]:
    # Incluye tarjetas inactivas: sus cargos vivos siguen consumiendo hasta su corte.
    return list(Account.objects.filter(account_type=Account.AccountType.CREDIT_CARD).order_by("name"))


def _spend_by_category(
    category_ids,
    start: date,
    end: date,
    *,
    account_id: int | None = None,
    exclude_credit_card: bool = False,
) -> dict[int, int]:
    queryset = Transaction.objects.filter(
        transaction_type__in=SPEND_TYPES,
        category_id__in=category_ids,
        date__gte=start,
        date__lte=end,
    )
    if account_id is not None:
        queryset = queryset.filter(account_id=account_id)
    if exclude_credit_card:
        queryset = queryset.exclude(account__account_type=Account.AccountType.CREDIT_CARD)
    rows = queryset.values("category_id").annotate(total=Sum("amount_cents"))
    return {row["category_id"]: row["total"] or 0 for row in rows}


def compute_live_budget(
    *,
    period: BudgetPeriod,
    allocation_cents: int,
    month_spent_cents: int,
    card_spend_rows: list[tuple[Account, BudgetPeriod, int]],
    expected_cents: int,
    monthly_flow_cents: int,
    carryover_balance_cents: int | None,
) -> LiveBudgetResult:
    """Unica sede de la formula de la ventana viva. Funcion pura, sin DB.

    monthly_reset: available = allocation - gasto no-tarjeta del mes - gasto vivo por tarjeta - expected.
    carryover: available = bolsa acumulada - expected (los cortes nunca recargan la bolsa).
    """
    if carryover_balance_cents is not None:
        return LiveBudgetResult(
            allocation_cents=allocation_cents,
            month_spent_cents=0,
            card_spent_cents=0,
            expected_cents=expected_cents,
            monthly_flow_cents=monthly_flow_cents,
            windows=[],
            is_carryover=True,
            carryover_balance_cents=carryover_balance_cents,
        )

    windows = [LiveWindow(kind="month", start=period.start, end=period.end, spent_cents=month_spent_cents)]
    card_spent = 0
    for account, cycle, cents in card_spend_rows:
        if cents <= 0:
            continue
        card_spent += cents
        windows.append(
            LiveWindow(
                kind="card",
                start=cycle.start,
                end=cycle.end,
                spent_cents=cents,
                account_id=account.id,
                account_name=account.name,
            )
        )
    return LiveBudgetResult(
        allocation_cents=allocation_cents,
        month_spent_cents=month_spent_cents,
        card_spent_cents=card_spent,
        expected_cents=expected_cents,
        monthly_flow_cents=monthly_flow_cents,
        windows=windows,
        is_carryover=False,
        carryover_balance_cents=None,
    )


def live_budget_for_category(
    category: Category,
    period: BudgetPeriod,
    as_of: date | None = None,
    cards: list[Account] | None = None,
) -> LiveBudgetResult:
    as_of = as_of or resolve_as_of(period)
    allocation = ensure_category_allocation(category, period).amount_cents
    monthly_flow = _spend_by_category([category.id], period.start, period.end).get(category.id, 0)
    expected = sum(
        charge.amount_cents
        for charge in expected_charges_for_period(period)
        if charge.category.id == category.id
    )

    if category.budget_behavior == Category.BudgetBehavior.CARRYOVER:
        return compute_live_budget(
            period=period,
            allocation_cents=allocation,
            month_spent_cents=0,
            card_spend_rows=[],
            expected_cents=expected,
            monthly_flow_cents=monthly_flow,
            carryover_balance_cents=carryover_balance_for_period(category, period),
        )

    month_spent = _spend_by_category(
        [category.id], period.start, as_of, exclude_credit_card=True
    ).get(category.id, 0)
    if cards is None:
        cards = active_credit_cards()
    card_spend_rows: list[tuple[Account, BudgetPeriod, int]] = []
    for card in cards:
        cycle = card_cycle(card.cutoff_day, as_of)
        # date <= as_of ya recorta la foto de cierre (as_of <= cycle.end por construccion);
        # no hace falta clamp adicional contra cycle.end.
        spent = _spend_by_category([category.id], cycle.start, as_of, account_id=card.id).get(category.id, 0)
        if spent > 0:
            card_spend_rows.append((card, cycle, spent))
    return compute_live_budget(
        period=period,
        allocation_cents=allocation,
        month_spent_cents=month_spent,
        card_spend_rows=card_spend_rows,
        expected_cents=expected,
        monthly_flow_cents=monthly_flow,
        carryover_balance_cents=None,
    )


def sync_monthly_overspend_record(
    category: Category,
    period: BudgetPeriod,
    cards: list[Account] | None = None,
) -> None:
    if category.budget_behavior != Category.BudgetBehavior.MONTHLY_RESET:
        return
    tracking_period = get_budget_period(category.overspend_tracking_start_date)
    if period_key(period) < period_key(tracking_period) or period.end >= app_localdate():
        return

    # Sobregiro = disponible vivo negativo al cierre del mes (misma formula de la ventana viva,
    # anclada a fin de mes). El flujo mensual sobre presupuesto NO es sobregiro si hubo liberacion.
    result = live_budget_for_category(category, period, as_of=period.end, cards=cards)
    overspend = max(-result.available_cents, 0)
    if overspend:
        CategoryOverspendRecord.objects.update_or_create(
            category=category,
            period_start=period.start,
            period_end=period.end,
            defaults={
                "budget_cents": result.allocation_cents,
                "spent_cents": result.live_spent_cents,
                "overspend_cents": overspend,
            },
        )
    else:
        CategoryOverspendRecord.objects.filter(
            category=category,
            period_start=period.start,
            period_end=period.end,
        ).delete()


def sync_closed_overspend_records(categories: list[Category], requested_period: BudgetPeriod) -> None:
    active_period = get_budget_period(app_localdate())
    last_closed_period = previous_budget_period(active_period)
    if period_key(requested_period) < period_key(last_closed_period):
        last_period = requested_period
    else:
        last_period = last_closed_period

    cards = active_credit_cards()
    for category in categories:
        if category.budget_behavior != Category.BudgetBehavior.MONTHLY_RESET:
            continue
        tracking_period = get_budget_period(category.overspend_tracking_start_date)
        if period_key(tracking_period) > period_key(last_period):
            continue
        for period in iter_budget_periods(tracking_period, last_period):
            sync_monthly_overspend_record(category, period, cards=cards)


def overspend_history_for_categories(category_ids: list[int]) -> dict[int, dict]:
    history: dict[int, dict] = {}
    records = CategoryOverspendRecord.objects.filter(category_id__in=category_ids).order_by("category_id", "period_start")
    for record in records:
        item = history.setdefault(
            record.category_id,
            {
                "overspend_count": 0,
                "overspend_total_cents": 0,
                "last_overspend_cents": 0,
                "last_overspend_period_start": None,
                "last_overspend_period_end": None,
            },
        )
        item["overspend_count"] += 1
        item["overspend_total_cents"] += record.overspend_cents
        item["last_overspend_cents"] = record.overspend_cents
        item["last_overspend_period_start"] = record.period_start
        item["last_overspend_period_end"] = record.period_end
    return history


def expected_charge_dismissal_period_start(account: Account | None, charge_date: date) -> date:
    """Ancla del descarte: inicio del ciclo de la tarjeta si el cargo está anclado a una
    tarjeta de crédito; primer día del mes calendario en cualquier otro caso."""
    if account is not None and account.account_type == Account.AccountType.CREDIT_CARD:
        return card_cycle(account.cutoff_day, charge_date).start
    return month_start(charge_date)


def expected_charge_source_account(source_type: str, source_id: int) -> Account | None:
    if source_type == "installment":
        plan = InstallmentPlan.objects.filter(pk=source_id).select_related("account").first()
        return plan.account if plan else None
    if source_type == "recurring":
        recurring = RecurringExpense.objects.filter(pk=source_id).select_related("account").first()
        return recurring.account if recurring else None
    return None


def expected_charges_for_period(period: BudgetPeriod):
    # Los descartes de cargos anclados a tarjeta se clavan por inicio de ciclo de la tarjeta;
    # el resto por inicio de mes. La ventana cubre ambas anclas, y se acepta también el ancla
    # de mes para descartes históricos previos al re-anclaje por ciclo.
    dismissal_lookup = set(
        ExpectedChargeDismissal.objects.filter(
            period_start__gte=add_months(period.start, -1),
            period_start__lte=period.end,
        ).values_list("source_type", "source_id", "period_start")
    )
    charges: list[ExpectedCharge] = []

    recurring_queryset = RecurringExpense.objects.filter(
        is_active=True,
        start_date__lte=period.end,
    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=period.start))

    for recurring in recurring_queryset.select_related("category", "category__member", "account"):
        already_confirmed = Transaction.objects.filter(
            recurring_expense=recurring,
            transaction_type=Transaction.TransactionType.EXPENSE,
            date__gte=period.start,
            date__lte=period.end,
        ).exists()
        if already_confirmed:
            continue
        charge_date = day_in_period(period, recurring.charge_day)
        if charge_date < recurring.start_date:
            charge_date = recurring.start_date
        anchor = expected_charge_dismissal_period_start(recurring.account, charge_date)
        if ("recurring", recurring.id, anchor) in dismissal_lookup or (
            "recurring",
            recurring.id,
            period.start,
        ) in dismissal_lookup:
            continue
        charges.append(
            ExpectedCharge(
                key=f"recurring:{recurring.id}:{period.start.isoformat()}",
                source_type="recurring",
                source_id=recurring.id,
                name=recurring.name,
                merchant=recurring.merchant,
                amount_cents=recurring.amount_cents,
                date=charge_date,
                period_start=period.start,
                period_end=period.end,
                category=recurring.category,
                account=recurring.account,
            )
        )

    # end_date ampliado un mes hacia atrás: el último corte de un plan con tarjeta puede caer
    # un mes calendario después de end_date; el rango de payment_number filtra con precisión.
    plans = InstallmentPlan.objects.filter(
        is_active=True,
        start_date__lte=period.end,
        end_date__gte=add_months(period.start, -1),
    ).select_related("category", "category__member", "account")

    for plan in plans:
        payment = installment_charge_for_period(plan, period)
        if payment is None:
            continue
        charge_date = max(period.start, plan.start_date)
        anchor = expected_charge_dismissal_period_start(plan.account, charge_date)
        if ("installment", plan.id, anchor) in dismissal_lookup or (
            "installment",
            plan.id,
            period.start,
        ) in dismissal_lookup:
            continue
        if plan.account is not None and plan.account.account_type == Account.AccountType.CREDIT_CARD:
            # Idempotencia por ciclo: una mensualidad por estado de cuenta.
            cycle = card_cycle(plan.account.cutoff_day, charge_date)
            confirmed_start, confirmed_end = cycle.start, cycle.end
        else:
            confirmed_start, confirmed_end = period.start, period.end
        already_confirmed = Transaction.objects.filter(
            installment_plan=plan,
            transaction_type=Transaction.TransactionType.EXPENSE,
            date__gte=confirmed_start,
            date__lte=confirmed_end,
        ).exists()
        if already_confirmed:
            continue
        charges.append(
            ExpectedCharge(
                key=f"installment:{plan.id}:{period.start.isoformat()}",
                source_type="installment",
                source_id=plan.id,
                name=plan.name,
                merchant=plan.merchant,
                amount_cents=payment["amount_cents"],
                date=charge_date,
                period_start=period.start,
                period_end=period.end,
                category=plan.category,
                account=plan.account,
                payments_total=plan.installments_count,
                payment_number=payment["payment_number"],
                total_amount_cents=plan.total_amount_cents,
            )
        )

    return charges


def installment_payment_number_for_period(plan: InstallmentPlan, period: BudgetPeriod) -> int:
    # Plan con tarjeta: una mensualidad por estado de cuenta, numerada por offset de ciclos
    # desde el ciclo que contiene start_date. Como cutoff_day <= 28, el corte de cada ciclo
    # cae en el mismo mes calendario que el fin de ese mes, así que la misma aritmética por
    # year/month de period.end sirve tanto para meses calendario como para ciclos de tarjeta.
    account = plan.account
    if account is not None and account.account_type == Account.AccountType.CREDIT_CARD:
        anchor_end = card_cycle(account.cutoff_day, plan.start_date).end
    else:
        anchor_end = month_period(plan.start_date).end
    month_offset = (period.end.year - anchor_end.year) * 12 + period.end.month - anchor_end.month
    return plan.first_payment_number + month_offset


def installment_charge_for_period(plan: InstallmentPlan, period: BudgetPeriod) -> dict | None:
    if not plan.is_active:
        return None

    payment_number = installment_payment_number_for_period(plan, period)
    # Los pagos anteriores a first_payment_number ocurrieron antes de start_date (plan
    # heredado) y por definicion no se rastrean: no generan mensualidad fantasma.
    if payment_number < plan.first_payment_number or payment_number > plan.installments_count:
        return None

    amount = plan.payment_amount_cents(payment_number)
    if amount <= 0:
        return None
    remaining_after_period = max(plan.installments_count - payment_number, 0)
    return {
        "payment_number": payment_number,
        "payments_total": plan.installments_count,
        "amount_cents": amount,
        "remaining_payments": remaining_after_period,
    }


def _projection_plan_account_payload(plan: InstallmentPlan) -> dict | None:
    if plan.account is None:
        return None
    return {
        "id": plan.account.id,
        "name": plan.account.name,
        "account_type": plan.account.account_type,
        "color": plan.account.color,
    }


def _projection_plan_owner_payload(plan: InstallmentPlan) -> dict | None:
    if plan.account is None or plan.account.owner is None:
        return None
    owner = plan.account.owner
    return {"id": owner.id, "name": owner.name, "color": owner.color}


def installment_projection(value: date | None = None, months_ahead: int = 6, account_id: int | None = None) -> dict:
    """Proyección MSI. Modo mes (default): columnas por mes calendario, cada mensualidad de un
    plan con tarjeta asignada al mes de su corte. Modo ciclo (?account= tarjeta de crédito):
    columnas por los ciclos reales de esa tarjeta."""
    value = value or app_localdate()
    account = (
        Account.objects.filter(pk=account_id).select_related("owner").first() if account_id is not None else None
    )
    cycle_mode = account is not None and account.account_type == Account.AccountType.CREDIT_CARD

    if cycle_mode:
        columns = [card_cycle_for_offset(account.cutoff_day, value, offset) for offset in range(months_ahead + 1)]
        column_keys = [column.end.isoformat() for column in columns]
    else:
        columns = project_budget_periods(value, months_ahead)
        column_keys = [f"{column.start.year}-{column.start.month:02d}" for column in columns]

    plans_queryset = InstallmentPlan.objects.filter(
        is_active=True,
        start_date__lte=columns[-1].end,
        # Cota amplia segura: primer día del mes anterior al inicio de la primera columna.
        # columns[0].start puede ser día 29 (corte 28 tras febrero) y add_months directo
        # sobre esa fecha revienta en años no bisiestos; la precisión la da payment_number.
        end_date__gte=add_months(month_start(columns[0].start), -1),
    ).select_related("category", "category__member", "account", "account__owner")
    if account is not None:
        plans_queryset = plans_queryset.filter(account_id=account.id)
    plans = list(plans_queryset)

    period_rows = []
    totals_by_key: dict[str, int] = {}

    for column, column_key in zip(columns, column_keys):
        total = 0
        plan_rows = []
        cards_map: dict[int | None, dict] = {}
        for plan in plans:
            payment = installment_charge_for_period(plan, column)
            if payment is None:
                continue
            total += payment["amount_cents"]
            plan_account_id = None if plan.account is None else plan.account.id
            card_bucket = cards_map.setdefault(
                plan_account_id,
                {
                    "account_id": plan_account_id,
                    "account_name": None if plan.account is None else plan.account.name,
                    "total_cents": 0,
                },
            )
            card_bucket["total_cents"] += payment["amount_cents"]
            member = plan.category.member
            plan_rows.append(
                {
                    "id": plan.id,
                    "name": plan.name,
                    "merchant": plan.merchant,
                    "amount_cents": payment["amount_cents"],
                    "payment_number": payment["payment_number"],
                    "payments_total": payment["payments_total"],
                    "remaining_payments": payment["remaining_payments"],
                    "total_amount_cents": plan.total_amount_cents,
                    "round_up_monthly_payment": plan.round_up_monthly_payment,
                    "category": {
                        "id": plan.category.id,
                        "name": plan.category.name,
                        "scope": plan.category.scope,
                        "budget_treatment": plan.category.budget_treatment,
                        "color": plan.category.color,
                        "icon": plan.category.icon,
                    },
                    "member": None if member is None else {"id": member.id, "name": member.name, "color": member.color},
                    "account": _projection_plan_account_payload(plan),
                    "owner": _projection_plan_owner_payload(plan),
                }
            )
        totals_by_key[column_key] = total
        period_rows.append(
            {
                "key": column_key,
                "start": column.start,
                "end": column.end,
                "label": f"{column.start.isoformat()} / {column.end.isoformat()}",
                "total_cents": total,
                "cards": list(cards_map.values()),
                "plans": plan_rows,
            }
        )

    current_key = column_keys[0]
    active_plan_rows = []
    for plan in plans:
        current_payment = installment_charge_for_period(plan, columns[0])
        future_total = 0
        monthly_amounts = []
        for column in columns:
            payment = installment_charge_for_period(plan, column)
            amount = payment["amount_cents"] if payment else 0
            monthly_amounts.append({"period_end": column.end, "amount_cents": amount})
            future_total += amount
        member = plan.category.member
        active_plan_rows.append(
            {
                "id": plan.id,
                "name": plan.name,
                "merchant": plan.merchant,
                "total_amount_cents": plan.total_amount_cents,
                "round_up_monthly_payment": plan.round_up_monthly_payment,
                "current_amount_cents": current_payment["amount_cents"] if current_payment else 0,
                "current_payment_number": current_payment["payment_number"] if current_payment else None,
                "payments_total": plan.installments_count,
                "remaining_payments": current_payment["remaining_payments"] if current_payment else 0,
                "projected_total_cents": future_total,
                "monthly_amounts": monthly_amounts,
                "category": {
                    "id": plan.category.id,
                    "name": plan.category.name,
                    "scope": plan.category.scope,
                    "budget_treatment": plan.category.budget_treatment,
                    "color": plan.category.color,
                    "icon": plan.category.icon,
                },
                "member": None if member is None else {"id": member.id, "name": member.name, "color": member.color},
                "account": _projection_plan_account_payload(plan),
                "owner": _projection_plan_owner_payload(plan),
            }
        )

    account_payload = None
    if account is not None:
        owner = account.owner
        account_payload = {
            "id": account.id,
            "name": account.name,
            "color": account.color,
            "cutoff_day": account.cutoff_day,
            "payment_due_day": account.payment_due_day,
            "owner": None if owner is None else {"id": owner.id, "name": owner.name, "color": owner.color},
        }

    return {
        "mode": "cycle" if cycle_mode else "month",
        "account": account_payload,
        "current_period_key": current_key,
        "current_total_cents": totals_by_key[current_key],
        "periods": period_rows,
        "plans": active_plan_rows,
    }


def _card_cycle_block(card: Account, cycle: BudgetPeriod) -> dict:
    # SPEND_TYPES: los expected_charge en tarjeta consumen la ventana viva, asi que
    # Pagos debe cobrarlos al corte igual que la ventana los libera.
    purchase_cents = (
        Transaction.objects.filter(
            transaction_type__in=SPEND_TYPES,
            account_id=card.id,
            installment_plan__isnull=True,
            date__gte=cycle.start,
            date__lte=cycle.end,
        )
        .exclude(category__budget_treatment=Category.BudgetTreatment.TRACKING_ONLY)
        .aggregate(total=Sum("amount_cents"))["total"]
        or 0
    )
    installment_cents = 0
    plans = InstallmentPlan.objects.filter(
        is_active=True,
        account_id=card.id,
        start_date__lte=cycle.end,
        # Cota amplia segura (cycle.start puede ser día 29 con corte 28 tras febrero).
        end_date__gte=add_months(month_start(cycle.start), -1),
    ).exclude(category__budget_treatment=Category.BudgetTreatment.TRACKING_ONLY)
    for plan in plans:
        payment = installment_charge_for_period(plan, cycle)
        if payment is None:
            continue
        installment_cents += payment["amount_cents"]
    payment_dates = card_payment_dates(cycle, card.payment_due_day) if card.payment_due_day is not None else None
    return {
        "start": cycle.start,
        "end": cycle.end,
        "payment_due_date": None if payment_dates is None else payment_dates.payment_due_date,
        "safe_payment_date": None if payment_dates is None else payment_dates.safe_payment_date,
        "purchase_cents": purchase_cents,
        "installment_cents": installment_cents,
        "total_cents": purchase_cents + installment_cents,
    }


def card_payments_summary(value: date | None = None) -> dict:
    """Estado de cuenta por tarjeta: ciclo cerrado (por pagar) y ciclo abierto (acumulando),
    con total global de por pagar y agrupación por titular."""
    value = value or app_localdate()
    cards = list(
        Account.objects.filter(account_type=Account.AccountType.CREDIT_CARD, is_active=True)
        .select_related("owner")
        .order_by("name")
    )

    rows = []
    total = 0
    owners: dict[int | None, dict] = {}
    for card in cards:
        closed = _card_cycle_block(card, last_closed_card_cycle(card.cutoff_day, value))
        open_cycle = _card_cycle_block(card, card_cycle(card.cutoff_day, value))
        total += closed["total_cents"]
        owner = card.owner
        owner_payload = None if owner is None else {"id": owner.id, "name": owner.name, "color": owner.color}
        bucket = owners.setdefault(
            None if owner is None else owner.id,
            {"member": owner_payload, "total_cents": 0, "account_ids": []},
        )
        bucket["total_cents"] += closed["total_cents"]
        bucket["account_ids"].append(card.id)
        rows.append(
            {
                "account_id": card.id,
                "account_name": card.name,
                "account_color": card.color,
                "owner": owner_payload,
                "closed_cycle": closed,
                "open_cycle": open_cycle,
            }
        )

    owners_list = sorted(owners.values(), key=lambda o: (o["member"] is None, (o["member"] or {}).get("name", "")))
    return {
        "total_cents": total,
        "as_of": value,
        "cards": rows,
        "owners": owners_list,
    }


def build_budget_summary(value: date | None = None, scope: str = "family", member_id: int | None = None):
    period = get_budget_period(value)
    ensure_allocations(period)
    normalized_scope = "family" if scope == "global" else scope
    categories = list(categories_for_scope(normalized_scope, member_id).select_related("member"))
    sync_closed_overspend_records(categories, period)
    as_of = resolve_as_of(period)
    category_ids = [category.id for category in categories]
    allocations = {
        allocation.category_id: allocation.amount_cents
        for allocation in BudgetAllocation.objects.filter(
            category_id__in=category_ids,
            period_start=period.start,
            period_end=period.end,
        )
    }

    # Flujo mensual: todo lo gastado en el mes calendario completo, sin importar ventanas.
    # Puede ser menor que el consumo vivo cuando gasto de tarjeta del mes anterior cruza al mes.
    monthly_flow_by_category = _spend_by_category(category_ids, period.start, period.end)
    # Ventana de mes: gasto cash/debito/banco del mes hasta as_of.
    month_spent_by_category = _spend_by_category(category_ids, period.start, as_of, exclude_credit_card=True)

    # Ventana por tarjeta: gasto del ciclo abierto de cada tarjeta hasta as_of.
    # date <= as_of ya recorta la foto de cierre (as_of <= cycle.end por construccion);
    # no hace falta clamp adicional contra cycle.end.
    cards = active_credit_cards()
    card_spend_rows_by_category: dict[int, list[tuple[Account, BudgetPeriod, int]]] = {}
    for card in cards:
        cycle = card_cycle(card.cutoff_day, as_of)
        for category_id, cents in _spend_by_category(category_ids, cycle.start, as_of, account_id=card.id).items():
            if cents > 0:
                card_spend_rows_by_category.setdefault(category_id, []).append((card, cycle, cents))

    pending_expected_by_category: dict[int, int] = {}
    for charge in expected_charges_for_period(period):
        if charge.category.id not in category_ids:
            continue
        pending_expected_by_category[charge.category.id] = (
            pending_expected_by_category.get(charge.category.id, 0) + charge.amount_cents
        )

    items = []
    overspend_history = overspend_history_for_categories(category_ids)
    totals = {
        "budget_cents": 0,
        "spent_cents": 0,
        "expected_cents": 0,
        "available_cents": 0,
        "real_available_cents": 0,
        "monthly_flow_cents": 0,
    }
    breakdown: dict[str, dict] = {}

    for category in categories:
        is_carryover = category.budget_behavior == Category.BudgetBehavior.CARRYOVER
        result = compute_live_budget(
            period=period,
            allocation_cents=allocations.get(category.id, category.monthly_budget_cents),
            month_spent_cents=month_spent_by_category.get(category.id, 0),
            card_spend_rows=card_spend_rows_by_category.get(category.id, []),
            expected_cents=pending_expected_by_category.get(category.id, 0),
            monthly_flow_cents=monthly_flow_by_category.get(category.id, 0),
            carryover_balance_cents=carryover_balance_for_period(category, period) if is_carryover else None,
        )
        budget = result.allocation_cents
        spent = result.spent_cents
        expected = result.expected_cents
        available = result.available_cents
        real_available = result.real_available_cents
        consumed = spent + expected
        percent_available = 0 if budget == 0 else round((available / budget) * 100, 2)
        member_payload = None
        if category.member:
            member_payload = {"id": category.member.id, "name": category.member.name, "color": category.member.color}
        history_payload = overspend_history.get(
            category.id,
            {
                "overspend_count": 0,
                "overspend_total_cents": 0,
                "last_overspend_cents": 0,
                "last_overspend_period_start": None,
                "last_overspend_period_end": None,
            },
        )

        items.append(
            {
                "category_id": category.id,
                "category_name": category.name,
                "scope": category.scope,
                "member": member_payload,
                "color": category.color,
                "icon": category.icon,
                "budget_treatment": category.budget_treatment,
                "budget_behavior": category.budget_behavior,
                "budget_cents": budget,
                "spent_cents": spent,
                "expected_cents": expected,
                "consumed_cents": consumed,
                "available_cents": available,
                "real_available_cents": real_available,
                "projected_available_cents": available,
                "monthly_flow_cents": result.monthly_flow_cents,
                "live_windows": [
                    {
                        "kind": window.kind,
                        "account_id": window.account_id,
                        "account_name": window.account_name,
                        "start": window.start,
                        "end": window.end,
                        "spent_cents": window.spent_cents,
                    }
                    for window in result.windows
                ],
                "carryover_real_balance_cents": result.carryover_balance_cents,
                "carryover_start_date": category.carryover_start_date,
                "percent_available": percent_available,
                "is_overspent": available < 0,
                **history_payload,
            }
        )
        totals["budget_cents"] += budget
        totals["spent_cents"] += spent
        totals["expected_cents"] += expected
        totals["available_cents"] += available
        totals["real_available_cents"] += real_available
        totals["monthly_flow_cents"] += result.monthly_flow_cents

        key = "family" if category.scope == Category.Scope.GLOBAL else f"member:{category.member_id}"
        label = "Familia" if category.scope == Category.Scope.GLOBAL else category.member.name
        color = "#0f766e" if category.scope == Category.Scope.GLOBAL else category.member.color
        bucket = breakdown.setdefault(
            key,
            {
                "key": key,
                "label": label,
                "color": color,
                "budget_cents": 0,
                "spent_cents": 0,
                "expected_cents": 0,
                "available_cents": 0,
                "real_available_cents": 0,
                "monthly_flow_cents": 0,
            },
        )
        bucket["budget_cents"] += budget
        bucket["spent_cents"] += spent
        bucket["expected_cents"] += expected
        bucket["available_cents"] += available
        bucket["real_available_cents"] += real_available
        bucket["monthly_flow_cents"] += result.monthly_flow_cents

    return {
        "period": {"start": period.start, "end": period.end},
        "scope": normalized_scope,
        "member_id": member_id,
        "totals": totals,
        "breakdown": list(breakdown.values()),
        "categories": items,
    }


def build_off_budget_summary(value: date | None = None) -> dict:
    period = get_budget_period(value)
    categories = list(
        Category.objects.filter(
            is_active=True,
            budget_treatment=Category.BudgetTreatment.TRACKING_ONLY,
        ).select_related("member")
    )
    category_ids = [category.id for category in categories]

    spent_rows = (
        Transaction.objects.filter(
            transaction_type__in=[Transaction.TransactionType.EXPENSE, Transaction.TransactionType.EXPECTED_CHARGE],
            category_id__in=category_ids,
            date__gte=period.start,
            date__lte=period.end,
        )
        .values("category_id")
        .annotate(total=Sum("amount_cents"))
    )
    spent_by_category = {row["category_id"]: row["total"] or 0 for row in spent_rows}

    expected_charges = [
        charge for charge in expected_charges_for_period(period) if charge.category.id in category_ids
    ]
    expected_by_category: dict[int, int] = {}
    expected_payload = []
    for charge in expected_charges:
        expected_by_category[charge.category.id] = expected_by_category.get(charge.category.id, 0) + charge.amount_cents
        member = charge.category.member
        expected_payload.append(
            {
                "key": charge.key,
                "source_type": charge.source_type,
                "source_id": charge.source_id,
                "name": charge.name,
                "merchant": charge.merchant,
                "amount_cents": charge.amount_cents,
                "date": charge.date,
                "period_start": charge.period_start,
                "period_end": charge.period_end,
                "category": {
                    "id": charge.category.id,
                    "name": charge.category.name,
                    "scope": charge.category.scope,
                    "budget_treatment": charge.category.budget_treatment,
                    "color": charge.category.color,
                    "icon": charge.category.icon,
                },
                "member": None if member is None else {"id": member.id, "name": member.name, "color": member.color},
                "account": None if charge.account is None else {"id": charge.account.id, "name": charge.account.name},
                "payment_number": charge.payment_number,
                "payments_total": charge.payments_total,
                "total_amount_cents": charge.total_amount_cents,
            }
        )

    items = []
    totals = {"spent_cents": 0, "expected_cents": 0, "total_cents": 0}
    for category in categories:
        spent = spent_by_category.get(category.id, 0)
        expected = expected_by_category.get(category.id, 0)
        total = spent + expected
        if total == 0:
            continue
        member_payload = None
        if category.member:
            member_payload = {"id": category.member.id, "name": category.member.name, "color": category.member.color}
        items.append(
            {
                "category_id": category.id,
                "category_name": category.name,
                "scope": category.scope,
                "member": member_payload,
                "color": category.color,
                "icon": category.icon,
                "budget_treatment": category.budget_treatment,
                "spent_cents": spent,
                "expected_cents": expected,
                "total_cents": total,
            }
        )
        totals["spent_cents"] += spent
        totals["expected_cents"] += expected
        totals["total_cents"] += total

    return {
        "period": {"start": period.start, "end": period.end},
        "totals": totals,
        "categories": items,
        "expected_charges": expected_payload,
    }


def account_balance(account: Account) -> int:
    income = (
        Transaction.objects.filter(
            transaction_type=Transaction.TransactionType.INCOME,
            destination_account=account,
        ).aggregate(total=Sum("amount_cents"))["total"]
        or 0
    )
    expenses = (
        Transaction.objects.filter(
            transaction_type__in=[Transaction.TransactionType.EXPENSE, Transaction.TransactionType.EXPECTED_CHARGE],
            account=account,
        )
        .exclude(category__budget_treatment=Category.BudgetTreatment.TRACKING_ONLY)
        .aggregate(total=Sum("amount_cents"))["total"]
        or 0
    )
    transfers_out = (
        Transaction.objects.filter(
            transaction_type=Transaction.TransactionType.TRANSFER,
            account=account,
        ).aggregate(total=Sum("amount_cents"))["total"]
        or 0
    )
    transfers_in = (
        Transaction.objects.filter(
            transaction_type=Transaction.TransactionType.TRANSFER,
            destination_account=account,
        ).aggregate(total=Sum("amount_cents"))["total"]
        or 0
    )
    return account.initial_balance_cents + income + transfers_in - expenses - transfers_out


def _confirmation_period(source_type: str, source_id: int, charge_date: date) -> BudgetPeriod:
    # Un MSI con tarjeta confirmado con fecha dentro del ciclo puede caer en otro mes
    # calendario que el del corte; se busca el cargo en el mes del corte de su ciclo.
    if source_type == "installment":
        plan = InstallmentPlan.objects.filter(pk=source_id).select_related("account").first()
        if plan and plan.account and plan.account.account_type == Account.AccountType.CREDIT_CARD:
            return month_period(card_cycle(plan.account.cutoff_day, charge_date).end)
    return get_budget_period(charge_date)


def confirm_expected_charge(source_type: str, source_id: int, charge_date: date, account: Account | None, user):
    period = _confirmation_period(source_type, source_id, charge_date)
    charge = next(
        (
            candidate
            for candidate in expected_charges_for_period(period)
            if candidate.source_type == source_type and candidate.source_id == source_id
        ),
        None,
    )
    if charge is None:
        raise ValueError("No se encontro un cargo esperado pendiente para ese periodo.")

    transaction = Transaction(
        transaction_type=Transaction.TransactionType.EXPENSE,
        merchant=charge.merchant,
        amount_cents=charge.amount_cents,
        date=charge_date,
        account=account,
        category=charge.category,
        note=f"Confirmado desde compromiso: {charge.name}",
        created_by=user,
    )
    if source_type == "recurring":
        transaction.recurring_expense_id = source_id
    if source_type == "installment":
        transaction.installment_plan_id = source_id
    transaction.save()
    return transaction


def auto_post_due_recurring_charges(as_of: date | None = None, user=None) -> list[Transaction]:
    as_of = as_of or app_localdate()
    created: list[Transaction] = []
    recurring_queryset = RecurringExpense.objects.filter(
        auto_charge=True,
        is_active=True,
        account__isnull=False,
        start_date__lte=as_of,
    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=as_of.replace(day=1)))

    with db_transaction.atomic():
        for recurring in recurring_queryset.select_related("category", "account"):
            for charge_date in charge_dates_for_recurring_expense(recurring, as_of, earliest=month_start(as_of)):
                period = get_budget_period(charge_date)
                already_posted = Transaction.objects.filter(
                    recurring_expense=recurring,
                    transaction_type=Transaction.TransactionType.EXPENSE,
                    date__gte=period.start,
                    date__lte=period.end,
                ).exists()
                if already_posted:
                    continue
                item = Transaction(
                    transaction_type=Transaction.TransactionType.EXPENSE,
                    merchant=recurring.merchant,
                    amount_cents=recurring.amount_cents,
                    date=charge_date,
                    account=recurring.account,
                    category=recurring.category,
                    note=f"Cargo automatico: {recurring.name}",
                    created_by=user if getattr(user, "is_authenticated", False) else None,
                    recurring_expense=recurring,
                )
                item.save()
                created.append(item)
    return created
