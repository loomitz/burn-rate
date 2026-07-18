# API

All endpoints require an authenticated Django session except `auth/csrf`, `auth/login`, onboarding status, bootstrap claim/status, and invitation resolve/accept.

## Auth

- `GET /api/auth/csrf/`: sets CSRF cookie.
- `POST /api/auth/login/`: body `{ "email": "...", "password": "..." }`. Legacy username payloads are still accepted for existing local clients.
- `POST /api/auth/logout/`: ends the session.
- `GET /api/auth/me/`: returns current user.
- `POST /api/auth/refresh/`: renews/touches the current session and returns current user.

## Onboarding

- `GET /api/onboarding/status/`: public read-only startup check used before login or first-admin claim.

Response shape:

```json
{
  "ready": true,
  "database": {
    "connected": true,
    "message": "Conexion a base de datos lista.",
    "configured": {
      "engine": "postgresql",
      "name": "burn_rate",
      "user": "burn_rate",
      "host": "db",
      "port": "5432",
      "password_configured": true
    }
  },
  "migrations": {
    "applied": true,
    "pending_count": 0
  },
  "initial_config": {
    "ready": true,
    "needs_first_admin": true,
    "has_users": false,
    "settings_ready": true
  }
}
```

The endpoint does not write Docker or database configuration. It only checks the environment-provided database connection, pending migrations, default app settings availability, and whether the installation still needs the first admin.

## Bootstrap

- `GET /api/bootstrap/status/`: returns whether the installation can be claimed by the first admin.
- `POST /api/bootstrap/claim/`: creates the first admin only when no users exist and starts a session.

Claim payload:

```json
{
  "email": "papa@example.com",
  "full_name": "Luis Hernandez",
  "display_name": "Papa",
  "password": "safe-password"
}
```

## Invitations

- `GET /api/invitations/`: staff-only list.
- `POST /api/invitations/`: staff-only create. Always returns `accept_url` for copying. `email_sent` is `true` only when SMTP and `BURN_RATE_PUBLIC_URL` are configured.
- `DELETE /api/invitations/{id}/`: staff-only delete for invitations that have not been accepted.
- `POST /api/invitations/{id}/revoke/`: staff-only revoke.
- `GET /api/invitations/resolve/?token=...`: public token lookup for the acceptance screen.
- `POST /api/invitations/accept/`: public token acceptance; creates the user/member and starts a session.

Create payload:

```json
{
  "email": "mama@example.com",
  "is_admin": false
}
```

Accept payload:

```json
{
  "token": "one-time-token",
  "email": "mama@example.com",
  "full_name": "Ana Hernandez",
  "display_name": "Mama",
  "password": "safe-password"
}
```

## Settings

- `GET /api/settings/`
- `PUT /api/settings/`
- `PATCH /api/settings/`

Payload:

```json
{ "currency": "MXN", "time_zone": "America/Mexico_City" }
```

There is no `cutoff_day` in settings anymore: the budget period is always the calendar month, and each credit card carries its own cutoff and payment due day on `/api/accounts/`. `time_zone` is optional on write and must be a valid IANA time zone; it defines the app-local "today" used to resolve budget months and card cycles.

## CRUD

- `/api/household-members/`
- `/api/categories/`
- `/api/accounts/`
- `/api/transactions/`
- `/api/recurring-expenses/`
- `/api/installment-plans/`

These are DRF viewset endpoints with list, retrieve, create, update, partial update, and delete.

Unsafe methods for `accounts`, `household-members`, `categories`, and `settings` require an admin user. In Burn Rate, admin means the linked Django user has `is_staff=true`.

`household-members` accepts optional access fields on create/update:

```json
{
  "name": "Ana",
  "color": "#2563eb",
  "has_access": true,
  "username": "ana",
  "email": "ana@example.com",
  "password": "safe-password",
  "is_admin": false
}
```

The response includes `access_enabled`, `user_username`, `user_email`, and `user_is_admin`.

`categories` accepts a user-facing color and icon key:

```json
{
  "name": "Mascotas",
  "scope": "global",
  "budget_treatment": "budgeted",
  "monthly_budget_cents": 100000,
  "color": "#ca8a04",
  "icon": "paw"
}
```

