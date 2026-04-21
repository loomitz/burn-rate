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

Payload:

```json
{ "currency": "MXN", "cutoff_day": 20 }
```

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
  "monthly_budget_cents": 100000,
  "color": "#ca8a04",
  "icon": "paw"
}
```

Use `PATCH /api/categories/{id}/` with any of those fields plus `is_active` to edit an existing category without deleting historical transactions.

`icon` is a stable key from the frontend's curated local icon catalog. Existing categories default to `tag`; old keys such as `paw`, `bolt`, and `box` remain valid. The frontend can also normalize `lucide:`-prefixed values to the same local keys when the icon exists in the curated catalog.

`accounts` supports `cash`, `bank`, `debit_card`, and `credit_card`. It also accepts a user-facing `color` and `is_active` flag on create/update. `initial_balance_cents` is only valid for `cash`; non-cash accounts must use `0`.

Use `PATCH /api/accounts/{id}/` to edit an existing account without deleting historical transactions.

`recurring-expenses` uses `name` for the household label and `merchant` for the actual store/provider written to the confirmed automatic expense:

```json
{
  "name": "Internet casa",
  "merchant": "Telmex",
  "amount_cents": 59900,
  "category": 2,
  "account": 1,
  "start_date": "2026-04-21",
  "charge_day": 5,
  "is_active": true
}
```

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

Returns period, totals, breakdown, and category rows.

`family` is the one shared household budget. The older `global` value is accepted as an alias for `family`, but the UI should not present both because there is only one family per installation.

The category row includes:

- `color`
- `icon`
- `budget_cents`
- `spent_cents`
- `expected_cents`
- `consumed_cents`
- `available_cents`
- `percent_available`
- `is_overspent`

The frontend uses `category_id` from these rows to let the user click a category card and inspect the matching expense transactions for the active period.

## Expected Charges

`GET /api/expected-charges/?date=YYYY-MM-DD`

Returns generated pending charges from recurring expenses and installment plans.

`period=YYYY-MM` remains accepted for older callers, but the app should send a full `date` from the selected budget cycle so cutoff-based periods resolve correctly.

The frontend treats recurring charges as actionable commitments. Installment charges remain automatic budget commitments and are shown through the MSI projection endpoint instead of the `Pagar/Omitir` action list.

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

Creates a real `expense` transaction. The transaction `merchant` comes from the commitment `merchant`, not from the internal commitment `name`.

`POST /api/expected-charges/dismiss/`

Payload:

```json
{
  "source_type": "installment",
  "source_id": 1,
  "date": "2026-05-01"
}
```

Hides that generated charge for the period.

## Installment Projection

`GET /api/installments/projection/?date=YYYY-MM-DD&months=6`

Returns the current budget period plus the next `months` budget periods for active MSI plans. With `months=6`, the response contains seven period rows: current period and six future periods.

Response shape:

```json
{
  "current_period_key": "2026-04-20",
  "current_total_cents": 515500,
  "periods": [
    {
      "key": "2026-04-20",
      "start": "2026-03-21",
      "end": "2026-04-20",
      "total_cents": 515500,
      "plans": []
    }
  ],
  "plans": []
}
```

Each plan row includes current payment amount, payment number, total payments, remaining payments, category, optional member, and optional account.
