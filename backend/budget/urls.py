from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AccountViewSet,
    AuthRefreshView,
    BootstrapClaimView,
    BootstrapStatusView,
    BudgetSummaryView,
    CategoryViewSet,
    ConfirmExpectedChargeView,
    DismissExpectedChargeView,
    ExpectedChargesView,
    HouseholdMemberViewSet,
    InstallmentProjectionView,
    InstallmentPlanViewSet,
    InvitationAcceptView,
    InvitationResolveView,
    InvitationViewSet,
    LoginView,
    LogoutView,
    MeView,
    MerchantConceptViewSet,
    OnboardingStatusView,
    RecurringExpenseViewSet,
    SettingsView,
    TransactionViewSet,
    csrf_view,
)

router = DefaultRouter()
router.register("household-members", HouseholdMemberViewSet)
router.register("categories", CategoryViewSet)
router.register("accounts", AccountViewSet)
router.register("invitations", InvitationViewSet, basename="invitations")
router.register("auth/invitations", InvitationViewSet, basename="auth-invitations")
router.register("merchant-concepts", MerchantConceptViewSet)
router.register("transactions", TransactionViewSet)
router.register("recurring-expenses", RecurringExpenseViewSet)
router.register("installment-plans", InstallmentPlanViewSet)

urlpatterns = [
    path("auth/csrf/", csrf_view),
    path("auth/login/", LoginView.as_view()),
    path("auth/logout/", LogoutView.as_view()),
    path("auth/me/", MeView.as_view()),
    path("auth/refresh/", AuthRefreshView.as_view()),
    path("onboarding/status/", OnboardingStatusView.as_view()),
    path("auth/bootstrap/status/", BootstrapStatusView.as_view()),
    path("auth/bootstrap/claim/", BootstrapClaimView.as_view()),
    path("auth/invitations/resolve/", InvitationResolveView.as_view()),
    path("auth/invitations/accept/", InvitationAcceptView.as_view()),
    path("bootstrap/status/", BootstrapStatusView.as_view()),
    path("bootstrap/claim/", BootstrapClaimView.as_view()),
    path("invitations/resolve/", InvitationResolveView.as_view()),
    path("invitations/accept/", InvitationAcceptView.as_view()),
    path("settings/", SettingsView.as_view()),
    path("budget/summary/", BudgetSummaryView.as_view()),
    path("expected-charges/", ExpectedChargesView.as_view()),
    path("expected-charges/confirm/", ConfirmExpectedChargeView.as_view()),
    path("expected-charges/dismiss/", DismissExpectedChargeView.as_view()),
    path("installments/projection/", InstallmentProjectionView.as_view()),
    path("", include(router.urls)),
]
