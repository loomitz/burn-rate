from django.contrib import admin

from .models import (
    Account,
    AppSettings,
    BudgetAllocation,
    Category,
    ExpectedChargeDismissal,
    HouseholdMember,
    InstallmentPlan,
    MerchantConcept,
    RecurringExpense,
    Transaction,
)


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    list_display = ["currency", "cutoff_day"]


@admin.register(HouseholdMember)
class HouseholdMemberAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "user", "user_is_admin"]
    list_filter = ["is_active"]

    @admin.display(boolean=True)
    def user_is_admin(self, obj):
        return bool(obj.user and obj.user.is_staff)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "scope", "member", "monthly_budget_cents", "is_active"]
    list_filter = ["scope", "is_active"]


@admin.register(BudgetAllocation)
class BudgetAllocationAdmin(admin.ModelAdmin):
    list_display = ["category", "period_start", "period_end", "amount_cents"]
    list_filter = ["period_start"]


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["name", "account_type", "initial_balance_cents", "is_active"]
    list_filter = ["account_type", "is_active"]


@admin.register(MerchantConcept)
class MerchantConceptAdmin(admin.ModelAdmin):
    list_display = ["name", "usage_count", "last_used_at"]
    search_fields = ["name"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["date", "transaction_type", "merchant", "amount_cents", "category", "account", "member", "created_by"]
    list_filter = ["transaction_type", "date"]


@admin.register(RecurringExpense)
class RecurringExpenseAdmin(admin.ModelAdmin):
    list_display = ["name", "merchant", "amount_cents", "category", "start_date", "end_date", "is_active"]
    list_filter = ["is_active"]


@admin.register(InstallmentPlan)
class InstallmentPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "merchant", "total_amount_cents", "monthly_amount_cents", "first_payment_number", "installments_count", "category"]
    list_filter = ["is_active"]


@admin.register(ExpectedChargeDismissal)
class ExpectedChargeDismissalAdmin(admin.ModelAdmin):
    list_display = ["source_type", "source_id", "period_start", "created_by"]