Categories default to `budget_treatment="budgeted"` and `budget_behavior="monthly_reset"`. To create a category that accumulates unused budget, set `budget_behavior="carryover"` and include `carryover_initial_balance_cents` plus `carryover_start_date`:

```json
{
  "name": "Viajes",
  "scope": "global",
  "monthly_budget_cents": 250000,
  "budget_behavior": "carryover",
  "carryover_initial_balance_cents": -50000,
  "carryover_start_date": "2026-04-01"
}
```

To create a category outside the budget, set `budget_treatment="tracking_only"` and omit the monthly budget:

```json
{
  "name": "Tarjeta ajena",
  "scope": "global",
  "budget_treatment": "tracking_only",
  "color": "#7c3aed",
  "icon": "credit-card"
}
```

Tracking-only categories can be used by expenses, recurring expenses, and installment plans, but they do not participate in budget summaries, budget allocations, account balances, or credit-card payment-to-avoid-interest totals. `budget_treatment`, `budget_behavior`, `carryover_initial_balance_cents`, and `carryover_start_date` are creation-time configuration. They cannot be changed later. Use `PATCH /api/categories/{id}/` with name, color, icon, scope, member, `is_active`, or `monthly_budget_cents` to edit an existing budgeted category without deleting historical transactions. When `monthly_budget_cents` changes, include `budget_effective_date`; the new budget applies from that calendar month forward.

`icon` is a stable key from the frontend's curated local icon catalog. Existing categories default to `tag`; old keys such as `paw`, `bolt`, and `box` remain valid. The frontend can also normalize `lucide:`-prefixed values to the same local keys when the icon exists in the curated catalog.

`accounts` supports `cash`, `bank`, `debit_card`, and `credit_card`. It also accepts a user-facing `color` and `is_active` flag on create/update. `initial_balance_cents` is only valid for `cash`; non-cash accounts must use `0`.

New credit cards require `cutoff_day` — the card's corte, validated from `1` to `28` — and `payment_due_day` — the bank deadline, validated from `1` to `31`. Other account types must omit both fields and always return them as `null`. Cards migrated from an earlier version keep `payment_due_day=null` until the real bank deadline is configured; the migration does not guess it. Any account accepts an optional `owner` (a household member id) for grouping and filtering; it never affects budget attribution:

```json
{
  "name": "Tarjeta oro",
  "account_type": "credit_card",
  "color": "#eab308",
  "cutoff_day": 15,
  "payment_due_day": 5,
  "owner": 2,
  "is_active": true
}
```

Responses include the read-only `owner_name` (`"Ana"` for the example above; both `owner` and `owner_name` are `null` when the account has no owner) and the derived `current_balance_cents`.

Use `PATCH /api/accounts/{id}/` to edit an existing account without deleting historical transactions.

`recurring-expenses` uses `name` for the household label and `merchant` for the actual store/provider written to the confirmed automatic expense:

```json
{
  "name": "Internet casa",
  "merchant": "Telmex",
  "amount_cents": 59900,
  "category": 2,
  "account": 1,
  "start_date": "2026-04-01",
  "charge_day": 5,
  "auto_charge": true,
  "is_active": true
}
```

When `auto_charge=true`, `account` is required for budgeted categories. Tracking-only recurring expenses can omit `account` and will be registered without changing account balances. Burn Rate records the real expense automatically once the configured day has arrived. Without `auto_charge`, the item remains a pending expected charge until the user confirms or dismisses it.

`installment-plans` accepts the first payment date and `months_count`; the API calculates `end_date` from that count. For a purchase already in progress, use the original first payment date so the current payment number is calculated from the calendar:

```json
{
  "name": "Laptop",
  "merchant": "Liverpool",
  "total_amount_cents": 1200000,
  "category": 2,
  "account": 1,
  "start_date": "2025-06-25",
  "months_count": 12,
  "round_up_monthly_payment": true,
  "is_active": true
}
```

Expenses in tracking-only categories can omit `account`:

```json
{
  "transaction_type": "expense",
  "merchant": "Compra ajena",
  "amount_cents": 25000,
  "date": "2026-04-25",
  "category": 9
}
```

`first_payment_number` is still accepted for old integrations, but the browser flow uses `months_count`. `round_up_monthly_payment` defaults to `true`; set it to `false` only when the bank does not round each required payment to the next full peso.

