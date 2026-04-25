# Domain

## Budget Period

The default cutoff day is `20`. A period starts on the day after cutoff and ends on the next cutoff day.

With cutoff day `20`:

- `2026-04-20` belongs to `2026-03-21` through `2026-04-20`.
- `2026-04-21` belongs to `2026-04-21` through `2026-05-20`.

Cutoff day is validated from `1` to `28` to avoid invalid dates in February.

## Household Members

A `HouseholdMember` is a budget person in the home. It is not a tenant. It may optionally be linked to a Django login user, but it primarily exists to own personal budget categories.

When a household member is created, the operator chooses whether that person has app access. If access is enabled, Burn Rate creates or links a local Django user. Admin access maps to Django staff/superuser flags and allows changing app settings, people, and categories.

## Categories

Categories are the budget envelopes.

- `global`: internal category scope for the one family budget in the installation.
- `personal`: belongs to one `HouseholdMember`.

A personal category must have a member. A family/global category must not have a member. The UI calls this scope `Familia`; `global` is only the internal database value.

Each category stores a presentation color and an icon key. The icon key points to the curated local frontend icon catalog, so the database does not store SVG markup or external asset URLs. The frontend currently renders that catalog with Lucide Vue icons while preserving short stable keys such as `tag`, `paw`, and `shopping-cart`.

## Budget Allocations

Each active category has a monthly default budget. When a period is viewed, Burn Rate materializes a `BudgetAllocation` for that category and period. This preserves historical budgets when a default budget changes later.

## Transactions

Transactions are manual financial movements.

- `expense`: consumes budget and requires category, account, and a merchant/name for the expense.
- `income`: adds money to a destination account but does not affect category spending.
- `transfer`: moves money between accounts and does not affect category spending.
- `expected_charge`: reserved for future persisted expected charges.

For expenses in personal categories, the member is inferred from the category. Every transaction records the Django user who created it when the movement comes through the API, so the UI can show who registered an expense when more than one person has access.

Expense merchant/concept names are also stored in a reusable catalog. Saving an expense, recurring expense, or installment plan with a new merchant creates a catalog entry; future expense and commitment capture can search and reuse that saved name.

## Accounts

Accounts represent payment media or sources such as cash, bank accounts, debit cards, and credit cards. Only cash accounts can have an initial balance. Bank accounts and cards start at zero in Burn Rate because the app is not trying to reconcile full account statements.

Allowed account types:

- `cash`
- `bank`
- `debit_card`
- `credit_card`

## Recurring Expenses

A recurring expense is a monthly commitment such as a subscription. It has an internal name, merchant, amount, category, optional account, start date, optional end date, charge day, and an optional automatic-charge flag.

For each active period, Burn Rate generates a pending expected charge unless it was already confirmed or dismissed.

When automatic charging is enabled, the recurring expense must have an account. Burn Rate posts the real expense once the configured day has arrived, and it does so idempotently per budget period so refreshes do not duplicate charges.

## Installment Plans

An installment plan represents a purchase at months without interest. The user enters an internal name, merchant, total amount, category, optional account, first payment date tracked by Burn Rate, last payment date, and the payment number represented by that first tracked date.

Burn Rate calculates total monthly payments from the start and end month plus the first tracked payment number. This lets the initial setup register purchases that are already on payment 4, 11, or any later month without treating prior payments as future spending. Each period consumes only that period's monthly payment. Any cent remainder is added to the final payment.

MSI payments are automatic budget commitments. They affect the budget summary as expected spending without requiring a manual `Pagar` action from the commitments screen. The commitments UI groups MSI separately and shows the current period payment plus a six-period forward projection so the household can see when MSI pressure falls or accumulates.

## Budget Summary

Budget summary includes:

- Budgeted amount.
- Actual spent.
- Pending expected charges.
- Consumed amount.
- Available amount.
- Percent available.

The family summary is the shared household budget and excludes personal categories. A member summary includes only that person's personal categories. The API also supports a technical `total` scope for reports that need family plus every personal category together.

## Demo Data

The project includes `python manage.py seed_demo_data` to create repeatable local data for testing:

- Family categories from the initial spreadsheet image: Comida, Meses, Gas, Internet, Perros, Yoga, Servicios, Mantenimiento, Bodega, and Mucha.
- Household members from the last three spreadsheet rows: Oli, Mama, and Papa.
- Access users for testing: `papa` is an admin user, `mama` is a normal user, and `Oli` remains a budget person without app login.
- One personal category called `Gastos generales` for each member, using the row amount as the monthly budget.
- Representative cash, bank, debit card, and credit card accounts.
- Example income, transfer, family expenses, personal expenses with merchant names, recurring expenses, confirmed recurring payments, MSI plans, and confirmed MSI payments.

The command is idempotent and can be run again without duplicating the seed records.
