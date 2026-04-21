from django.core.management import call_command
from django.contrib.auth.models import User
from django.test import TestCase

from budget.models import Account, Category, HouseholdMember, InstallmentPlan, RecurringExpense, Transaction


class SeedDemoDataTests(TestCase):
    def test_seed_demo_data_is_idempotent_and_covers_demo_types(self):
        call_command("seed_demo_data")
        call_command("seed_demo_data")

        self.assertEqual(HouseholdMember.objects.count(), 3)
        self.assertEqual(Category.objects.filter(scope=Category.Scope.GLOBAL).count(), 10)
        self.assertEqual(Category.objects.filter(scope=Category.Scope.PERSONAL).count(), 3)
        self.assertEqual(Account.objects.count(), 4)
        self.assertEqual(Transaction.objects.count(), 20)
        self.assertEqual(RecurringExpense.objects.count(), 5)
        self.assertEqual(InstallmentPlan.objects.count(), 3)
        self.assertTrue(User.objects.filter(username="papa", is_staff=True, is_superuser=True).exists())
        self.assertTrue(User.objects.filter(username="mama", is_staff=False, is_superuser=False).exists())
        self.assertIsNone(HouseholdMember.objects.get(name="Oli").user)
        self.assertEqual(HouseholdMember.objects.get(name="Papa").user.username, "papa")
        self.assertEqual(HouseholdMember.objects.get(name="Mama").user.username, "mama")
        self.assertFalse(Transaction.objects.filter(transaction_type=Transaction.TransactionType.EXPENSE, merchant="").exists())
        self.assertTrue(Transaction.objects.filter(merchant="Superama", created_by__username="mama").exists())
        self.assertTrue(Transaction.objects.filter(note="Demo actual: pago confirmado Internet casa").exists())
        self.assertTrue(Transaction.objects.filter(note="Demo actual: pago confirmado MSI familia Meses").exists())
        self.assertTrue(RecurringExpense.objects.filter(name="Streaming Mama").exists())
        self.assertTrue(InstallmentPlan.objects.filter(name="Demo MSI personal Papa").exists())
        self.assertFalse(Account.objects.filter(account_type="other").exists())
        self.assertFalse(Account.objects.exclude(account_type=Account.AccountType.CASH).exclude(initial_balance_cents=0).exists())
