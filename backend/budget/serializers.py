from calendar import monthrange
from datetime import timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .auth_services import apply_user_names, normalize_email, normalize_name, unique_username_for_email
from .models import (
    Account,
    AppSettings,
    BudgetAllocation,
    Category,
    HouseholdMember,
    InstallmentPlan,
    Invitation,
    MerchantConcept,
    RecurringExpense,
    Transaction,
)
from .services import account_balance


def add_calendar_months(value, months: int):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "display_name",
            "is_staff",
            "is_superuser",
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.first_name or obj.username

    def get_display_name(self, obj):
        profile = obj.budget_profiles.order_by("created_at").first()
        if profile:
            return profile.name
        return obj.get_full_name() or obj.first_name or obj.username


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    username = serializers.CharField(required=False)
    password = serializers.CharField(trim_whitespace=False)

    def validate(self, attrs):
        identifier = normalize_email(attrs.get("email") or attrs.get("username") or "")
        user = None
        matched_user = User.objects.filter(email__iexact=identifier).first()
        if matched_user:
            user = authenticate(username=matched_user.username, password=attrs["password"])
        if user is None and attrs.get("username"):
            user = authenticate(username=attrs["username"], password=attrs["password"])
        if user is None:
            raise serializers.ValidationError("Email o password invalido.")
        if not user.is_active:
            raise serializers.ValidationError("El usuario esta inactivo.")
        attrs["user"] = user
        return attrs


def validate_user_password(password: str, *, email: str, full_name: str, username: str | None = None, user: User | None = None) -> None:
    user = user or User(username=username or email, email=email)
    user.email = email
    apply_user_names(user, full_name)
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc


class AppSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppSettings
        fields = ["currency", "cutoff_day"]


class BootstrapClaimSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=150)
    display_name = serializers.CharField(max_length=120)
    password = serializers.CharField(trim_whitespace=False, write_only=True)

    def validate(self, attrs):
        email = normalize_email(attrs["email"])
        full_name = normalize_name(attrs["full_name"])
        display_name = normalize_name(attrs["display_name"])
        attrs["email"] = email
        attrs["full_name"] = full_name
        attrs["display_name"] = display_name
        if not full_name:
            raise serializers.ValidationError({"full_name": "Escribe el nombre completo."})
        if not display_name:
            raise serializers.ValidationError({"display_name": "Escribe el nombre visible."})
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({"email": "Ya existe un usuario con ese email."})
        try:
            validate_user_password(attrs["password"], email=email, full_name=full_name)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({"password": exc.detail}) from exc
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        user = User(
            username=unique_username_for_email(self.validated_data["email"]),
            email=self.validated_data["email"],
            is_staff=True,
            is_superuser=True,
        )
        apply_user_names(user, self.validated_data["full_name"])
        user.set_password(self.validated_data["password"])
        user.save()
        member = HouseholdMember.objects.create(name=self.validated_data["display_name"], user=user)
        return user, member


class InvitationSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    is_admin = serializers.BooleanField(source="is_staff", read_only=True)
    invited_by_email = serializers.EmailField(source="invited_by.email", read_only=True)
    accepted_by_email = serializers.EmailField(source="accepted_by.email", read_only=True)
    revoked_by_email = serializers.EmailField(source="revoked_by.email", read_only=True)

    class Meta:
        model = Invitation
        fields = [
            "id",
            "email",
            "full_name",
            "display_name",
            "is_staff",
            "is_admin",
            "message",
            "status",
            "invited_by_email",
            "accepted_by_email",
            "revoked_by_email",
            "expires_at",
            "accepted_at",
            "revoked_at",
            "created_at",
        ]


class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    display_name = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    message = serializers.CharField(required=False, allow_blank=True)
    is_staff = serializers.BooleanField(required=False, default=False)
    is_admin = serializers.BooleanField(required=False, write_only=True)
    expires_at = serializers.DateTimeField(required=False)
    expires_in_days = serializers.IntegerField(required=False, min_value=1, max_value=90, write_only=True)

    def validate(self, attrs):
        email = normalize_email(attrs["email"])
        full_name = normalize_name(attrs.get("full_name", ""))
        display_name = normalize_name(attrs.get("display_name", ""))
        message = attrs.get("message", "").strip()
        now = timezone.now()
        expires_at = attrs.get("expires_at")
        expires_in_days = attrs.pop("expires_in_days", None)
        if expires_in_days:
            expires_at = now + timedelta(days=expires_in_days)
        if expires_at and expires_at <= now:
            raise serializers.ValidationError({"expires_at": "La invitacion debe vencer en el futuro."})
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({"email": "Ya existe un usuario con ese email."})
        pending_exists = Invitation.objects.filter(
            email__iexact=email,
            accepted_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=now,
        ).exists()
        if pending_exists:
            raise serializers.ValidationError({"email": "Ya existe una invitacion pendiente para ese email."})
        attrs["email"] = email
        attrs["full_name"] = full_name
        attrs["display_name"] = display_name
        attrs["message"] = message
        if "is_admin" in attrs:
            attrs["is_staff"] = attrs.pop("is_admin")
        if expires_at:
            attrs["expires_at"] = expires_at
        return attrs


class InvitationResolveSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    is_admin = serializers.BooleanField(source="is_staff", read_only=True)

    class Meta:
        model = Invitation
        fields = ["email", "full_name", "display_name", "is_staff", "is_admin", "message", "status", "expires_at", "accepted_at"]


class InvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField(trim_whitespace=False)
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=150)
    display_name = serializers.CharField(max_length=120)
    password = serializers.CharField(trim_whitespace=False, write_only=True)

    def validate(self, attrs):
        invitation = Invitation.for_token(attrs["token"])
        if invitation is None:
            raise serializers.ValidationError({"token": "La invitacion no existe."})
        if not invitation.is_pending:
            raise serializers.ValidationError({"token": "Esta invitacion ya no esta disponible."})

        email = normalize_email(attrs["email"])
        full_name = normalize_name(attrs["full_name"])
        display_name = normalize_name(attrs["display_name"])
        if email != invitation.email:
            raise serializers.ValidationError({"email": "El email no coincide con la invitacion."})
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({"email": "Ya existe un usuario con ese email."})
        if not full_name:
            raise serializers.ValidationError({"full_name": "Escribe el nombre completo."})
        if not display_name:
            raise serializers.ValidationError({"display_name": "Escribe el nombre visible."})
        linked_member = HouseholdMember.objects.filter(name__iexact=display_name, user__isnull=False).first()
        if linked_member:
            raise serializers.ValidationError({"display_name": "Ese nombre visible ya esta ligado a otro usuario."})
        try:
            validate_user_password(attrs["password"], email=email, full_name=full_name)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({"password": exc.detail}) from exc

        attrs["invitation"] = invitation
        attrs["email"] = email
        attrs["full_name"] = full_name
        attrs["display_name"] = display_name
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        invitation = Invitation.objects.select_for_update().get(pk=self.validated_data["invitation"].pk)
        if not invitation.is_pending:
            raise serializers.ValidationError({"token": "Esta invitacion ya no esta disponible."})

        member = HouseholdMember.objects.select_for_update().filter(name__iexact=self.validated_data["display_name"]).first()
        if member and member.user_id:
            raise serializers.ValidationError({"display_name": "Ese nombre visible ya esta ligado a otro usuario."})

        user = User(
            username=unique_username_for_email(self.validated_data["email"]),
            email=self.validated_data["email"],
            is_staff=invitation.is_staff,
            is_superuser=invitation.is_staff,
        )
        apply_user_names(user, self.validated_data["full_name"])
        user.set_password(self.validated_data["password"])
        user.save()
        if member:
            member.name = self.validated_data["display_name"]
            member.user = user
            member.is_active = True
            member.save(update_fields=["name", "user", "is_active"])
        else:
            member = HouseholdMember.objects.create(name=self.validated_data["display_name"], user=user)
        invitation.full_name = self.validated_data["full_name"]
        invitation.display_name = self.validated_data["display_name"]
        invitation.save(update_fields=["full_name", "display_name", "updated_at"])
        invitation.mark_accepted(user)
        return user, member, invitation


