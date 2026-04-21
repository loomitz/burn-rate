from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F
from django.utils import timezone


def default_invitation_expiry():
    return timezone.now() + timedelta(days=getattr(settings, "INVITATION_TTL_DAYS", 14))


def hash_invitation_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_merchant_concept_name(value: str) -> str:
    return " ".join(value.strip().split())


def merchant_concept_lookup_key(value: str) -> str:
    return normalize_merchant_concept_name(value).casefold()


class AppSettings(models.Model):
    currency = models.CharField(max_length=3, default="MXN")
    cutoff_day = models.PositiveSmallIntegerField(
        default=20,
        validators=[MinValueValidator(1), MaxValueValidator(28)],
    )

    class Meta:
        verbose_name = "app settings"
        verbose_name_plural = "app settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "AppSettings":
        settings_obj, _ = cls.objects.get_or_create(pk=1)
        return settings_obj

    def __str__(self) -> str:
        return f"{self.currency}, corte {self.cutoff_day}"


class HouseholdMember(models.Model):
    name = models.CharField(max_length=120, unique=True)
    color = models.CharField(max_length=7, default="#2563eb")
    is_active = models.BooleanField(default=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="budget_profiles",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Category(models.Model):
    class Scope(models.TextChoices):
        GLOBAL = "global", "Global"
        PERSONAL = "personal", "Personal"

    name = models.CharField(max_length=140)
    color = models.CharField(max_length=7, default="#0f766e")
    icon = models.CharField(max_length=40, default="tag")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    scope = models.CharField(max_length=16, choices=Scope.choices, default=Scope.GLOBAL)
    member = models.ForeignKey(
        HouseholdMember,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    monthly_budget_cents = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scope", "member__name", "order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=models.Q(scope="global"),
                name="unique_global_category_name",
            ),
            models.UniqueConstraint(
                fields=["name", "member"],
                condition=models.Q(scope="personal"),
                name="unique_personal_category_name",
            )
        ]

    def clean(self) -> None:
        if self.scope == self.Scope.PERSONAL and self.member_id is None:
            raise ValidationError({"member": "Las categorias personales requieren una persona."})
        if self.scope == self.Scope.GLOBAL and self.member_id is not None:
            raise ValidationError({"member": "Las categorias globales no deben tener persona."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        if self.scope == self.Scope.PERSONAL and self.member:
            return f"{self.name} - {self.member.name}"
        return self.name


class BudgetAllocation(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="allocations")
    period_start = models.DateField()
    period_end = models.DateField()
    amount_cents = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["period_start", "category__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "period_start", "period_end"],
                name="unique_budget_allocation_period",
            )
        ]

    def __str__(self) -> str:
        return f"{self.category}: {self.amount_cents} ({self.period_start} - {self.period_end})"


class Account(models.Model):
    class AccountType(models.TextChoices):
        CASH = "cash", "Efectivo"
        BANK = "bank", "Banco"
        DEBIT_CARD = "debit_card", "Tarjeta de debito"
        CREDIT_CARD = "credit_card", "Tarjeta de credito"

    name = models.CharField(max_length=140, unique=True)
    account_type = models.CharField(max_length=24, choices=AccountType.choices)
    color = models.CharField(max_length=7, default="#475569")
    initial_balance_cents = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def clean(self) -> None:
        if self.account_type != self.AccountType.CASH and self.initial_balance_cents != 0:
            raise ValidationError({"initial_balance_cents": "Solo las cuentas de efectivo pueden tener saldo inicial."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class MerchantConcept(models.Model):
    name = models.CharField(max_length=160)
    normalized_name = models.CharField(max_length=160, unique=True, db_index=True)
    usage_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-usage_count", "name"]

    def clean(self) -> None:
        self.name = normalize_merchant_concept_name(self.name)
        self.normalized_name = merchant_concept_lookup_key(self.name)
        if not self.name:
            raise ValidationError({"name": "Escribe un comercio o concepto."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @classmethod
    def record(cls, name: str) -> "MerchantConcept | None":
        clean_name = normalize_merchant_concept_name(name)
        if not clean_name:
            return None
        concept, _ = cls.objects.get_or_create(
            normalized_name=merchant_concept_lookup_key(clean_name),
            defaults={"name": clean_name},
        )
        cls.objects.filter(pk=concept.pk).update(usage_count=F("usage_count") + 1, last_used_at=timezone.now())
        concept.refresh_from_db()
        return concept

    def __str__(self) -> str:
        return self.name


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        EXPENSE = "expense", "Gasto"
        INCOME = "income", "Ingreso"
        TRANSFER = "transfer", "Transferencia"
        EXPECTED_CHARGE = "expected_charge", "Cargo esperado"

    transaction_type = models.CharField(max_length=24, choices=TransactionType.choices)
    merchant = models.CharField(max_length=160, blank=True)
    amount_cents = models.PositiveIntegerField()
    date = models.DateField()
    account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="outgoing_transactions",
    )
    destination_account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    member = models.ForeignKey(
        HouseholdMember,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_transactions",
    )
    recurring_expense = models.ForeignKey(
        "RecurringExpense",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transactions",
    )
    installment_plan = models.ForeignKey(
        "InstallmentPlan",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def clean(self) -> None:
        if self.amount_cents <= 0:
            raise ValidationError({"amount_cents": "El monto debe ser positivo."})
        if self.transaction_type in [self.TransactionType.EXPENSE, self.TransactionType.EXPECTED_CHARGE]:
            if not self.merchant:
                raise ValidationError({"merchant": "Los gastos requieren comercio o nombre."})
            if self.category_id is None:
                raise ValidationError({"category": "Los gastos requieren categoria."})
            if self.account_id is None:
                raise ValidationError({"account": "Los gastos requieren cuenta o medio de pago."})
        if self.transaction_type == self.TransactionType.TRANSFER:
            if self.account_id is None or self.destination_account_id is None:
                raise ValidationError({"destination_account": "Las transferencias requieren origen y destino."})
            if self.account_id == self.destination_account_id:
                raise ValidationError({"destination_account": "Origen y destino deben ser distintos."})

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        self.merchant = normalize_merchant_concept_name(self.merchant)
        if self.category and self.category.scope == Category.Scope.PERSONAL:
            self.member = self.category.member
        elif self.category and self.category.scope == Category.Scope.GLOBAL:
            self.member = None
        self.full_clean()
        result = super().save(*args, **kwargs)
        if is_new and self.transaction_type == self.TransactionType.EXPENSE:
            MerchantConcept.record(self.merchant)
        return result

    def __str__(self) -> str:
        label = self.merchant or self.get_transaction_type_display()
        return f"{label} {self.amount_cents} on {self.date}"


class RecurringExpense(models.Model):
    name = models.CharField(max_length=160)
    amount_cents = models.PositiveIntegerField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="recurring_expenses")
    account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="recurring_expenses",
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    charge_day = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(28)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    @property
    def member(self) -> HouseholdMember | None:
        return self.category.member if self.category.scope == Category.Scope.PERSONAL else None

    def clean(self) -> None:
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "La fecha final no puede ser anterior al inicio."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class InstallmentPlan(models.Model):
    name = models.CharField(max_length=160)
    total_amount_cents = models.PositiveIntegerField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="installment_plans")
    account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="installment_plans",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    installments_count = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    @property
    def member(self) -> HouseholdMember | None:
        return self.category.member if self.category.scope == Category.Scope.PERSONAL else None

    @property
    def monthly_amount_cents(self) -> int:
        return self.total_amount_cents // self.installments_count

    def clean(self) -> None:
        if self.end_date < self.start_date:
            raise ValidationError({"end_date": "La fecha final no puede ser anterior al inicio."})
        if self.installments_count < 1:
            raise ValidationError({"installments_count": "Debe existir al menos una mensualidad."})

    def save(self, *args, **kwargs):
        self.installments_count = count_calendar_months(self.start_date, self.end_date)
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class ExpectedChargeDismissal(models.Model):
    class SourceType(models.TextChoices):
        RECURRING = "recurring", "Recurrente"
        INSTALLMENT = "installment", "MSI"

    source_type = models.CharField(max_length=24, choices=SourceType.choices)
    source_id = models.PositiveIntegerField()
    period_start = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dismissed_expected_charges",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_type", "source_id", "period_start"],
                name="unique_expected_charge_dismissal",
            )
        ]


