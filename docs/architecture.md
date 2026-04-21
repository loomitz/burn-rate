# Architecture

## Monorepo

Burn Rate is organized as a full monorepo:

- `backend/`: Django API and domain logic.
- `frontend/`: Vue mobile-first client.
- `docs/`: internal wiki and agentic history.
- `Dockerfile`: production image that builds Vue and runs Django/Gunicorn.
- `docker-compose.yml`: local PostgreSQL service plus the deployable web service.

## Backend

Django owns the data model, validation, period calculations, expected-charge generation, and budget summaries. Django REST Framework exposes CRUD endpoints and derived budget endpoints.

Business calculations live in `budget/services.py` so they can be tested without going through HTTP. Startup readiness checks for onboarding live in `budget/setup_services.py` and verify the configured database connection, migration state, and initial settings availability without writing environment configuration.

Authentication uses Django sessions with sliding renewal. Users are local to the installation. A fresh database is claimed from the web UI by the first admin; later users are created through admin-issued invitation links or, for local development, Django admin/the `create_local_user` management command.

Household members may optionally create/link a local user during member creation. Admin members use Django `is_staff`/`is_superuser` and can change settings, accounts, people, categories, and invitations. Non-admin users can access the app but cannot mutate those adjustment surfaces.

## Frontend

Vue 3 uses Composition API and Pinia. The frontend is online-only and calls the Django API through Vite's `/api` proxy in development. The local backend port is `8001` to avoid colliding with other local services that commonly use `8000`.

The first UI is optimized for phones:

- Bottom navigation with four product jobs: `Plan`, `Gastos`, `MSI`, and `Ajustes`.
- Quick expense capture and a separate recent movements tab inside `Gastos`.
- Budget cards with available balance, overspend state, and a full-screen click-through expense detail for the active category.
- `MSI` groups recurring subscription actions, automatic MSI progress, six-period payment projection, liquidation markers, and new commitment creation with a starting payment number for already-running purchases.
- `Ajustes` is shown to every authenticated user. Admin-only setup controls appear first for cutoff day, accounts, household people, and category setup; the theme preference panel sits just above the large logout action at the bottom of the screen.

The frontend applies resolved visual theme state at the document root with `data-theme`. The saved theme preference can be `auto`, `light`, or `dark`; `auto` follows `prefers-color-scheme`. The selected preference is persisted in browser `localStorage` under `burn-rate-theme`. Theme styling is centralized in `frontend/src/style.css` through CSS custom properties so the same Vue screens work in both dark and light mode.

Category icons are rendered from a curated local Lucide Vue catalog in `frontend/src/categoryIcons.ts`. The database stores only short icon keys; the frontend resolves those keys to imported Lucide components and falls back to `tag` for unknown values. The admin category form opens a searchable gallery so users can choose from the curated set without exposing an unbounded external icon browser.

## Deployment

Burn Rate deploys as one web app container. The Docker image compiles `frontend/` with Vite using `/static/` as the asset base, copies the generated `frontend/dist` folder into the Django runtime image, installs production backend dependencies, and starts Gunicorn through `docker-entrypoint.sh`.

Django serves the compiled SPA shell from `frontend/dist/index.html` for non-API routes. Static assets are collected from `frontend/dist/assets` into `backend/staticfiles` and served by WhiteNoise under `/static/`. API routes remain under `/api/`, Django admin remains under `/admin/`, and `/healthz/` returns a lightweight JSON liveness response for container healthchecks.

The container entrypoint can wait for Postgres, run migrations, and run `collectstatic` on startup. These behaviors are controlled by `WAIT_FOR_DB`, `RUN_MIGRATIONS`, and `COLLECT_STATIC`. Production host, CSRF, CORS, secure-cookie, SSL redirect, proxy-header, session-renewal, invitation TTL, and optional SMTP behavior are configured through environment variables documented in `.env.example`. Postgres stays private to the Compose network by default; only the app port is published, bound to `127.0.0.1` unless `APP_BIND` is changed for a VPN/reverse-proxy deployment.

## Data Flow

1. Vue checks onboarding status before showing login. If database, migrations, or initial settings are not ready, it shows a read-only checklist and retry action.
2. Vue checks bootstrap status after onboarding passes. If no users exist, the first admin claims the installation.
3. Users log in through `/api/auth/login/` or accept an invitation through `/api/invitations/accept/`.
4. Authenticated sessions are renewed through `/api/auth/refresh/` while the app is in active use.
5. Vue loads settings, members, categories, accounts, transactions, commitments, summary, and expected charges.
6. Budget summaries are calculated by Django on request.
7. Recurring expenses and installment plans generate expected charges for the current period, carrying both the internal commitment name and the merchant that will be used on the resulting expense.
8. A pending recurring expected charge can be confirmed into a real expense or dismissed for that period; confirmed expenses use the commitment merchant as `Transaction.merchant`.
9. MSI plans are projected through `/api/installments/projection/` so the frontend can show the current period payment, the next six period totals, the correct payment number for purchases that started before Burn Rate, and which plans finish in each projected cycle without turning MSI into manual payable rows.

## Documentation Flow

Every functional change must update this wiki and append `docs/agent-history.md`. The docs are intentionally versioned with code so future agents can understand current behavior before changing it.
