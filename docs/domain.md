# Domain

## Budget Period

The budget period is the calendar month: from the 1st through the last day of the month. It is the one clock for budgets and for cash, debit, and bank spending.

- `2026-04-20` belongs to `2026-04-01` through `2026-04-30`.
- `2026-05-01` belongs to `2026-05-01` through `2026-05-31`.

There is no global cutoff day. Cutoff days exist only per credit card.

## Corte and Card Cycles

Each credit card has its own corte (statement closing day). It is required for credit cards, not allowed on other account types, and validated from `1` to `28` to avoid invalid dates in February.

A card cycle is that card's statement window: it runs from the day after a corte through the next corte, inclusive. Spending on the day of the corte belongs to the cycle that closes that day. Card cycles cross calendar months.

With a corte on day `20`:

- An expense on `2026-04-20` belongs to the cycle `2026-03-21` through `2026-04-20` (the cycle closing that day).
- An expense on `2026-04-21` belongs to the cycle `2026-04-21` through `2026-05-20`.

A card's statement (estado de cuenta) is its closed cycle: the cycle's purchases plus that cycle's MSI mensualidades. It is what must be paid to avoid interest.

Each card also has a bank payment due day (`payment_due_day`, `1`–`31`). For every closed or open cycle, Burn Rate resolves the first occurrence of that day strictly after the corte. If that day does not exist in the target month, it uses the month's last day. The operational payment date is always three calendar days before the bank deadline; both dates remain visible so the safety margin is explicit.

Existing cards created before this field was introduced keep `payment_due_day=null` until an admin configures the real bank deadline; the migration never invents a date.

## Live Window and Release

A category's budget is consumed by its live window (ventana viva): the set of open spending windows at any moment — the current calendar month for cash/debit/bank spending, plus each credit card's open cycle.

Available (disponible) = category budget − cash/debit/bank spending of the current calendar month − each credit card's spending since its last corte − pending expected charges.

At a card's corte, that card's cycle spending is released (liberación): it stops consuming category budgets and becomes the card's statement, visible in payments as an obligation. The category's available goes back up by the released amount.

Example with a `$10,000` budget and one card with corte `20`:

- `2026-07-10`: `$5,000` with the card and `2026-07-12`: `$2,000` in cash → available `$3,000`.
- `2026-07-21` (day after the corte): the card's `$5,000` is released into the statement → available `$8,000`.
- `2026-07-25`: `$4,000` with the card → available `$4,000`.
- `2026-08-05`: August budget minus the card's open cycle that started `2026-07-21` → available `$6,000`. The July close snapshot stays at `$4,000`.

Carryover categories are excluded from release: their pot is the accumulated real balance (monthly credits minus all spending), so a card's corte never gives money back to a carryover pot.

## Monthly Flow and Overspend

Monthly flow (flujo mensual) is everything spent in a category during the calendar month regardless of windows. It is an informative metric only: a category's total monthly outflow can legitimately exceed its budget, because each corte recharges that card's window. Monthly flow above budget is not overspend.

Overspend (sobregiro) is a negative live available — the open windows together exceeded the category budget. The historical record is the snapshot of negative available at calendar-month close: past months are immutable close snapshots, the current month is evaluated as of today, and future months project the month close.

## Household Members

A `HouseholdMember` is a budget person in the home. It is not a tenant. It may optionally be linked to a Django login user, but it primarily exists to own personal budget categories.

When a household member is created, the operator chooses whether that person has app access. If access is enabled, Burn Rate creates or links a local Django user. Admin access maps to Django staff/superuser flags and allows changing app settings, people, and categories.

## Categories

Categories are the budget envelopes. Which envelope an expense consumes is decided by its category, never by the payment medium or the account owner.

- `global`: internal category scope for the one family budget in the installation.
- `personal`: belongs to one `HouseholdMember`.

A personal category must have a member. A family/global category must not have a member. The UI calls this scope `Familia`; `global` is only the internal database value.

Each category also has a `budget_treatment`:

- `budgeted`: normal budget category. It receives period allocations, consumes budget, participates in available-balance calculations, and can be monthly-reset or carryover.
- `tracking_only`: outside the budget. It records manual expenses, recurring commitments, or installment plans for visibility, but it does not receive allocations, consume budget, create overspend records, affect account balances, or contribute to per-card statement totals.

Each category stores a presentation color and an icon key. The icon key points to the curated local frontend icon catalog, so the database does not store SVG markup or external asset URLs. The frontend currently renders that catalog with Lucide Vue icons while preserving short stable keys such as `tag`, `paw`, and `shopping-cart`.

## Budget Allocations

Each active budgeted category has a monthly default budget. When a calendar month is viewed, Burn Rate materializes a `BudgetAllocation` for that category and month. This preserves historical budgets when a default budget changes later. Tracking-only categories never materialize budget allocations.

## Transactions

Transactions are manual financial movements.

- `expense`: consumes budget and requires category, account, and a merchant/name for the expense. If the category is tracking-only, the account is optional and the transaction stays outside budget/account calculations.
- `income`: adds money to a destination account but does not affect category spending.
- `transfer`: moves money between accounts and does not affect category spending.
- `expected_charge`: reserved for future persisted expected charges.