class HouseholdMemberSerializer(serializers.ModelSerializer):
    has_access = serializers.BooleanField(write_only=True, required=False)
    username = serializers.CharField(write_only=True, required=False, allow_blank=True)
    email = serializers.EmailField(write_only=True, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)
    is_admin = serializers.BooleanField(write_only=True, required=False, default=False)
    access_enabled = serializers.SerializerMethodField()
    user_username = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    user_is_admin = serializers.SerializerMethodField()

    class Meta:
        model = HouseholdMember
        fields = [
            "id",
            "name",
            "color",
            "is_active",
            "user",
            "has_access",
            "username",
            "email",
            "password",
            "is_admin",
            "access_enabled",
            "user_username",
            "user_email",
            "user_is_admin",
        ]
        read_only_fields = ["user"]

    def get_access_enabled(self, obj):
        return obj.user_id is not None

    def get_user_username(self, obj):
        return obj.user.username if obj.user else None

    def get_user_email(self, obj):
        return obj.user.email if obj.user else None

    def get_user_is_admin(self, obj):
        return bool(obj.user and obj.user.is_staff)

    def _matching_user(self, username: str = "", email: str = ""):
        user = None
        if username:
            user = User.objects.filter(username__iexact=username).first()
        if user is None and email:
            user = User.objects.filter(email__iexact=email).first()
        return user

    def _validate_reusable_user(self, user):
        if user is None:
            return
        linked_member = HouseholdMember.objects.filter(user=user)
        if self.instance is not None:
            linked_member = linked_member.exclude(pk=self.instance.pk)
        if linked_member.exists():
            raise serializers.ValidationError({"username": "Ese usuario ya esta ligado a otra persona."})

    def validate(self, attrs):
        is_admin = attrs.get("is_admin", False)
        has_access = True if is_admin else attrs.get("has_access")
        username = attrs.get("username", "").strip()
        email = normalize_email(attrs.get("email", ""))
        password = attrs.get("password", "")
        matched_user = self._matching_user(username, email)
        self._validate_reusable_user(matched_user)
        attrs["has_access"] = has_access
        attrs["username"] = username
        attrs["email"] = email
        if has_access:
            if not username and not getattr(self.instance, "user_id", None):
                raise serializers.ValidationError({"username": "Se requiere usuario cuando la persona tendra acceso."})
            needs_new_user = getattr(self.instance, "user_id", None) is None and matched_user is None
            if needs_new_user and not password:
                raise serializers.ValidationError({"password": "Se requiere contrasena al crear acceso."})
            if password:
                full_name = attrs.get("name", getattr(self.instance, "name", username))
                try:
                    validate_user_password(password, email=email or username, full_name=full_name, username=username)
                except serializers.ValidationError as exc:
                    raise serializers.ValidationError({"password": exc.detail}) from exc
        return attrs

    def _upsert_access_user(self, instance, payload):
        has_access = payload.pop("has_access", None)
        username = payload.pop("username", "").strip()
        email = normalize_email(payload.pop("email", ""))
        password = payload.pop("password", "")
        is_admin = payload.pop("is_admin", False)
        if is_admin:
            has_access = True

        if has_access is False:
            instance.user = None
            instance.save(update_fields=["user"])
            return instance

        if has_access:
            user = instance.user
            if user is None:
                user = self._matching_user(username, email) or User(username=username)
            elif username:
                user.username = username
            user.email = email
            apply_user_names(user, instance.name)
            user.is_staff = is_admin
            user.is_superuser = is_admin
            if password:
                user.set_password(password)
            user.save()
            instance.user = user
            instance.save(update_fields=["user"])
        return instance

    def create(self, validated_data):
        access_payload = {
            "has_access": validated_data.pop("has_access", False),
            "username": validated_data.pop("username", ""),
            "email": validated_data.pop("email", ""),
            "password": validated_data.pop("password", ""),
            "is_admin": validated_data.pop("is_admin", False),
        }
        instance = super().create(validated_data)
        return self._upsert_access_user(instance, access_payload)

    def update(self, instance, validated_data):
        access_payload = {
            "has_access": validated_data.pop("has_access", None),
            "username": validated_data.pop("username", ""),
            "email": validated_data.pop("email", ""),
            "password": validated_data.pop("password", ""),
            "is_admin": validated_data.pop("is_admin", False),
        }
        instance = super().update(instance, validated_data)
        return self._upsert_access_user(instance, access_payload)


class CategorySerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source="member.name", read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "color",
            "icon",
            "order",
            "is_active",
            "scope",
            "member",
            "member_name",
            "monthly_budget_cents",
        ]

    def validate(self, attrs):
        scope = attrs.get("scope", getattr(self.instance, "scope", Category.Scope.GLOBAL))
        member = attrs.get("member", getattr(self.instance, "member", None))
        if scope == Category.Scope.PERSONAL and member is None:
            raise serializers.ValidationError({"member": "Las categorias personales requieren una persona."})
        if scope == Category.Scope.GLOBAL and member is not None:
            raise serializers.ValidationError({"member": "Las categorias globales no deben tener persona."})
        return attrs


class BudgetAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetAllocation
        fields = ["id", "category", "period_start", "period_end", "amount_cents"]


class AccountSerializer(serializers.ModelSerializer):
    current_balance_cents = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            "id",
            "name",
            "account_type",
            "color",
            "initial_balance_cents",
            "current_balance_cents",
            "is_active",
        ]

    def get_current_balance_cents(self, obj):
        return account_balance(obj)

    def validate(self, attrs):
        account_type = attrs.get("account_type", getattr(self.instance, "account_type", None))
        initial_balance = attrs.get("initial_balance_cents", getattr(self.instance, "initial_balance_cents", 0))
        if account_type != Account.AccountType.CASH and initial_balance != 0:
            raise serializers.ValidationError(
                {"initial_balance_cents": "Solo las cuentas de efectivo pueden tener saldo inicial."}
            )
        return attrs