class Invitation(models.Model):
    email = models.EmailField(db_index=True)
    full_name = models.CharField(max_length=150, blank=True, default="")
    display_name = models.CharField(max_length=120, blank=True, default="")
    message = models.TextField(blank=True)
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    is_staff = models.BooleanField(default=False)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_budget_invitations",
    )
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="accepted_budget_invitations",
    )
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="revoked_budget_invitations",
    )
    expires_at = models.DateTimeField(default=default_invitation_expiry)
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self) -> None:
        self.email = self.email.strip().lower()
        self.full_name = " ".join(self.full_name.strip().split())
        self.display_name = " ".join(self.display_name.strip().split())
        self.message = self.message.strip()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @classmethod
    def issue(cls, **kwargs):
        token = secrets.token_urlsafe(32)
        invitation = cls(token_hash=hash_invitation_token(token), **kwargs)
        invitation.save()
        return invitation, token

    @classmethod
    def for_token(cls, token: str) -> "Invitation | None":
        token = token.strip()
        if not token:
            return None
        return cls.objects.filter(token_hash=hash_invitation_token(token)).first()

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def status(self) -> str:
        if self.accepted_at:
            return "accepted"
        if self.revoked_at:
            return "revoked"
        if self.is_expired:
            return "expired"
        return "pending"

    @property
    def is_pending(self) -> bool:
        return self.status == "pending"

    def mark_accepted(self, user) -> None:
        self.accepted_by = user
        self.accepted_at = timezone.now()
        self.save(update_fields=["accepted_by", "accepted_at", "updated_at"])

    def revoke(self, user) -> None:
        self.revoked_by = user
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_by", "revoked_at", "updated_at"])

    def __str__(self) -> str:
        return f"{self.email} ({self.status})"


def count_calendar_months(start, end) -> int:
    return (end.year - start.year) * 12 + end.month - start.month + 1
