from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.db import transaction as db_transaction
from django.db.models import Q, Sum
from django.utils import timezone

from .models import (
    Account,
    AppSettings,
    BudgetAllocation,
    Category,
    CategoryBudgetChange,
    CategoryOverspendRecord,
    ExpectedChargeDismissal,
    InstallmentPlan,
    RecurringExpense,
    Transaction,
)


@dataclass(frozen=True)
class BudgetPeriod:
    start: date
    end: date


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


def get_budget_period(value: date | None = None, cutoff_day: int | None = None) -> BudgetPeriod:
    value = value or timezone.localdate()
    cutoff_day = cutoff_day or AppSettings.load().cutoff_day
    if not 1 <= cutoff_day <= 28:
        raise ValueError("cutoff_day must be between 1 and 28")

    if value.day <= cutoff_day:
        period_end = date(value.year, value.month, cutoff_day)
        previous_month_cutoff = add_months(period_end, -1)
        period_start = previous_month_cutoff.replace(day=cutoff_day + 1)
    else:
        period_start = date(value.year, value.month, cutoff_day + 1)
        period_end = add_months(date(value.year, value.month, cutoff_day), 1)
    return BudgetPeriod(start=period_start, end=period_end)


def project_budget_periods(value: date | None = None, months_ahead: int = 6) -> list[BudgetPeriod]:
    current_period = get_budget_period(value)
    return [get_budget_period(add_months(current_period.end, offset)) for offset in range(months_ahead + 1)]


def previous_budget_period(period: BudgetPeriod) -> BudgetPeriod:
    return get_budget_period(add_months(period.end, -1))


def period_key(period: BudgetPeriod) -> tuple[date, date]:
    return period.start, period.end


def iter_budget_periods(start_period: BudgetPeriod, end_period: BudgetPeriod):
    period = start_period
    while period_key(period) <= period_key(end_period):
        yield period
        period = get_budget_period(add_months(period.end, 1))


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
    for category in Category.objects.filter(is_active=True):
        ensure_category_allocation(category, period)


def record_category_budget_change(
    category: Category,
    amount_cents: int,
    effective_date: date,
    previous_amount_cents: int | None = None,
) -> CategoryBudgetChange:
    effective_period = get_budget_period(effective_date)
    current_period = get_budget_period(timezone.localdate())
    has_changes = CategoryBudgetChange.objects.filter(category=category).exists()

    if previous_amount_cents is not None and not has_changes and period_key(effective_period) > period_key(current_period):
        CategoryBudgetChange.objects.create(
            category=category,
            amount_cents=previous_amount_cents,
            effective_date=timezone.localdate(),
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
    BudgetAllocation.objects.filter(category=category, period_start__gte=effective_period.start).update(
        amount_cents=amount_cents
    )
    return change


def categories_for_scope(scope: str, member_id: int | None = None):
    queryset = Category.objects.filter(is_active=True)
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


def sync_monthly_overspend_record(category: Category, period: BudgetPeriod) -> None:
    if category.budget_behavior != Category.BudgetBehavior.MONTHLY_RESET:
        return
    tracking_period = get_budget_period(category.overspend_tracking_start_date)
    if period_key(period) < period_key(tracking_period) or period.end >= timezone.localdate():
        return

    budget = ensure_category_allocation(category, period).amount_cents
    spent = category_real_spend(category, period.start, period.end)
    overspend = max(spent - budget, 0)
    if overspend:
        CategoryOverspendRecord.objects.update_or_create(
            category=category,
            period_start=period.start,
            period_end=period.end,
            defaults={"budget_cents": budget, "spent_cents": spent, "overspend_cents": overspend},
        )
    else:
        CategoryOverspendRecord.objects.filter(
            category=category,
            period_start=period.start,
            period_end=period.end,
        ).delete()


def sync_closed_overspend_records(categories: list[Category], requested_period: BudgetPeriod) -> None:
    active_period = get_budget_period(timezone.localdate())
    last_closed_period = previous_budget_period(active_period)
    if period_key(requested_period) < period_key(last_closed_period):
        last_period = requested_period
    else:
        last_period = last_closed_period

    for category in categories:
        if category.budget_behavior != Category.BudgetBehavior.MONTHLY_RESET:
            continue
        tracking_period = get_budget_period(category.overspend_tracking_start_date)
        if period_key(tracking_period) > period_key(last_period):
            continue
        for period in iter_budget_periods(tracking_period, last_period):
            sync_monthly_overspend_record(category, period)


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


def expected_charges_for_period(period: BudgetPeriod):
    dismissals = set(
        ExpectedChargeDismissal.objects.filter(period_start=period.start).values_list("source_type", "source_id")
    )
    charges: list[ExpectedCharge] = []

    recurring_queryset = RecurringExpense.objects.filter(
        is_active=True,
        start_date__lte=period.end,
    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=period.start))

    for recurring in recurring_queryset.select_related("category", "category__member", "account"):
        if ("recurring", recurring.id) in dismissals:
            continue
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

    plans = InstallmentPlan.objects.filter(
        is_active=True,
        start_date__lte=period.end,
        end_date__gte=period.start,
    ).select_related("category", "category__member", "account")

    for plan in plans:
        if ("installment", plan.id) in dismissals:
            continue
        already_confirmed = Transaction.objects.filter(
            installment_plan=plan,
            transaction_type=Transaction.TransactionType.EXPENSE,
            date__gte=period.start,
            date__lte=period.end,
        ).exists()
        if already_confirmed:
            continue
        payment = installment_charge_for_period(plan, period)
        if payment is None:
            continue
        charge_date = max(period.start, plan.start_date)
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
    first_period = get_budget_period(plan.start_date)
    month_offset = (period.end.year - first_period.end.year) * 12 + period.end.month - first_period.end.month
    return plan.first_payment_number + month_offset