`transactions` for expenses require a merchant/name. The API sets `created_by` from the logged-in Django user and returns `created_by_username` for audit visibility in the UI.
Creating an expense, recurring expense, or installment plan also records the merchant/name in the merchant concept catalog, normalizing extra spaces and merging case-insensitive duplicates.

Example expense payload:

```json
{
  "transaction_type": "expense",
  "merchant": "Super local",
  "amount_cents": 25000,
  "date": "2026-04-25",
  "account": 1,
  "category": 2,
  "note": "Despensa semanal"
}
```

Expense responses include:

```json
{
  "merchant": "Super local",
  "created_by": 1,
  "created_by_username": "papa"
}
```

## Merchant Concepts

- `GET /api/merchant-concepts/`: returns saved merchants/concepts ordered by use count.
- `GET /api/merchant-concepts/?search=super`: filters suggestions by the normalized name.

The frontend uses this read-only endpoint to suggest existing concepts while the user types in expense capture. New concepts are created indirectly when a new expense is saved.

## Budget Summary

`GET /api/budget/summary/?date=YYYY-MM-DD&scope=family|member|total&member_id=ID`

Returns period, totals, breakdown, and category rows. `period` is the calendar month containing `date`:

```json
{ "period": { "start": "2026-07-01", "end": "2026-07-31" } }
```

`family` is the one shared household budget. The older `global` value is accepted as an alias for `family`, but the UI should not present both because there is only one family per installation.

The category row includes:

- `color`
- `icon`
- `budget_cents`
- `spent_cents`
- `expected_cents`
- `consumed_cents`
- `available_cents`
- `real_available_cents`
- `projected_available_cents`
- `monthly_flow_cents`
- `live_windows`
- `carryover_real_balance_cents`
- `carryover_start_date`
- `budget_behavior`
- `budget_treatment`
- `overspend_count`
- `overspend_total_cents`
- `last_overspend_cents`
- `last_overspend_period_start`
- `last_overspend_period_end`
- `percent_available`
- `is_overspent`

For `monthly_reset` categories, `available_cents` follows the live-window model: budget minus the month's cash/debit/bank spend, minus each credit card's spend since its last corte, minus pending expected charges. `spent_cents` is that live consumption, while `monthly_flow_cents` is the informative total spent in the calendar month regardless of windows — the two can differ in either direction when card cycles cross the month boundary, and monthly flow above budget is not overspend. The overspend fields summarize closed months whose live available was negative at month close.

`live_windows` lists the open windows consuming the budget: one `month` window (always present for `monthly_reset` categories) plus one `card` window per credit card with spending in its open cycle:

```json
"live_windows": [
  {
    "kind": "month",
    "account_id": null,
    "account_name": null,
    "start": "2026-07-01",
    "end": "2026-07-31",
    "spent_cents": 200000
  },
  {
    "kind": "card",
    "account_id": 3,
    "account_name": "Tarjeta oro",
    "start": "2026-06-21",
    "end": "2026-07-20",
    "spent_cents": 500000
  }
]
```

The current month is evaluated as of today; past months are the immutable month-close snapshot and future months project the month close.

For `carryover` categories, `live_windows` is empty and release does not apply: `real_available_cents` is the accumulated real balance, `projected_available_cents`/`available_cents` subtract pending expected charges as the current free amount, and `spent_cents` equals `monthly_flow_cents`.

`totals` and each `breakdown` bucket carry `budget_cents`, `spent_cents`, `expected_cents`, `available_cents`, `real_available_cents`, and `monthly_flow_cents`.

The frontend uses `category_id` from these rows to let the user click a category card and inspect the matching expense transactions for the active month. Tracking-only categories are excluded from this endpoint.

`GET /api/budget/off-budget-summary/?date=YYYY-MM-DD`

Returns calendar-month totals for tracking-only categories:

```json
{
  "period": { "start": "2026-04-01", "end": "2026-04-30" },
  "totals": { "spent_cents": 25000, "expected_cents": 12000, "total_cents": 37000 },
  "categories": [],
  "expected_charges": []
}
```

## Expected Charges

`GET /api/expected-charges/?date=YYYY-MM-DD`

Returns generated pending charges from recurring expenses and installment plans.

