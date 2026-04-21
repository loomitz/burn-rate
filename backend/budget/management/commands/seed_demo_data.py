from datetime import date

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from budget.models import Account, Category, HouseholdMember, InstallmentPlan, RecurringExpense, Transaction


def pesos(value: int) -> int:
    return value * 100


class Command(BaseCommand):
    help = "Seed Burn Rate with image-based categories and representative demo data."

    def handle(self, *args, **options):
        access_users = self.seed_access_users()
        Transaction.objects.filter(note__startswith="Demo").delete()

        accounts = self.seed_accounts()
        global_categories = self.seed_global_categories()
        members = self.seed_members(access_users)
        personal_categories = self.seed_personal_categories(members)
        self.seed_transactions(accounts, global_categories, personal_categories, access_users)
        self.seed_commitments(accounts, global_categories, personal_categories)

        self.stdout.write(self.style.SUCCESS("Seeded Burn Rate demo data."))

    def seed_accounts(self):
        account_specs = [
            ("Caja", Account.AccountType.CASH, pesos(5000), "#8b5e34"),
            ("BBVA principal", Account.AccountType.BANK, 0, "#1d4ed8"),
            ("Debito Santander", Account.AccountType.DEBIT_CARD, 0, "#b91c1c"),
            ("Tarjeta dorada", Account.AccountType.CREDIT_CARD, 0, "#b7791f"),
        ]
        accounts = {}
        for name, account_type, initial_balance, color in account_specs:
            account, _ = Account.objects.update_or_create(
                name=name,
                defaults={
                    "account_type": account_type,
                    "initial_balance_cents": initial_balance,
                    "color": color,
                    "is_active": True,
                },
            )
            accounts[name] = account
        return accounts

    def seed_global_categories(self):
        category_specs = [
            ("Comida", 11000, "#0f766e", "utensils"),
            ("Meses", 8865, "#7c3aed", "calendar"),
            ("Gas", 2800, "#dc2626", "flame"),
            ("Internet", 3500, "#2563eb", "wifi"),
            ("Perros", 3000, "#ca8a04", "paw"),
            ("Yoga", 1100, "#db2777", "heart"),
            ("Servicios", 1100, "#0891b2", "bolt"),
            ("Mantenimiento", 1000, "#475569", "wrench"),
            ("Bodega", 1000, "#92400e", "box"),
            ("Mucha", 3200, "#16a34a", "sparkles"),
        ]
        categories = {}
        for order, (name, budget, color, icon) in enumerate(category_specs, start=1):
            category, _ = Category.objects.update_or_create(
                name=name,
                scope=Category.Scope.GLOBAL,
                defaults={
                    "color": color,
                    "icon": icon,
                    "order": order,
                    "is_active": True,
                    "member": None,
                    "monthly_budget_cents": pesos(budget),
                },
            )
            categories[name] = category
        return categories

    def seed_access_users(self):
        papa, _ = User.objects.update_or_create(
            username="papa",
            defaults={
                "email": "papa@example.com",
                "first_name": "Papa",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        papa.set_password("burnrate123")
        papa.save()

        mama, _ = User.objects.update_or_create(
            username="mama",
            defaults={
                "email": "mama@example.com",
                "first_name": "Mama",
                "is_staff": False,
                "is_superuser": False,
                "is_active": True,
            },
        )
        mama.set_password("burnrate123")
        mama.save()

        return {"papa": papa, "mama": mama}

    def seed_members(self, access_users):
        member_specs = [
            ("Oli", "#7c3aed", None),
            ("Mama", "#db2777", access_users["mama"]),
            ("Papa", "#2563eb", access_users["papa"]),
        ]
        members = {}
        for name, color, user in member_specs:
            member, _ = HouseholdMember.objects.update_or_create(
                name=name,
                defaults={
                    "color": color,
                    "is_active": True,
                    "user": user,
                },
            )
            members[name] = member
        return members

    def seed_personal_categories(self, members):
        personal_specs = [
            ("Oli", 3000),
            ("Mama", 3000),
            ("Papa", 1000),
        ]
        categories = {}
        for order, (member_name, budget) in enumerate(personal_specs, start=1):
            member = members[member_name]
            category, _ = Category.objects.update_or_create(
                name="Gastos generales",
                scope=Category.Scope.PERSONAL,
                member=member,
                defaults={
                    "color": member.color,
                    "icon": "user",
                    "order": order,
                    "is_active": True,
                    "monthly_budget_cents": pesos(budget),
                },
            )
            categories[member_name] = category
        return categories

    def seed_transactions(self, accounts, global_categories, personal_categories, access_users):
        transaction_specs = [
            {
                "transaction_type": Transaction.TransactionType.INCOME,
                "amount_cents": pesos(45000),
                "date": date(2026, 4, 21),
                "destination_account": accounts["BBVA principal"],
                "note": "Demo siguiente periodo: ingreso familiar mensual",
            },
            {
                "transaction_type": Transaction.TransactionType.INCOME,
                "amount_cents": pesos(42000),
                "date": date(2026, 3, 21),
                "destination_account": accounts["BBVA principal"],
                "note": "Demo actual: ingreso familiar mensual",
            },
            {
                "transaction_type": Transaction.TransactionType.TRANSFER,
                "amount_cents": pesos(2500),
                "date": date(2026, 4, 22),
                "account": accounts["BBVA principal"],
                "destination_account": accounts["Caja"],
                "note": "Demo siguiente periodo: retiro para caja",
            },
            {
                "transaction_type": Transaction.TransactionType.TRANSFER,
                "amount_cents": pesos(3000),
                "date": date(2026, 3, 22),
                "account": accounts["BBVA principal"],
                "destination_account": accounts["Caja"],
                "note": "Demo actual: retiro para caja",
            },
            {
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "amount_cents": pesos(2150),
                "date": date(2026, 3, 23),
                "account": accounts["Debito Santander"],
                "category": global_categories["Comida"],
                "note": "Demo actual: super semanal",
            },
            {
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "amount_cents": pesos(1200),
                "date": date(2026, 4, 2),
                "account": accounts["BBVA principal"],
                "category": global_categories["Gas"],
                "note": "Demo actual: gas estacionario",
            },
            {
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "amount_cents": pesos(650),
                "date": date(2026, 4, 8),
                "account": accounts["BBVA principal"],
                "category": global_categories["Servicios"],
                "note": "Demo actual: agua y luz parcial",
            },
            {
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "amount_cents": pesos(750),
                "date": date(2026, 4, 12),
                "account": accounts["Tarjeta dorada"],
                "category": global_categories["Mantenimiento"],
                "note": "Demo actual: arreglo menor casa",
            },
            {
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "amount_cents": pesos(980),
                "date": date(2026, 4, 13),
                "account": accounts["Caja"],
                "category": global_categories["Bodega"],
                "note": "Demo actual: bodega mensual",
            },
            {
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "amount_cents": pesos(700),
                "date": date(2026, 4, 14),
                "account": accounts["Caja"],
                "category": personal_categories["Oli"],
                "note": "Demo actual: gasto personal Oli",
            },
            {
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "amount_cents": pesos(1600),
                "date": date(2026, 4, 15),
                "account": accounts["Tarjeta dorada"],
                "category": personal_categories["Mama"],
                "note": "Demo actual: gasto personal Mama",
            },
            {
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "amount_cents": pesos(1200),
                "date": date(2026, 4, 16),
                "account": accounts["Debito Santander"],
                "category": personal_categories["Papa"],
                "note": "Demo actual: gasto personal Papa con sobregasto",
            },
            {
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "amount_cents": pesos(1850),
                "date": date(2026, 4, 23),
                "account": accounts["Debito Santander"],
                "category": global_categories["Comida"],
                "note": "Demo siguiente periodo: super semanal",
            },
            {
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "amount_cents": pesos(850),
                "date": date(2026, 4, 24),
                "account": accounts["Caja"],
                "category": global_categories["Perros"],
                "note": "Demo siguiente periodo: croquetas",
            },
            {
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "amount_cents": pesos(1200),
                "date": date(2026, 4, 25),
                "account": accounts["Tarjeta dorada"],
                "category": personal_categories["Oli"],
                "note": "Demo siguiente periodo: ropa Oli",
            },
            {
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "amount_cents": pesos(3300),
                "date": date(2026, 4, 26),
                "account": accounts["Tarjeta dorada"],
                "category": personal_categories["Mama"],
                "note": "Demo siguiente periodo: gasto personal Mama con sobregasto",
            },
            {
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "amount_cents": pesos(450),
                "date": date(2026, 4, 27),
                "account": accounts["Caja"],
                "category": personal_categories["Papa"],
                "note": "Demo siguiente periodo: gasto personal Papa",
            },
        ]

        for spec in transaction_specs:
            if spec["transaction_type"] == Transaction.TransactionType.EXPENSE:
                spec.setdefault("merchant", self.merchant_from_note(spec["note"]))
            spec.setdefault("merchant", "")
            spec.setdefault("created_by", self.created_by_for_demo_note(spec["note"], access_users))
            Transaction.objects.update_or_create(
                note=spec["note"],
                defaults=spec,
            )

    def merchant_from_note(self, note):
        merchant_map = {
            "Demo actual: super semanal": "Superama",
            "Demo actual: gas estacionario": "Gas Express",
            "Demo actual: agua y luz parcial": "CFE y Agua",
            "Demo actual: arreglo menor casa": "Ferreteria local",
            "Demo actual: bodega mensual": "Bodega centro",
            "Demo actual: gasto personal Oli": "Papeleria Oli",
            "Demo actual: gasto personal Mama": "Boutique Mama",
            "Demo actual: gasto personal Papa con sobregasto": "Tienda Papa",
            "Demo siguiente periodo: super semanal": "Costco",
            "Demo siguiente periodo: croquetas": "Veterinaria Patitas",
            "Demo siguiente periodo: ropa Oli": "Zara Kids",
            "Demo siguiente periodo: gasto personal Mama con sobregasto": "Liverpool",
            "Demo siguiente periodo: gasto personal Papa": "Home Depot",
            "Demo actual: pago confirmado Internet casa": "Internet casa",
            "Demo actual: pago confirmado MSI familia Meses": "MSI familia Meses",
            "Demo actual: pago confirmado MSI Papa": "MSI Papa",
        }
        return merchant_map.get(note, note.replace("Demo actual: ", "").replace("Demo siguiente periodo: ", ""))

    def created_by_for_demo_note(self, note, access_users):
        if "Mama" in note or "Oli" in note or "super semanal" in note or "bodega mensual" in note:
            return access_users["mama"]
        return access_users["papa"]

    def seed_commitments(self, accounts, global_categories, personal_categories):
        internet, _ = RecurringExpense.objects.update_or_create(
            name="Internet casa",
            defaults={
                "amount_cents": pesos(3500),
                "category": global_categories["Internet"],
                "account": accounts["BBVA principal"],
                "start_date": date(2026, 3, 21),
                "end_date": None,
                "charge_day": 5,
                "is_active": True,
            },
        )
        RecurringExpense.objects.update_or_create(
            name="Yoga mensual",
            defaults={
                "amount_cents": pesos(1100),
                "category": global_categories["Yoga"],
                "account": accounts["Tarjeta dorada"],
                "start_date": date(2026, 3, 21),
                "end_date": None,
                "charge_day": 24,
                "is_active": True,
            },
        )
        RecurringExpense.objects.update_or_create(
            name="Gasto personal Oli recurrente",
            defaults={
                "amount_cents": pesos(600),
                "category": personal_categories["Oli"],
                "account": accounts["Debito Santander"],
                "start_date": date(2026, 3, 21),
                "end_date": None,
                "charge_day": 2,
                "is_active": True,
            },
        )
        RecurringExpense.objects.update_or_create(
            name="Streaming Mama",
            defaults={
                "amount_cents": pesos(399),
                "category": personal_categories["Mama"],
                "account": accounts["Tarjeta dorada"],
                "start_date": date(2026, 3, 21),
                "end_date": None,
                "charge_day": 18,
                "is_active": True,
            },
        )
        RecurringExpense.objects.update_or_create(
            name="Seguro perros",
            defaults={
                "amount_cents": pesos(780),
                "category": global_categories["Perros"],
                "account": accounts["BBVA principal"],
                "start_date": date(2026, 3, 21),
                "end_date": None,
                "charge_day": 12,
                "is_active": True,
            },
        )
        InstallmentPlan.objects.filter(name="Demo MSI global - categoria Meses").update(
            name="Demo MSI familia - categoria Meses"
        )
        family_msi, _ = InstallmentPlan.objects.update_or_create(
            name="Demo MSI familia - categoria Meses",
            defaults={
                "total_amount_cents": pesos(8865),
                "category": global_categories["Meses"],
                "account": accounts["Tarjeta dorada"],
                "start_date": date(2026, 3, 21),
                "end_date": date(2026, 5, 21),
                "is_active": True,
            },
        )
        mama_msi, _ = InstallmentPlan.objects.update_or_create(
            name="Demo MSI personal Mama",
            defaults={
                "total_amount_cents": pesos(3000),
                "category": personal_categories["Mama"],
                "account": accounts["Tarjeta dorada"],
                "start_date": date(2026, 3, 21),
                "end_date": date(2026, 5, 21),
                "is_active": True,
            },
        )
        papa_msi, _ = InstallmentPlan.objects.update_or_create(
            name="Demo MSI personal Papa",
            defaults={
                "total_amount_cents": pesos(2400),
                "category": personal_categories["Papa"],
                "account": accounts["Tarjeta dorada"],
                "start_date": date(2026, 3, 21),
                "end_date": date(2026, 4, 21),
                "is_active": True,
            },
        )
        self.seed_confirmed_commitment_payments(
            accounts,
            internet=internet,
            family_msi=family_msi,
            papa_msi=papa_msi,
            created_by=User.objects.get(username="papa"),
        )

    def seed_confirmed_commitment_payments(self, accounts, internet, family_msi, papa_msi, created_by):
        confirmed_specs = [
            {
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "merchant": "Internet casa",
                "amount_cents": pesos(3500),
                "date": date(2026, 4, 5),
                "account": accounts["BBVA principal"],
                "category": internet.category,
                "recurring_expense": internet,
                "note": "Demo actual: pago confirmado Internet casa",
                "created_by": created_by,
            },
            {
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "merchant": "MSI familia Meses",
                "amount_cents": pesos(2955),
                "date": date(2026, 3, 21),
                "account": accounts["Tarjeta dorada"],
                "category": family_msi.category,
                "installment_plan": family_msi,
                "note": "Demo actual: pago confirmado MSI familia Meses",
                "created_by": created_by,
            },
            {
                "transaction_type": Transaction.TransactionType.EXPENSE,
                "merchant": "MSI Papa",
                "amount_cents": pesos(1200),
                "date": date(2026, 3, 21),
                "account": accounts["Tarjeta dorada"],
                "category": papa_msi.category,
                "installment_plan": papa_msi,
                "note": "Demo actual: pago confirmado MSI Papa",
                "created_by": created_by,
            },
        ]
        for spec in confirmed_specs:
            Transaction.objects.update_or_create(note=spec["note"], defaults=spec)
