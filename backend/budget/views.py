from datetime import date

from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, SAFE_METHODS, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth_services import build_invitation_accept_url, send_invitation_email
from .models import (
    Account,
    AppSettings,
    Category,
    ExpectedChargeDismissal,
    HouseholdMember,
    InstallmentPlan,
    Invitation,
    MerchantConcept,
    merchant_concept_lookup_key,
    RecurringExpense,
    Transaction,
)
from .serializers import (
    AccountSerializer,
    AppSettingsSerializer,
    BootstrapClaimSerializer,
    CategorySerializer,
    HouseholdMemberSerializer,
    InstallmentPlanSerializer,
    InvitationAcceptSerializer,
    InvitationCreateSerializer,
    InvitationResolveSerializer,
    InvitationSerializer,
    LoginSerializer,
    MerchantConceptSerializer,
    RecurringExpenseSerializer,
    TransactionSerializer,
    UserSerializer,
)
from .services import (
    build_budget_summary,
    confirm_expected_charge,
    expected_charges_for_period,
    get_budget_period,
    installment_projection,
)
from .setup_services import build_onboarding_status


class IsStaffForUnsafe(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class IsStaffUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


def bootstrap_needs_claim() -> bool:
    return not User.objects.exists()


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        login(request, serializer.validated_data["user"])
        return Response({"user": UserSerializer(serializer.validated_data["user"]).data})


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@ensure_csrf_cookie
@api_view(["GET"])
@permission_classes([AllowAny])
def csrf_view(request):
    return Response({"detail": "ok"})


class MeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response({"user": None})
        return Response({"user": UserSerializer(request.user).data})


@method_decorator(ensure_csrf_cookie, name="dispatch")
class AuthRefreshView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        request.session.modified = True
        return Response({"user": UserSerializer(request.user).data})

    def post(self, request):
        request.session.modified = True
        return Response({"user": UserSerializer(request.user).data})


class OnboardingStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(build_onboarding_status())


class BootstrapStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        needs_claim = bootstrap_needs_claim()
        return Response(
            {
                "needs_bootstrap": needs_claim,
                "can_claim": needs_claim,
                "has_users": not needs_claim,
                "staff_exists": not needs_claim,
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class BootstrapClaimView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        if not bootstrap_needs_claim():
            return Response({"detail": "Burn Rate ya tiene un administrador."}, status=status.HTTP_409_CONFLICT)
        serializer = BootstrapClaimSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not bootstrap_needs_claim():
            return Response({"detail": "Burn Rate ya tiene un administrador."}, status=status.HTTP_409_CONFLICT)
        user, member = serializer.save()
        login(request, user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "member": {"id": member.id, "name": member.name, "color": member.color},
            },
            status=status.HTTP_201_CREATED,
        )


class SettingsView(APIView):
    permission_classes = [IsAuthenticated, IsStaffForUnsafe]

    def get(self, request):
        return Response(AppSettingsSerializer(AppSettings.load()).data)

    def put(self, request):
        settings_obj = AppSettings.load()
        serializer = AppSettingsSerializer(settings_obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request):
        settings_obj = AppSettings.load()
        serializer = AppSettingsSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class InvitationViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Invitation.objects.select_related("invited_by", "accepted_by", "revoked_by").all()
    serializer_class = InvitationSerializer
    permission_classes = [IsAuthenticated, IsStaffUser]

    def create(self, request, *args, **kwargs):
        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation, token = Invitation.issue(invited_by=request.user, **serializer.validated_data)
        accept_url = build_invitation_accept_url(token, request=request)
        email_sent = send_invitation_email(invitation, token, accept_url)
        data = InvitationSerializer(invitation).data
        data.update({"token": token, "accept_url": accept_url, "email_sent": email_sent})
        return Response(data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        invitation = self.get_object()
        if invitation.accepted_at:
            return Response({"detail": "No se puede eliminar una invitacion aceptada."}, status=status.HTTP_400_BAD_REQUEST)
        invitation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        invitation = self.get_object()
        if invitation.accepted_at:
            return Response({"detail": "No se puede revocar una invitacion aceptada."}, status=status.HTTP_400_BAD_REQUEST)
        if not invitation.revoked_at:
            invitation.revoke(request.user)
        return Response(InvitationSerializer(invitation).data)


class InvitationResolveView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get("token", "")
        invitation = Invitation.for_token(token)
        if invitation is None:
            return Response({"detail": "La invitacion no existe."}, status=status.HTTP_404_NOT_FOUND)
        return Response(InvitationResolveSerializer(invitation).data)


@method_decorator(csrf_protect, name="dispatch")
class InvitationAcceptView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = InvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, member, invitation = serializer.save()
        login(request, user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "member": {"id": member.id, "name": member.name, "color": member.color},
                "invitation": InvitationResolveSerializer(invitation).data,
            },
            status=status.HTTP_201_CREATED,
        )


class HouseholdMemberViewSet(viewsets.ModelViewSet):
    queryset = HouseholdMember.objects.all()
    serializer_class = HouseholdMemberSerializer
    permission_classes = [IsAuthenticated, IsStaffForUnsafe]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.select_related("member").all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsStaffForUnsafe]

    def get_queryset(self):
        queryset = super().get_queryset()
        scope = self.request.query_params.get("scope")
        member_id = self.request.query_params.get("member")
        if scope:
            queryset = queryset.filter(scope=scope)
        if member_id:
            queryset = queryset.filter(member_id=member_id)
        return queryset


class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated, IsStaffForUnsafe]


class MerchantConceptViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MerchantConcept.objects.all()
    serializer_class = MerchantConceptSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get("search", "")
        if search:
            queryset = queryset.filter(normalized_name__contains=merchant_concept_lookup_key(search))
        return queryset


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.select_related("account", "destination_account", "category", "member", "created_by").all()
    serializer_class = TransactionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        if params.get("type"):
            queryset = queryset.filter(transaction_type=params["type"])
        if params.get("category"):
            queryset = queryset.filter(category_id=params["category"])
        if params.get("account"):
            queryset = queryset.filter(account_id=params["account"])
        if params.get("member"):
            queryset = queryset.filter(member_id=params["member"])
        if params.get("scope") == "global":
            queryset = queryset.filter(category__scope=Category.Scope.GLOBAL)
        if params.get("scope") == "personal":
            queryset = queryset.filter(category__scope=Category.Scope.PERSONAL)
        if params.get("period"):
            period_date = date.fromisoformat(f"{params['period']}-01")
            period = get_budget_period(period_date)
            queryset = queryset.filter(date__gte=period.start, date__lte=period.end)
        return queryset


class RecurringExpenseViewSet(viewsets.ModelViewSet):
    queryset = RecurringExpense.objects.select_related("category", "category__member", "account").all()
    serializer_class = RecurringExpenseSerializer


class InstallmentPlanViewSet(viewsets.ModelViewSet):
    queryset = InstallmentPlan.objects.select_related("category", "category__member", "account").all()
    serializer_class = InstallmentPlanSerializer


class BudgetSummaryView(APIView):
    def get(self, request):
        value = request.query_params.get("date")
        scope = request.query_params.get("scope", "family")
        member_id = request.query_params.get("member_id")
        summary_date = date.fromisoformat(value) if value else None
        summary = build_budget_summary(summary_date, scope=scope, member_id=member_id)
        return Response(summary)


class ExpectedChargesView(APIView):
    def get(self, request):
        period_param = request.query_params.get("period")
        date_param = request.query_params.get("date")
        period_date = date.fromisoformat(date_param) if date_param else None
        if period_date is None and period_param:
            period_date = date.fromisoformat(f"{period_param}-01")
        period = get_budget_period(period_date)
        charges = []
        for charge in expected_charges_for_period(period):
            member = charge.category.member
            charges.append(
                {
                    "key": charge.key,
                    "source_type": charge.source_type,
                    "source_id": charge.source_id,
                    "name": charge.name,
                    "amount_cents": charge.amount_cents,
                    "date": charge.date,
                    "period_start": charge.period_start,
                    "period_end": charge.period_end,
                    "category": {
                        "id": charge.category.id,
                        "name": charge.category.name,
                        "scope": charge.category.scope,
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
        return Response({"period": {"start": period.start, "end": period.end}, "charges": charges})


class InstallmentProjectionView(APIView):
    def get(self, request):
        value = request.query_params.get("date")
        months = int(request.query_params.get("months", 6))
        projection_date = date.fromisoformat(value) if value else None
        return Response(installment_projection(projection_date, months_ahead=months))


class ConfirmExpectedChargeView(APIView):
    def post(self, request):
        source_type = request.data["source_type"]
        source_id = int(request.data["source_id"])
        charge_date = date.fromisoformat(request.data["date"])
        account = Account.objects.get(pk=request.data["account"])
        transaction = confirm_expected_charge(source_type, source_id, charge_date, account, request.user)
        return Response(TransactionSerializer(transaction, context={"request": request}).data, status=status.HTTP_201_CREATED)


class DismissExpectedChargeView(APIView):
    def post(self, request):
        source_type = request.data["source_type"]
        source_id = int(request.data["source_id"])
        charge_date = date.fromisoformat(request.data["date"])
        period = get_budget_period(charge_date)
        ExpectedChargeDismissal.objects.get_or_create(
            source_type=source_type,
            source_id=source_id,
            period_start=period.start,
            defaults={"created_by": request.user},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