Charges are generated per calendar month. `period=YYYY-MM` remains accepted for older callers and resolves to that calendar month; a full `date` resolves to the calendar month that contains it.

The frontend treats recurring charges as actionable commitments. Installment charges remain automatic budget commitments and are shown through the MSI projection endpoint instead of the `Pagar/Omitir` action list.

`POST /api/expected-charges/auto-post/`

Payload:

```json
{
  "date": "2026-05-15"
}
```

Creates due real `expense` transactions for active recurring expenses with `auto_charge=true`, using each budgeted recurring expense's configured account. Tracking-only automatic charges can post without an account. The operation is idempotent per calendar month, so repeated calls do not duplicate charges. The app calls it before refreshing dashboard data.

`POST /api/expected-charges/confirm/`

Payload:

```json
{
  "source_type": "recurring",
  "source_id": 1,
  "date": "2026-05-01",
  "account": 1
}
```

Creates a real `expense` transaction. The transaction `merchant` comes from the commitment `merchant`, not from the internal commitment `name`. Tracking-only expected charges may send `"account": null`. For an MSI plan on a credit card, the pending mensualidad is looked up in the calendar month of its cycle's corte, so the charge can be confirmed with any `date` inside the card cycle.

`POST /api/expected-charges/dismiss/`

Payload:

```json
{
  "source_type": "installment",
  "source_id": 1,
  "date": "2026-05-01"
}
```

Hides that generated charge. The backend resolves the dismissal anchor from the commitment itself: if the commitment is attached to a credit card, the dismissal pins to the card cycle containing `date`; otherwise it pins to the calendar month of `date`. For a plan on a card with corte `20`, dismissing with `"date": "2026-05-01"` hides the mensualidad of the cycle `2026-04-21` through `2026-05-20`.

## Installment Projection

`GET /api/installments/projection/?date=YYYY-MM-DD&months=6&account=ID`

Returns the current column plus the next `months` columns for active MSI plans. With `months=6`, the response contains seven period rows: current plus six future. The response works in one of two modes:

- `month` (default): columns are calendar months and `key` is `YYYY-MM`. Each mensualidad of a plan on a credit card is assigned to the calendar month of its corte; plans without a card use calendar months directly. Every period row also breaks the total down per card in `cards` (`account_id` is `null` for plans without a card).
- `cycle`: when `account=` is a credit card id, columns are that card's real cycles, `key` is the ISO date of each cycle's corte, plans are filtered to that card, and the top-level `account` carries the card and its owner.

Month mode response shape:

```json
{
  "mode": "month",
  "account": null,
  "current_period_key": "2026-04",
  "current_total_cents": 400000,
  "periods": [
    {
      "key": "2026-04",
      "start": "2026-04-01",
      "end": "2026-04-30",
      "label": "2026-04-01 / 2026-04-30",
      "total_cents": 400000,
      "cards": [
        { "account_id": 3, "account_name": "Tarjeta oro", "total_cents": 300000 },
        { "account_id": null, "account_name": null, "total_cents": 100000 }
      ],
      "plans": [
        {
          "id": 1,
          "name": "Pantalla",
          "merchant": "Liverpool",
          "amount_cents": 300000,
          "payment_number": 1,
          "payments_total": 3,
          "remaining_payments": 2,
          "total_amount_cents": 900000,
          "round_up_monthly_payment": true,
          "category": {
            "id": 2,
            "name": "Meses",
            "scope": "global",
            "budget_treatment": "budgeted",
            "color": "#0f766e",
            "icon": "tag"
          },
          "member": null,
          "account": { "id": 3, "name": "Tarjeta oro", "account_type": "credit_card", "color": "#eab308" },
          "owner": { "id": 2, "name": "Ana", "color": "#dc2626" }
        },
        {
          "id": 2,
          "name": "Colchon sin tarjeta",
          "merchant": "Costco",
          "amount_cents": 100000,
          "payment_number": 1,
          "payments_total": 2,
          "remaining_payments": 1,
          "total_amount_cents": 200000,
          "round_up_monthly_payment": true,
          "category": {
            "id": 2,
            "name": "Meses",
            "scope": "global",
            "budget_treatment": "budgeted",
            "color": "#0f766e",
            "icon": "tag"
          },
          "member": null,
          "account": null,
          "owner": null
        }
      ]
    }
  ],
  "plans": []
}
```