class MerchantConceptSerializer(serializers.ModelSerializer):
    class Meta:
        model = MerchantConcept
        fields = ["id", "name", "usage_count", "last_used_at", "created_at"]
        read_only_fields = fields


class TransactionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)
    destination_account_name = serializers.CharField(source="destination_account.name", read_only=True)
    member_name = serializers.CharField(source="member.name", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "transaction_type",
            "merchant",
            "amount_cents",
            "date",
            "account",
            "account_name",
            "destination_account",
            "destination_account_name",
            "category",
            "category_name",
            "member",
            "member_name",
            "note",
            "created_by",
            "created_by_username",
            "recurring_expense",
            "installment_plan",
            "created_at",
        ]
        read_only_fields = ["member", "created_by", "created_by_username", "created_at"]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

    def validate(self, attrs):
        transaction_type = attrs.get("transaction_type", getattr(self.instance, "transaction_type", None))
        account = attrs.get("account", getattr(self.instance, "account", None))
        destination = attrs.get("destination_account", getattr(self.instance, "destination_account", None))
        category = attrs.get("category", getattr(self.instance, "category", None))
        if transaction_type in [Transaction.TransactionType.EXPENSE, Transaction.TransactionType.EXPECTED_CHARGE]:
            if not attrs.get("merchant", getattr(self.instance, "merchant", "")):
                raise serializers.ValidationError({"merchant": "Los gastos requieren comercio o nombre."})
            if category is None:
                raise serializers.ValidationError({"category": "Los gastos requieren categoria."})
            if account is None:
                raise serializers.ValidationError({"account": "Los gastos requieren cuenta o medio de pago."})
        if transaction_type == Transaction.TransactionType.TRANSFER:
            if account is None or destination is None:
                raise serializers.ValidationError({"destination_account": "Las transferencias requieren origen y destino."})
            if account == destination:
                raise serializers.ValidationError({"destination_account": "Origen y destino deben ser distintos."})
        return attrs


class RecurringExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    member_name = serializers.CharField(source="category.member.name", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = RecurringExpense
        fields = [
            "id",
            "name",
            "merchant",
            "amount_cents",
            "category",
            "category_name",
            "member_name",
            "account",
            "account_name",
            "start_date",
            "end_date",
            "charge_day",
            "is_active",
        ]

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        merchant = attrs.get("merchant", getattr(self.instance, "merchant", ""))
        if not merchant.strip():
            raise serializers.ValidationError({"merchant": "Escribe el comercio del cargo mensual."})
        if end_date and start_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "La fecha final no puede ser anterior al inicio."})
        return attrs


class InstallmentPlanSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    member_name = serializers.CharField(source="category.member.name", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)
    monthly_amount_cents = serializers.IntegerField(read_only=True)
    end_date = serializers.DateField(required=False)
    months_count = serializers.IntegerField(write_only=True, min_value=1, required=False)

    class Meta:
        model = InstallmentPlan
        fields = [
            "id",
            "name",
            "merchant",
            "total_amount_cents",
            "monthly_amount_cents",
            "category",
            "category_name",
            "member_name",
            "account",
            "account_name",
            "start_date",
            "end_date",
            "months_count",
            "first_payment_number",
            "installments_count",
            "round_up_monthly_payment",
            "is_active",
        ]
        read_only_fields = ["installments_count"]

    def validate(self, attrs):
        months_count = attrs.pop("months_count", None)
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        first_payment_number = attrs.get("first_payment_number", getattr(self.instance, "first_payment_number", 1))
        total = attrs.get("total_amount_cents", getattr(self.instance, "total_amount_cents", None))
        merchant = attrs.get("merchant", getattr(self.instance, "merchant", ""))
        if months_count is not None:
            if start_date is None:
                raise serializers.ValidationError({"start_date": "Indica la fecha del primer pago."})
            attrs["end_date"] = add_calendar_months(start_date, months_count - 1)
            attrs["first_payment_number"] = 1
            end_date = attrs["end_date"]
        if not merchant.strip():
            raise serializers.ValidationError({"merchant": "Escribe el comercio de la compra a meses."})
        if start_date and not end_date:
            raise serializers.ValidationError({"months_count": "Indica la cantidad de meses de la compra."})
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "La fecha final no puede ser anterior al inicio."})
        if first_payment_number < 1:
            raise serializers.ValidationError({"first_payment_number": "El primer pago debe ser al menos 1."})
        if total is not None and total <= 0:
            raise serializers.ValidationError({"total_amount_cents": "El monto debe ser positivo."})
        return attrs