def installment_charge_for_period(plan: InstallmentPlan, period: BudgetPeriod) -> dict | None:
    if not plan.is_active or plan.start_date > period.end or plan.end_date < period.start:
        return None

    payment_number = installment_payment_number_for_period(plan, period)
    if payment_number < 1 or payment_number > plan.installments_count:
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


def installment_projection(value: date | None = None, months_ahead: int = 6) -> dict:
    periods = project_budget_periods(value, months_ahead)
    plans = list(
        InstallmentPlan.objects.filter(
            is_active=True,
            start_date__lte=periods[-1].end,
            end_date__gte=periods[0].start,
        ).select_related("category", "category__member", "account")
    )
    period_rows = []
    totals_by_period: dict[str, int] = {}

    for period in periods:
        period_key = period.end.isoformat()
        total = 0
        plan_rows = []
        for plan in plans:
            payment = installment_charge_for_period(plan, period)
            if payment is None:
                continue
            total += payment["amount_cents"]
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
                        "color": plan.category.color,
                        "icon": plan.category.icon,
                    },
                    "member": None if member is None else {"id": member.id, "name": member.name, "color": member.color},
                    "account": None if plan.account is None else {"id": plan.account.id, "name": plan.account.name},
                }
            )
        totals_by_period[period_key] = total
        period_rows.append(
            {
                "key": period_key,
                "start": period.start,
                "end": period.end,
                "label": f"{period.start.isoformat()} / {period.end.isoformat()}",
                "total_cents": total,
                "plans": plan_rows,
            }
        )

    current_key = periods[0].end.isoformat()
    active_plan_rows = []
    for plan in plans:
        current_payment = installment_charge_for_period(plan, periods[0])
        future_total = 0
        monthly_amounts = []
        for period in periods:
            payment = installment_charge_for_period(plan, period)
            amount = payment["amount_cents"] if payment else 0
            monthly_amounts.append({"period_end": period.end, "amount_cents": amount})
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
                    "color": plan.category.color,
                    "icon": plan.category.icon,
                },
                "member": None if member is None else {"id": member.id, "name": member.name, "color": member.color},
                "account": None if plan.account is None else {"id": plan.account.id, "name": plan.account.name},
            }
        )

    return {
        "current_period_key": current_key,
        "current_total_cents": totals_by_period[current_key],
        "periods": period_rows,
        "plans": active_plan_rows,
    }


def build_budget_summary(value: date | None = None, scope: str = "family", member_id: int | None = None):
    period = get_budget_period(value)
    ensure_allocations(period)
    normalized_scope = "family" if scope == "global" else scope
    categories = list(categories_for_scope(normalized_scope, member_id).select_related("member"))
    sync_closed_overspend_records(categories, period)
    category_ids = [category.id for category in categories]
    allocations = {
        allocation.category_id: allocation.amount_cents
        for allocation in BudgetAllocation.objects.filter(
            category_id__in=category_ids,
            period_start=period.start,
            period_end=period.end,
        )
    }

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
    }
    breakdown: dict[str, dict] = {}

    for category in categories:
        budget = allocations.get(category.id, category.monthly_budget_cents)
        spent = spent_by_category.get(category.id, 0)
        expected = pending_expected_by_category.get(category.id, 0)
        consumed = spent + expected
        if category.budget_behavior == Category.BudgetBehavior.CARRYOVER:
            real_available = carryover_balance_for_period(category, period)
        else:
            real_available = budget - spent
        available = real_available - expected
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
                "budget_behavior": category.budget_behavior,
                "budget_cents": budget,
                "spent_cents": spent,
                "expected_cents": expected,
                "consumed_cents": consumed,
                "available_cents": available,
                "real_available_cents": real_available,
                "projected_available_cents": available,
                "carryover_real_balance_cents": real_available
                if category.budget_behavior == Category.BudgetBehavior.CARRYOVER
                else None,
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
            },
        )
        bucket["budget_cents"] += budget
        bucket["spent_cents"] += spent
        bucket["expected_cents"] += expected
        bucket["available_cents"] += available
        bucket["real_available_cents"] += real_available

    return {
        "period": {"start": period.start, "end": period.end},
        "scope": normalized_scope,
        "member_id": member_id,
        "totals": totals,
        "breakdown": list(breakdown.values()),
        "categories": items,
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
        ).aggregate(total=Sum("amount_cents"))["total"]
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


def confirm_expected_charge(source_type: str, source_id: int, charge_date: date, account: Account, user):
    period = get_budget_period(charge_date)
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
    as_of = as_of or timezone.localdate()
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