Cycle mode for the card with corte `20` (`?account=3`):

```json
{
  "mode": "cycle",
  "account": {
    "id": 3,
    "name": "Tarjeta oro",
    "color": "#eab308",
    "cutoff_day": 20,
    "payment_due_day": 10,
    "owner": { "id": 2, "name": "Ana", "color": "#dc2626" }
  },
  "current_period_key": "2026-05-20",
  "current_total_cents": 300000,
  "periods": [
    {
      "key": "2026-05-20",
      "start": "2026-04-21",
      "end": "2026-05-20",
      "label": "2026-04-21 / 2026-05-20",
      "total_cents": 300000,
      "cards": [
        { "account_id": 3, "account_name": "Tarjeta oro", "total_cents": 300000 }
      ],
      "plans": []
    }
  ],
  "plans": []
}
```

Period `plans` rows in cycle mode have the same shape as in month mode. The top-level `plans` array lists every active plan with `total_amount_cents`, `round_up_monthly_payment`, `current_amount_cents`, `current_payment_number`, `payments_total`, `remaining_payments`, `projected_total_cents`, `monthly_amounts` (one `{ "period_end": ..., "amount_cents": ... }` per column), `category`, optional `member`, and the plan's `account` and `owner` payloads (both `null` for plans without a card).

### Credit card payments to avoid interest

`GET /api/credit-cards/interest-free-payment/?date=YYYY-MM-DD`

Returns one row per active credit card with two blocks resolved as of `date` (`as_of`, defaults to today): `closed_cycle` — the card's last closed cycle, its statement, what must be paid to avoid interest — and `open_cycle` — the cycle currently accumulating toward the next corte. Each block sums the cycle's purchases registered with that card (excluding transactions linked to installment plans) plus that cycle's MSI mensualidades for plans assigned to the card. Tracking-only transactions and plans are excluded. On the exact day of a corte the cycle is still open; it closes at the end of that day.

When the card has `payment_due_day`, each block includes the real bank `payment_due_date` and `safe_payment_date`, exactly three calendar days earlier. The deadline is the first configured due day after that cycle's corte; days `29`–`31` clamp to the target month's last valid day. Both fields are `null` on migrated cards that still need configuration.

`total_cents` is the sum of every card's `closed_cycle.total_cents`, and `owners` groups those statement totals by card owner (`member` is `null` for cards without owner; named owners sort first).

Response shape:

```json
{
  "total_cents": 250000,
  "as_of": "2026-05-10",
  "cards": [
    {
      "account_id": 3,
      "account_name": "Tarjeta oro",
      "account_color": "#eab308",
      "owner": { "id": 2, "name": "Ana", "color": "#dc2626" },
      "closed_cycle": {
        "start": "2026-03-21",
        "end": "2026-04-20",
        "payment_due_date": "2026-05-10",
        "safe_payment_date": "2026-05-07",
        "purchase_cents": 30000,
        "installment_cents": 200000,
        "total_cents": 230000
      },
      "open_cycle": {
        "start": "2026-04-21",
        "end": "2026-05-20",
        "payment_due_date": "2026-06-10",
        "safe_payment_date": "2026-06-07",
        "purchase_cents": 50000,
        "installment_cents": 200000,
        "total_cents": 250000
      }
    },
    {
      "account_id": 4,
      "account_name": "Tarjeta azul",
      "account_color": "#475569",
      "owner": null,
      "closed_cycle": {
        "start": "2026-04-06",
        "end": "2026-05-05",
        "payment_due_date": null,
        "safe_payment_date": null,
        "purchase_cents": 20000,
        "installment_cents": 0,
        "total_cents": 20000
      },
      "open_cycle": {
        "start": "2026-05-06",
        "end": "2026-06-05",
        "payment_due_date": null,
        "safe_payment_date": null,
        "purchase_cents": 40000,
        "installment_cents": 0,
        "total_cents": 40000
      }
    }
  ],
  "owners": [
    {
      "member": { "id": 2, "name": "Ana", "color": "#dc2626" },
      "total_cents": 230000,
      "account_ids": [3]
    },
    {
      "member": null,
      "total_cents": 20000,
      "account_ids": [4]
    }
  ]
}
```
