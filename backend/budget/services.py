from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.db.models import Q, Sum
from django.utils import timezone

from .models import (
    Account,
    AppSettings,
    BudgetAllocation,
    Category,
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


def ensure_allocations(period: BudgetPeriod) -> None:
    for category in Category.objects.filter(is_active=True):
        BudgetAllocation.objects.get_or_create(
            category=category,
            period_start=period.start,
            period_end=period.end,
            defaults={"amount_cents": category.monthly_budget_cents},
        )


def categories_for_scope(scope: str, member_id: int | None = None):
    queryset = Category.objects.filter(is_active=True)
    if scope in ["family", "global"]:
        return queryset.filter(scope=Category.Scope.GLOBAL)
    if scope == "member":
        return queryset.filter(scope=Category.Scope.PERSONAL, member_id=member_id)
    if scope == "total":
        return queryset
    return queryset


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
        first_period = get_budget_period(plan.start_date)
        payment_number = (period.end.year - first_period.end.year) * 12 + period.end.month - first_period.end.month + 1
        base_amount = plan.total_amount_cents // plan.installments_count
        remainder = plan.total_amount_cents % plan.installments_count
        amount = base_amount + (remainder if payment_number == plan.installments_count else 0)
        charge_date = max(period.start, plan.start_date)
        charges.append(
            ExpectedCharge(
                key=f"installment:{plan.id}:{period.start.isoformat()}",
                source_type="installment",
                source_id=plan.id,
                name=plan.name,
                amount_cents=amount,
                date=charge_date,
                period_start=period.start,
                period_end=period.end,
                category=plan.category,
                account=plan.account,
                payments_total=plan.installments_count,
                payment_number=payment_number,
                total_amount_cents=plan.total_amount_cents,
            )
        )

    return charges


def installment_charge_for_period(plan: InstallmentPlan, period: BudgetPeriod) -> dict | None:
    if not plan.is_active or plan.start_date > period.end or plan.end_date < period.start:
        return None

    first_period = get_budget_period(plan.start_date)
    payment_number = (period.end.year - first_period.end.year) * 12 + period.end.month - first_period.end.month + 1
    if payment_number < 1 or payment_number > plan.installments_count:
        return None

    base_amount = plan.total_amount_cents // plan.installments_count
    remainder = plan.total_amount_cents % plan.installments_count
    amount = base_amount + (remainder if payment_number == plan.installments_count else 0)
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
                    "amount_cents": payment["amount_cents"],
                    "payment_number": payment["payment_number"],
                    "payments_total": payment["payments_total"],
                    "remaining_payments": payment["remaining_payments"],
                    "total_amount_cents": plan.total_amount_cents,
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
                "total_amount_cents": plan.total_amount_cents,
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
    totals = {"budget_cents": 0, "spent_cents": 0, "expected_cents": 0, "available_cents": 0}
    breakdown: dict[str, dict] = {}

    for category in categories:
        budget = allocations.get(category.id, category.monthly_budget_cents)
        spent = spent_by_category.get(category.id, 0)
        expected = pending_expected_by_category.get(category.id, 0)
        consumed = spent + expected
        available = budget - consumed
        percent_available = 0 if budget == 0 else round((available / budget) * 100, 2)
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
                "budget_cents": budget,
                "spent_cents": spent,
                "expected_cents": expected,
                "consumed_cents": consumed,
                "available_cents": available,
                "percent_available": percent_available,
                "is_overspent": available < 0,
            }
        )
        totals["budget_cents"] += budget
        totals["spent_cents"] += spent
        totals["expected_cents"] += expected
        totals["available_cents"] += available

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
            },
        )
        bucket["budget_cents"] += budget
        bucket["spent_cents"] += spent
        bucket["expected_cents"] += expected
        bucket["available_cents"] += available

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
        merchant=charge.name,
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