An expense consumes the window its date and account fall into: credit-card expenses consume through that card's cycle until its corte releases them; every other expense consumes the calendar month of its date.

For expenses in personal categories, the member is inferred from the category. Every transaction records the Django user who created it when the movement comes through the API, so the UI can show who registered an expense when more than one person has access.

Expense merchant/concept names are also stored in a reusable catalog. Saving an expense, recurring expense, or installment plan with a new merchant creates a catalog entry; future expense and commitment capture can search and reuse that saved name.

## Accounts

Accounts represent payment media or sources such as cash, bank accounts, debit cards, and credit cards. Only cash accounts can have an initial balance. Bank accounts and cards start at zero in Burn Rate because the app is not trying to reconcile full account statements.

Allowed account types:

- `cash`
- `bank`
- `debit_card`
- `credit_card`

Credit cards require a `cutoff_day` (their corte, `1`–`28`) and new cards require a `payment_due_day` (the bank deadline, `1`–`31`). Existing migrated cards can temporarily return a null payment deadline until configured. Any account can have an optional owner (titular): the household member the card or account belongs to. The owner is grouping and filtering metadata only — it never decides which budget an expense consumes; the category does.

Each active credit card has a derived per-card payments summary with two blocks: the closed cycle (the statement to pay to avoid interest) and the open cycle (what is accumulating toward the next corte). Each block sums the cycle's real purchases paid with that card, excluding transactions linked to installment plans and tracking-only transactions, plus that cycle's MSI mensualidades for active budgeted plans assigned to the same card. Statements can be totaled across cards and grouped by owner. Inactive credit cards are excluded from the payments summary, but their live cycle spending still consumes category budgets until their corte.

## Recurring Expenses

A recurring expense is a monthly commitment such as a subscription. It has an internal name, merchant, amount, category, optional account, start date, optional end date, charge day, and an optional automatic-charge flag.

For each calendar month, Burn Rate generates a pending expected charge unless it was already confirmed or dismissed.

When automatic charging is enabled for a budgeted category, the recurring expense must have an account. Tracking-only recurring expenses can post without an account so they do not affect account balances. Burn Rate posts the real expense once the configured day has arrived, and it does so idempotently per calendar month so refreshes do not duplicate charges. The posted expense then consumes whatever window its date and account fall into.

## Installment Plans

An installment plan represents a purchase at months without interest (MSI). The user enters an internal name, merchant, total amount, category, optional account, first payment date tracked by Burn Rate, last payment date, and the payment number represented by that first tracked date.

Burn Rate calculates total monthly payments from the start and end month plus the first tracked payment number. This lets the initial setup register purchases that are already on payment 4, 11, or any later month without treating prior payments as future spending. Any cent remainder is added to the final payment.

Each MSI mensualidad is anchored to its card's cycle: exactly one mensualidad per statement, numbered by whole-cycle offsets from the cycle that contains the plan's start date. A plan on a card with corte `20` starting `2026-04-21` charges mensualidad 1 in the cycle `2026-04-21` through `2026-05-20`, mensualidad 2 in `2026-05-21` through `2026-06-20`, and so on. Plans without a card fall back to calendar months.

MSI payments are automatic budget commitments. They affect the budget summary as expected spending without requiring a manual `Pagar` action from the commitments screen. The commitments UI groups MSI separately and shows the current payment plus a six-column forward projection — calendar months by default, or one card's real cycles — so the household can see when MSI pressure falls or accumulates.

## Budget Summary

Budget summary is computed per calendar month and includes:

- Budgeted amount.
- Spent amount (live-window consumption: month window plus open card windows).
- Pending expected charges.
- Consumed amount.
- Available amount.
- Monthly flow (informative).
- The live windows themselves, so the UI can show what is consuming the budget and from which card.
- Percent available.

The family summary is the shared household budget and excludes personal categories. A member summary includes only that person's personal categories. The API also supports a technical `total` scope for reports that need family plus every personal category together.

Tracking-only categories are excluded from the family, member, and total budget summaries. They are exposed through a separate off-budget summary with calendar-month totals for registered and expected amounts.

## Demo Data

The project includes `python manage.py seed_demo_data` to create repeatable local data for testing:

- Family categories from the initial spreadsheet image: Comida, Meses, Gas, Internet, Perros, Yoga, Servicios, Mantenimiento, Bodega, and Mucha.
- Household members from the last three spreadsheet rows: Oli, Mama, and Papa.
- Access users for testing: `papa` is an admin user, `mama` is a normal user, and `Oli` remains a budget person without app login.
- One personal category called `Gastos generales` for each member, using the row amount as the monthly budget.
- Representative cash, bank, debit card, and credit card accounts.
- Example income, transfer, family expenses, personal expenses with merchant names, recurring expenses, confirmed recurring payments, MSI plans, and confirmed MSI payments.

The command is idempotent and can be run again without duplicating the seed records.
