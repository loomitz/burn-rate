# Agent History

## 2026-04-21 - README en español, gitignore y capturas

Objetivo: cerrar la documentación pública de instalación con logo, capturas reales de la aplicación, flujo inicial e instrucciones de operación en español.

Archivos tocados:

- Ampliado `.gitignore` para cubrir secretos locales, entornos Python, builds de frontend, caches, logs y artefactos temporales sin ignorar `.env.example`.
- Reescrito `README.md` en español con logo, descripción, instalación Docker, flujo de primer administrador, invitaciones, variables de entorno, actualización por nuevo contenedor, seguridad esperada, desarrollo local, pruebas y estructura del proyecto.
- Agregadas capturas en `docs/screenshots/01-login.png`, `docs/screenshots/02-plan.png` y `docs/screenshots/03-invitaciones.png`.
- Actualizado este historial técnico.

Verificaciones:

- Capturas tomadas desde la app local con Playwright.
- Migración `budget.0007_invitation` aplicada en la base local usada por el servidor de desarrollo para poder capturar el panel de invitaciones sin error.
- `USE_SQLITE_FOR_TESTS=true uv run pytest` pasó en `backend/` con 37 tests.
- `pnpm test` pasó en `frontend/` con 8 tests.
- `pnpm build` pasó en `frontend/`.
- `docker compose config` pasó.
- `file docs/screenshots/*.png` confirmó que las tres capturas son PNG válidos.

## 2026-04-21 - Docker Install, Bootstrap Admin, Invitations, And Session Renewal

Objective: make Burn Rate installable from Docker with a first-admin welcome flow, admin-issued invitations, optional email delivery, and sliding sessions for VPN-style self-hosting.

Files touched:

- Added backend bootstrap, auth refresh, invitation model/API, password validation, token hashing, and staff-only mutation permissions.
- Updated frontend bootstrap/login state, first-admin claim screen, invitation acceptance screen, admin invitation panel, session renewal, and logout cleanup.
- Updated Docker/production settings so the app container serves Vue + Django, keeps Postgres private by default, and exposes `/healthz/`.
- Updated README, API/product/architecture docs, and this agent history.

Behavior after:

- Fresh installs show a claim screen and create the first admin from the browser when no users exist.
- Admins can create invitation links with email, full name, display name, optional admin role, and a custom message.
- Email sends only when public URL and SMTP credentials are configured; otherwise the copyable link remains available.
- Sessions renew with app activity, visibility return, and a 10-minute authenticated interval.
- `docker compose up --build app` builds the unified app and starts Postgres without publishing the database port.

Tests/checks:

- `USE_SQLITE_FOR_TESTS=true uv run pytest` passed in `backend/` with 37 tests.
- `USE_SQLITE_FOR_TESTS=true uv run python manage.py makemigrations --check --dry-run` reported no changes.
- `USE_SQLITE_FOR_TESTS=true uv run python manage.py check` passed.
- `pnpm test` passed in `frontend/` with 8 tests.
- `pnpm build` passed in `frontend/`.
- `docker compose config` passed.
- `docker compose build app` passed.
- `DJANGO_DEBUG=false ... uv run python manage.py check --deploy` passed with HTTPS/HSTS env enabled.
- Smoke-tested the built `burn_rate-app` image with DB wait/migrations disabled: `/healthz/` returned `{"status": "ok"}` and `/` returned the SPA HTML.

## 2026-04-21 - Single Container Deploy Surface

Objective: add the deploy/settings surface for running Burn Rate as one Django-served app.

Files touched:

- Added `Dockerfile` to build Vue with `/static/`, install backend production dependencies, run Gunicorn, and expose a container healthcheck.
- Added `docker-entrypoint.sh` to wait for Postgres, run migrations, collect static files, and then exec the app command.
- Added `.dockerignore` so local virtualenvs, build output, and caches do not enter the Docker context.
- Updated `docker-compose.yml` with an `app` service, production environment wiring, Postgres dependency health, private Postgres networking by default, and app healthcheck while preserving the `db` service.
- Updated `.env.example` with deploy/runtime variables.
- Updated `backend/pyproject.toml` with Gunicorn and WhiteNoise.
- Updated `backend/config/settings.py` for env helpers, production secret validation, WhiteNoise static handling, frontend dist static assets, CSRF/CORS environment variables, and secure deployment toggles.
- Updated `backend/config/urls.py` with `/healthz/` and a non-API SPA fallback.
- Updated README and architecture documentation.

Behavior before:

- Docker Compose only started Postgres.
- Django did not serve the compiled Vue app or expose a health endpoint.
- Production runtime dependencies for Gunicorn/WhiteNoise were not present.

Behavior after:

- `docker compose up --build app` can build and run the unified app container plus Postgres.
- Django serves API routes under `/api/`, admin under `/admin/`, Vue SPA routes from `frontend/dist/index.html`, and static assets through WhiteNoise under `/static/`.
- The app exposes `/healthz/` for Docker healthchecks.

Tests/checks:

- `uv lock` passed in `backend/` and added Gunicorn/WhiteNoise to `uv.lock`.
- `USE_SQLITE_FOR_TESTS=true uv run python manage.py test` passed in `backend/` with 28 tests.
- `USE_SQLITE_FOR_TESTS=true uv run python manage.py check` passed in `backend/`.
- `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,testserver USE_SQLITE_FOR_TESTS=true uv run python manage.py shell -c "from django.test import Client; r = Client().get('/healthz/'); print(r.status_code, r.json())"` returned `200 {'status': 'ok'}`.
- `docker compose config` passed.
- `pnpm exec vue-tsc -b --force` passed in `frontend/`.
- `pnpm exec vite build --base=/static/` passed in `frontend/` and produced `frontend/dist/index.html` with `/static/assets/...` references.
- `docker build --target backend-build -t burn-rate-backend-build-test .` passed.
- `docker build -t burn-rate-full-build-test .` passed.
- `docker run --rm -d --name burn-rate-static-health-test -e WAIT_FOR_DB=false -e RUN_MIGRATIONS=false -e COLLECT_STATIC=true -e DJANGO_SECRET_KEY=test-secret -e DJANGO_DEBUG=false -e DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost -p 18081:8000 burn-rate-full-build-test` started the app, `/healthz/` returned `{"status": "ok"}`, `/` returned the SPA HTML, a referenced `/static/assets/*.js` file returned 200, and `docker stop burn-rate-static-health-test` cleaned up the container.

## 2026-04-21 - Commitments Header Density And Settings Polish

Objective: simplify the monthly commitments layout and clean up the settings placement/details.

Files touched:

- Updated `frontend/src/App.vue` so the current-cycle commitment total is inline in the `Cargos del mes` header, the monthly pending title total is removed, the lower `Agregar cargo mensual` button is removed, the `Ajustes` nav icon is a gear, and the theme panel sits just above the final logout action.
- Updated `frontend/src/style.css` to remove the old summary-card styles, add the inline commitment summary, add more separation between the segmented selector and the monthly section title, make commitment row action buttons more transparent than their borders, and align the theme title/status on one row.
- Updated product documentation and this agent history entry.

Behavior before:

- The current-cycle commitment total appeared as a separate card under the header.
- The monthly pending total and helper text appeared in another card above the charge list.
- The replacement monthly title row repeated the pending count and total.
- `Agregar cargo mensual` appeared as an extra full-width button near the lower part of the monthly list.
- `Cargos mensuales` sat too close to the tab selector.
- The settings nav icon used a sun-like glyph.
- The theme panel was the first settings section and stacked `Tema` above the current theme state.

Behavior after:

- The current-cycle total is a compact inline header summary with amount first and count detail second.
- `Cargos mensuales` is a clean title without duplicate count/total text.
- The monthly add action only remains in the main header.
- The monthly section title has more breathing room after the selector.
- Pending-charge buttons use transparent fills with stronger borders.
- The `Ajustes` nav icon is a gear, and the theme panel is the penultimate section with `Tema` and the current state on one row.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.
- Browser validation at `http://127.0.0.1:5173/` confirmed `Cargos` uses an inline amount-first cycle summary, `Cargos mensuales` no longer repeats the pending count/total, pending-charge buttons use transparent fills with stronger borders, the `Ajustes` nav icon is a gear, and the theme panel is the penultimate settings section with title/status on one row.

## 2026-04-21 - Neutral Dark Background

Objective: make the dark theme background neutral instead of warm brown.

Files touched:

- Updated `frontend/src/style.css` dark theme tokens and remaining dark-only backgrounds to use neutral charcoal surfaces while keeping section accents.
- Updated product documentation and this agent history entry.

Behavior before:

- Dark mode used brown and espresso backgrounds across the page shell, cards, progress tracks, and budget hero.

Behavior after:

- Dark mode uses neutral charcoal backgrounds and surfaces; orange, teal, purple, and blue remain as functional accents.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.
- Browser validation at `http://127.0.0.1:5173/` confirmed the saved and resolved theme are `dark`, `--paper` is `#101010`, `--surface` is `#181818`, and the rendered app background is neutral charcoal.

## 2026-04-21 - Login Helper Removal And MSI Projection Detail

Objective: remove the login helper text and make the MSI projection show useful totals and liquidation timing.

Files touched:

- Updated `frontend/src/App.vue` to remove `Sin registro público` from login and replace the old MSI bar chart with a period-by-period payment timeline.
- Updated `frontend/src/style.css` for the new MSI projection timeline layout.
- Updated product and architecture documentation plus this agent history entry.

Behavior before:

- The login form showed `Sin registro público`.
- The MSI projection only showed seven unlabeled bars with period shorthand.

Behavior after:

- The login helper text is gone.
- The MSI projection shows total registered MSI purchases, each projected period amount, payment count per period, and liquidation markers when plans finish.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.
- Browser validation at `http://127.0.0.1:5173/` confirmed the login helper text is gone and the MSI projection shows `Pagos a meses registrados`, the registered total, period amounts, payment counts, and liquidation labels.

## 2026-04-21 - Login Copy And Theme Icon

Objective: update the login screen comments by using email/password wording and restoring a compact theme control before sign-in.

Files touched:

- Updated `frontend/src/App.vue` so the login form labels are `Email` and `Password`, the email input uses email autocomplete, and the login panel has a small icon-only theme cycle.
- Updated `frontend/src/stores/budget.ts`, `frontend/src/stores/api.ts`, and `backend/budget/serializers.py` so API login accepts `{ email, password }`, error copy matches the new login language, and legacy username payloads remain usable.
- Added API coverage in `backend/budget/tests/test_api.py`.
- Updated API, product, architecture documentation, and this agent history entry.

Behavior before:

- The login labels read `Usuario` and `Clave`.
- The login screen did not expose a theme control.
- The API login payload was documented as username/password only.

Behavior after:

- The login labels read `Email` and `Password`.
- A small icon in the login panel cycles `Auto`, `Light`, and `Dark`.
- Email/password login is supported by the backend.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.
- `USE_SQLITE_FOR_TESTS=true uv run python manage.py test` passed in `backend/` with 28 tests.
- Browser validation at `http://127.0.0.1:5173/` confirmed the login labels are `Email` and `Password`, the email field uses email autocomplete, the login theme icon cycles the saved theme preference, and `papa@example.com` can sign in successfully.

## 2026-04-21 - Settings Logout Placement

Objective: move logout out of the `Ajustes` header and make it a prominent final action in the settings screen.

Files touched:

- Updated `frontend/src/App.vue` to remove the square logout action from the settings header and add a large `Salir de Burn Rate` button at the end of `Ajustes`.
- Updated `frontend/src/style.css` for the large logout action and removed the old header-button style.
- Updated product and architecture documentation plus this agent history entry.

Behavior before:

- Logout was a small icon button in the top-right of `Ajustes`.

Behavior after:

- Logout is a large full-width action at the bottom of `Ajustes`, after theme and admin setup sections.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.
- Browser validation at `http://127.0.0.1:5173/` confirmed the settings header no longer has a logout action, the old `.settings-logout-action` button is gone, and `Salir de Burn Rate` is the last child in the `Ajustes` screen after theme and admin setup sections.

## 2026-04-21 - Theme Preference In Settings

Objective: move theme control into `Ajustes` and support `Auto`, `Light`, and `Dark` preferences.

Files touched:

- Updated `frontend/src/App.vue` to remove the theme action from login and main navigation, add a theme preference switch inside `Ajustes`, resolve `Auto` from `prefers-color-scheme`, and keep `Ajustes` visible to non-admin users while preserving admin-only setup controls.
- Updated `frontend/src/style.css` to replace the loose theme button styling with the settings theme switch.
- Updated product and architecture documentation plus this agent history entry.

Behavior before:

- Theme was a two-state icon action on login and in the main navigation.
- The app stored only `light` or `dark`.

Behavior after:

- Theme is controlled inside `Ajustes`.
- The preference options are `Auto`, `Light`, and `Dark`.
- `Auto` follows the browser or operating-system color scheme while still storing the user preference locally.
- Non-admin users can access `Ajustes` for theme/logout, but cannot see the administrative setup forms.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.
- Browser validation at `http://127.0.0.1:5173/` confirmed `Ajustes` contains the `Auto`, `Light`, and `Dark` switch, login and navigation no longer expose theme toggle buttons, `Auto` resolves from `prefers-color-scheme`, each option persists to `localStorage`, and a non-admin user sees theme/logout without admin setup sections.

## 2026-04-21 - Dark Theme Version

Objective: create a dark version of the Burn Rate application without changing the existing product flows.

Files touched:

- Updated `frontend/src/App.vue` to default to dark mode, persist the selected theme in browser storage, swap the login logo by theme, and add icon-only theme actions on login and in the main navigation.
- Updated `frontend/src/style.css` with dark theme tokens, dark surfaces for cards/forms/navigation/modals, adjusted status states, and theme action styling.
- Updated product and architecture documentation plus this agent history entry.

Behavior before:

- The app rendered only in the warm light palette.
- The dark brand logo asset existed but was not used by the app.

Behavior after:

- The app opens in a warm dark palette by default.
- Users can switch between dark and light mode, and the choice persists locally.
- The login screen uses the logo variant that matches the active theme.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- Browser validation at `http://127.0.0.1:5173/` confirmed the login screen renders in dark mode by default, the dark logo appears, and the theme action toggles the root `data-theme` between `dark` and `light`.

## 2026-04-21 - Plan Top And Category Card Spacing

Objective: tighten the Plan top area and keep category progress bars visually centered after adding the `+` shortcut.

Files touched:

- Updated `frontend/src/style.css` so the Plan screen uses a smaller cycle selector, less vertical space between top elements, and less space before category cards.
- Updated category card spacing so the title area still reserves room for the `+` action while the progress bar spans the normal card width.
- Updated product documentation and agent history.

Behavior before:

- The cycle selector text felt oversized.
- The Plan top section had too much vertical space before `Detalle por categoría`.
- Category progress bars ended before the `+` action column, making them feel off-center.

Behavior after:

- The cycle selector is more compact.
- The Plan top area sits closer to the category cards.
- Category progress bars use the card width while the titles remain left-aligned and clear of the `+` button.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.
- Browser validation at 401x693 confirmed the cycle select uses 14px text, the gap from the top section to the category ledger is 16px, and the `Internet` progress bar extends into the horizontal `+` action column while its title line remains left-aligned.

## 2026-04-21 - Current Cycle As Selector Endpoint

Objective: keep the Plan cycle selector historical and make the current cycle the last option.

Files touched:

- Updated `frontend/src/App.vue` so cycle options include 12 past cycles and the current cycle as the final option.
- Disabled cycle arrow navigation before the oldest listed cycle and after the current cycle.
- Updated `frontend/src/style.css` for disabled cycle arrows.
- Updated product documentation and agent history.

Behavior before:

- The cycle selector included future cycles after the current one.
- The next arrow could move Plan into a future cycle.

Behavior after:

- The current cycle appears as the last option in the selector.
- The UI no longer allows navigating into future cycles.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.
- Browser validation at 401x693 confirmed the selector has 13 options, no future options, the current cycle is the final option, and the next arrow is disabled while on the current cycle.

## 2026-04-21 - Category Card Expense Shortcut

Objective: add direct expense shortcuts to each Plan category card.

Files touched:

- Updated `frontend/src/App.vue` so each category card has a separate `+` action that opens expense capture with that category preselected.
- Kept the main category card action opening the category detail.
- Updated `frontend/src/style.css` so the `+` action follows each category color.
- Updated product documentation and agent history.

Behavior before:

- Category cards only opened their detail screen.
- Registering a category expense required opening the detail or going through the full expense form.

Behavior after:

- Tapping the card body opens the detail.
- Tapping the colored `+` starts a new expense with that category already selected.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.
- Browser validation at 401x693 confirmed there is one `+` action per category card, the card body still opens the category detail, and the `+` opens `Gastos` with that category selected.

## 2026-04-21 - Commitments Summary Simplification

Objective: simplify the top summary in `Cargos del mes`.

Files touched:

- Updated `frontend/src/App.vue` to replace the large commitments hero with a compact pending-total strip.
- Updated `frontend/src/style.css` for the compact commitments summary.
- Updated product documentation and agent history.

Behavior before:

- The commitments view repeated total, count, and two internal metric cards before the tabs.

Behavior after:

- The top summary shows only the pending cycle total and compact monthly/MSI counts.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.
- Browser validation at 401x693 confirmed the compact summary renders, the old `Cargos planeados` hero is gone, and the view still shows the commitments tabs below.

## 2026-04-21 - Plan Top Redesign

Objective: simplify the Plan top area while leaving `Detalle por categoría` and everything below it intact.

Files touched:

- Updated `frontend/src/App.vue` to remove the general `Registrar gasto` button from Plan.
- Replaced the visible `Ciclo del plan` label with an accessible-only select label and a compact top section showing `Plan de casa` plus the formatted cycle range.
- Updated `frontend/src/style.css` for the new top section and compact cycle controls.
- Updated product documentation and agent history.

Behavior before:

- Plan opened with a large `Registrar gasto` button and a visible `Ciclo del plan` label above the selector.

Behavior after:

- Plan opens with a cleaner top section and cycle controls only.
- `Detalle por categoría` remains the first functional budget area below the top controls.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.
- Browser validation at 401x693 confirmed the general `Registrar gasto` button is gone, the visible `Ciclo del plan` title is gone, and `Detalle por categoría` still starts the functional budget area.

## 2026-04-21 - Merchant Concept Suggestions

Objective: turn the expense merchant/concept input into a reusable suggestion flow backed by the database.

Files touched:

- Added `MerchantConcept` in `backend/budget/models.py`, registered it in admin, and created migration `0006_merchantconcept.py` with a backfill from existing expense merchants.
- Added a read-only `/api/merchant-concepts/` endpoint and serializer.
- Updated transaction saving so new expense merchants create or reuse catalog entries automatically.
- Updated `frontend/src/stores/budget.ts` and `frontend/src/App.vue` so the expense form loads concepts and shows filtered suggestions while typing.
- Updated `frontend/src/style.css` for the merchant suggestion list.
- Updated API, domain, product docs, and agent history.

Behavior before:

- The merchant/concept field was a plain required text input.
- Reusing a prior merchant required typing it again from memory.

Behavior after:

- Saving a new expense records its merchant/concept in the database.
- The merchant/concept input shows saved suggestions filtered by the typed text and fills the input when selected.

Tests/checks:

- `USE_SQLITE_FOR_TESTS=true uv run python manage.py makemigrations --check --dry-run` reported no model drift.
- `USE_SQLITE_FOR_TESTS=true uv run python manage.py test` passed with 27 tests.
- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.
- `uv run python manage.py migrate` applied `budget.0006_merchantconcept` to the local database.
- `DB_PORT=5433 uv run python manage.py migrate budget 0006` applied the same migration to the database used by the active IAB backend.
- Browser validation at 401x693 confirmed typing `super` in the merchant field shows saved suggestions.

## 2026-04-21 - Expense Final Details Block

Objective: merge the merchant and amount fields into the final expense registration block.

Files touched:

- Updated `frontend/src/App.vue` so merchant, amount, date, and note live together in one final `Datos del gasto` section.
- Updated `frontend/src/style.css` to replace the old optional date/note styling with the final expense details block.
- Updated product documentation and agent history.

Behavior before:

- Merchant and amount appeared as a separate block at the top of the expense form.
- The final always-expanded section was titled `Fecha y nota`.

Behavior after:

- Category and account selection stay first.
- Merchant, amount, date, and note are fused into the final `Datos del gasto` block before saving.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.
- Browser validation at 401x693 confirmed the form starts with category/account selection, the old `Fecha y nota` title is gone, and merchant, amount, date, and note are grouped under `Datos del gasto` before saving.

## 2026-04-21 - Plan Header Cleanup

Objective: simplify Plan header actions and remove helper copy that no longer adds value.

Files touched:

- Updated `frontend/src/App.vue` so `Registrar gasto` appears above the cycle controls.
- Removed the category ledger helper sentence.
- Removed logout from the Plan header and added it to the Ajustes header.
- Updated `frontend/src/style.css` so cycle controls use a warmer orange treatment and the Ajustes logout action uses the settings color.
- Updated product documentation and agent history.

Behavior before:

- The cycle selector appeared above the primary expense action.
- Plan included a logout action in the header.
- Category detail included helper copy below the heading.

Behavior after:

- `Registrar gasto` is the first Plan action after the title.
- Cycle controls sit below the expense action with an orange tint.
- Logout is only available from `Ajustes`.
- Category detail heading is cleaner.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.

## 2026-04-21 - Plan Primary Expense Action

Objective: keep the expense action visible at the start of Plan and remove the redundant commitments button from the summary.

Files touched:

- Updated `frontend/src/App.vue` so `Registrar gasto` appears immediately after the cycle selector.
- Removed `Ver cargos del mes` from the Plan summary disclosure.
- Removed now-unused Plan action helper/style code.
- Updated product documentation and agent history.

Behavior before:

- `Registrar gasto` lived inside the collapsed summary area.
- The summary also contained a `Ver cargos del mes` button.

Behavior after:

- `Registrar gasto` is a primary top-level action at the start of the Plan view.
- The summary disclosure only contains summary information and totals.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.

## 2026-04-21 - Expense Form Header Removal and Favicon Asset

Objective: simplify the expense capture form and point the browser favicon at the supplied favicon asset.

Files touched:

- Copied `Logos/favicon.svg` into `frontend/src/assets/brand/favicon.svg`.
- Updated `frontend/index.html` so the favicon points to `favicon.svg`.
- Removed the `Gasto rápido / ¿Qué salió de la casa? / Hoy` hero block from the expense capture form.
- Removed the now-unused expense hero styles from `frontend/src/style.css`.
- Updated product documentation and agent history.

Behavior before:

- The expense form had an extra hero block before the merchant and amount fields.
- The favicon pointed to `burn-rate-logo-white.svg`.

Behavior after:

- The expense form starts directly with merchant and amount.
- The favicon uses the asset named `favicon.svg`.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.

## 2026-04-21 - Plan Cycle View

Objective: make the Plan screen cycle-based, always whole-house, and card-first.

Files touched:

- Updated `frontend/src/App.vue` so Plan uses a complete budget-cycle selector with previous/next controls instead of an arbitrary date input.
- Removed the Plan scope selector; the Plan screen now always requests the `total` whole-house budget scope.
- Moved category status cards above attention and summary so budget cards are prioritized.
- Hid the large Plan summary behind a `Mostrar resumen` disclosure.
- Updated the attention panel styling so it uses the same card language as category rows.
- Updated `frontend/src/stores/budget.ts` and `backend/budget/views.py` so expected charges can be fetched with a full cycle date.
- Updated API/product documentation and agent history.

Behavior before:

- Plan used a date input plus a `Toda la casa / Por persona` selector.
- The large summary panel dominated the top of the Plan screen before users reached category status cards.
- Expected charges were requested by calendar month, which could point to the wrong cutoff-based cycle.

Behavior after:

- Plan selects complete cutoff cycles and always shows the whole-house `total` scope.
- Category cards are the first budget status surface after cycle selection.
- Attention and summary are secondary; summary opens only when the user asks for it.
- Expected charges resolve from the selected cycle date.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.
- `USE_SQLITE_FOR_TESTS=true uv run python manage.py test` passed in `backend/` with 26 tests.

## 2026-04-21 - Expense Account Picker Search

Objective: apply the same searchable card picker pattern to account selection in expense capture.

Files touched:

- Updated `frontend/src/App.vue` so expense accounts use a search field and scrollable filtered card list instead of quick cards plus a dropdown.
- Updated `frontend/src/style.css` so the account picker has bounded vertical scroll and keeps account color styling.
- Updated product documentation and agent history.

Behavior before:

- Account selection showed only quick account cards and relied on a separate dropdown for the full account list.

Behavior after:

- Account selection is a single card-based picker with search, internal scroll, and account colors.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.

## 2026-04-21 - Expense Capture Picker Refinement

Objective: make the expense capture category and account selection easier to scan on mobile.

Files touched:

- Updated `frontend/src/App.vue` so category selection uses a searchable scrollable card list instead of quick cards plus a dropdown.
- Updated `frontend/src/App.vue` so account quick cards expose each account's assigned color.
- Updated `frontend/src/App.vue` so date and note fields are always expanded.
- Updated `frontend/src/style.css` for the scrollable picker, account color cues, and expanded date/note section.
- Updated product documentation and agent history.

Behavior before:

- Category capture mixed four cards with a full dropdown, which could grow awkwardly and duplicated the choice model.
- Account cards did not show the account colors already configured in the app.
- Date and note were hidden behind a collapsible disclosure.

Behavior after:

- Category capture is a single card-based picker with a search box and bounded vertical scroll.
- Account cards show a color dot and tinted card state from the account color.
- Date and note are visible without opening a disclosure.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.

## 2026-04-21 - White Monochrome Favicon

Objective: switch the favicon to the white monochrome Burn Rate mark.

Files touched:

- Updated `frontend/index.html` so the favicon points to `burn-rate-logo-white.svg`.
- Updated product documentation and agent history.

Behavior before:

- The favicon used the official light logo variant.

Behavior after:

- The favicon uses the official white monochrome logo variant while the login screen keeps the light logo.

Tests/checks:

- `pnpm build` passed in `frontend/`.

## 2026-04-21 - Category Detail Expense Shortcut

Objective: add a direct expense action to the category budget detail and fix the odd contrast on the period chip.

Files touched:

- Updated `frontend/src/App.vue` so a category detail can open the expense capture flow with that category preselected.
- Updated `frontend/src/style.css` so the detail header has room for the new action and the context chip uses the active category palette instead of the plan green.
- Updated product documentation and agent history.

Behavior before:

- From a category detail, users had to leave the detail view and choose the category again in `Gastos`.
- The detail context chip mixed the red category accent with the green plan background, which made the contrast feel inconsistent.

Behavior after:

- The category detail header includes a `Gasto` action that opens `Gastos` with the current category already selected.
- The context chip now uses a light tint of the active category color with darker category text and border.

Tests/checks:

- `pnpm build` passed in `frontend/`.
- `pnpm test` passed in `frontend/` with 5 tests.
- Browser-validated at 443x693: opened the Gas category detail, confirmed the new button renders in the header, clicked it, and confirmed the expense form has Gas selected.

## 2026-04-21 - Official Logo Integration

Objective: replace the temporary Burn Rate logo with the official logo set supplied in `Logos/`.

Files touched:

- Added the official logo variants under `frontend/src/assets/brand/`.
- Updated `frontend/src/App.vue` to use `burn-rate-logo-light.svg` on the login screen.
- Updated `frontend/index.html` so the favicon uses the official light logo variant.
- Updated `frontend/src/style.css` so the taller official logo fits the login panel on mobile and desktop.
- Removed the old temporary `frontend/src/assets/burn-rate-logo.svg`.
- Updated product documentation and agent history.

Behavior before:

- The login screen and favicon used a temporary custom SVG logo with a horizontal wordmark.

Behavior after:

- The login screen and favicon use the official Burn Rate logo.
- The official dark, black, and white variants are versioned with the frontend for future surfaces.
- The login layout reserves space for the vertical official mark without crowding the form on narrow screens.

Tests/checks:

- Rendered the supplied logo variants to PNG with `rsvg-convert` to inspect proportions and contrast.
- `pnpm --prefix frontend test` passed with 5 tests.
- `pnpm --prefix frontend build` passed.
- Browser-validated the login screen at 390x844 and 320x720 with no horizontal overflow and no vertical overflow.

Decisions:

- Use `light-mode.svg` as the current primary logo because the app interface is light.
- Keep the other supplied variants in the frontend asset tree even though the current UI does not yet have dark or monochrome surfaces.

## 2026-04-21 - Sequential Skill Chain Verification

Objective: verify the harden, adapt, normalize, arrange, and polish chain after the final agent handoff.

Files touched:

- Updated `backend/budget/views.py`, `backend/budget/tests/test_api.py`, and `frontend/src/stores/budget.ts` so unauthenticated `/api/auth/me/` returns `{ "user": null }` instead of a console-visible 403 during normal login bootstrap.
- Updated `frontend/src/App.vue` to fix the remaining visible Spanish accent inconsistencies found during final copy verification and remove redundant icon-search autofocus.
- Updated `frontend/src/style.css` so shared segmented controls preserve 44px touch targets.
- Updated `docs/agent-history.md` with this final verification note.

Behavior after:

- Fresh unauthenticated loads no longer produce a console-visible 403 for the normal session check.
- Remaining visible copy such as `Atención`, `categoría`, `categorías`, and `Gasto rápido` is consistently accented in the active app UI.
- Segmented controls now meet the 44px touch baseline at 320px after the final browser check exposed a 36px height.
- The icon gallery keeps programmatic focus without triggering a redundant browser autofocus info message.

Tests/checks:

- `pnpm --prefix frontend test` passed with 5 tests.
- `pnpm --prefix frontend build` passed.
- `USE_SQLITE_FOR_TESTS=true uv run python manage.py test` passed with 26 backend tests.
- Browser-validated `Plan`, `Gastos`, and `Ajustes` at 320px with no horizontal overflow and no visible interactive target below 44px.

Decisions:

- Keep the final orchestration changes limited to copy consistency and a shared touch-target fix.

## 2026-04-21 - Final polish pass

Objective: tighten the last visible rough edges after the layout and normalization work.

Files touched:

- Refined visible Spanish copy in the frontend for accent, capitalization, and punctuation consistency.
- Added reduced-motion-aware scrolling plus shared button/segment/icon hover, active, and focus polish in the frontend stylesheet.
- Added this polish entry to the agent history.

Behavior before:

- A few labels, status strings, and helper texts still mixed accented and unaccented Spanish.
- Shared controls had usable states, but they felt a little flat and inconsistent at the edges.
- View changes always used smooth scrolling, even when reduced motion is preferred.

Behavior after:

- Visible copy now reads consistently in Spanish across the main household flow.
- Shared buttons, segmented controls, bottom nav, icon tiles, and color picks have lighter state feedback and steadier micro-alignment.
- View transitions respect `prefers-reduced-motion` while keeping the default motion for everyone else.

Tests/checks:

- `pnpm --prefix frontend test` passed.
- `pnpm --prefix frontend build` passed.

Decisions:

- Kept the scope to micro-detail polish only.
- Left the established layout and component structure intact.

## 2026-04-21 - Layout rhythm and alignment pass

Objective: improve spacing rhythm, hierarchy, and alignment after the harden/adapt/normalize steps.

Files touched:

- Updated shared layout rhythm in the frontend stylesheet.
- Added this arrange entry to the agent history.

Behavior before:

- Several sections used the same spacing weight everywhere.
- Section titles, summary rows, category cards, and the bottom nav felt flatter than the rest of the UI.

Behavior after:

- Section headers now align more intentionally and read as clearer title/subtitle groups.
- The plan hero, category cards, attention panel, setup tabs, icon gallery, and bottom nav have more deliberate breathing room and internal hierarchy.
- Mobile plan actions collapse cleanly while wider screens keep a denser split action layout.

Tests/checks:

- `pnpm --prefix frontend test` passed.
- `pnpm --prefix frontend build` passed.

Decisions:

- Kept the scope limited to spatial rhythm and alignment only.
- Reused existing spacing tokens and component structure instead of introducing new surfaces.

## 2026-04-20 - Initial monorepo implementation

Objective: create the first working Burn Rate monorepo from the approved plan.

Files touched:

- Created backend Django project in `backend/`.
- Created Vue frontend in `frontend/`.
- Created internal wiki in `docs/`.
- Added root setup files.

Behavior before:

- The project folder only contained `.env`.

Behavior after:

- Django API models household members, global and personal categories, budget allocations, accounts, transactions, recurring expenses, and installment plans.
- Budget period defaults to day 21 through day 20.
- Budget summary shows available budget, expected charges, and negative overspend.
- Vue app supports login, mobile navigation, budget view, expense capture, accounts, commitments, and settings.
- Expected charges can be confirmed into real expenses or dismissed.
- Category uniqueness is enforced separately for global categories and per-person personal categories.
- Recurring charge dates are calculated inside the active budget period, including days after the cutoff.

Tests/checks:

- `USE_SQLITE_FOR_TESTS=true uv run python manage.py test` passed with 16 tests.
- `uv run python manage.py check` passed.
- `pnpm test` passed with 2 tests.
- `pnpm build` passed.
- Applied migrations to the Postgres database configured in `.env`.
- Applied follow-up migration `budget.0002` for category uniqueness constraints.

Decisions:

- Household members are budget people, not tenants.
- Categories determine whether a charge is global or personal.
- MSI consumes only the monthly payment in each period.
- Documentation updates are mandatory for future functional changes.
- Local Django dev server uses port `8001` because `8000` was already occupied by an existing Beagle service.

## 2026-04-20 - Account types and member access

Objective: simplify account types and add explicit access/admin choices when creating household members.

Files touched:

- Updated backend account validation, member serializer access fields, and admin-only unsafe permissions for settings/member/category changes.
- Updated Vue settings and account forms.
- Updated docs for account types, access rules, and admin permissions.

Behavior before:

- Accounts allowed a generic `other` type.
- Any account type could receive an initial balance.
- Household members could be linked to a user only by passing an existing user id.
- Settings/person/category mutations were available to any authenticated user.

Behavior after:

- Account type `other` is removed.
- Only `cash` accounts may have `initial_balance_cents`.
- Creating a household member asks whether they have app access and whether that access is admin.
- Admin access maps to Django staff/superuser permissions.
- Non-admin users cannot change settings, people, or categories through the API.
- The settings tab is hidden for non-admin users in the frontend.

Tests/checks:

- Applied migration `budget.0003`.
- `USE_SQLITE_FOR_TESTS=true uv run python manage.py test` passed with 21 tests.
- `pnpm test` passed with 2 tests.
- `pnpm build` passed.

Decisions:

- Admin access uses Django built-in staff/superuser flags instead of a new role table.
- Cash is the only account type with an initial balance because Burn Rate is not a bank reconciliation tool.

## 2026-04-20 - Image-based category and demo data seed

Objective: create the categories and people from the provided spreadsheet image and add representative dummy data for testing the app.

Files touched:

- Added `seed_demo_data` management command.
- Added tests for seed idempotency and demo-data coverage.
- Updated domain documentation.

Behavior before:

- The database only had manually created data.
- There was no repeatable way to create app-wide sample data.

Behavior after:

- Running `python manage.py seed_demo_data` creates the spreadsheet categories, the household members `Oli`, `Mama`, and `Papa`, personal budget categories, all account types, transactions, recurring expenses, and MSI plans.
- The seed can be run repeatedly without duplicating the demo records.

Tests/checks:

- Ran `uv run python manage.py seed_demo_data` against the local configured database.
- Verified local counts: 3 members, 10 global categories, 3 personal categories, 4 accounts, 7 transactions, 3 recurring expenses, and 2 installment plans.

Decisions:

- The last three rows of the image are treated as people.
- Each person gets a personal `Gastos generales` category using the image amount as monthly budget.
- Spreadsheet labels were normalized to user-facing category names: `Gas`, `Internet`, `Mantenimiento`, and title-case names.

## 2026-04-20 - Expanded Current-Period Demo Data

Objective: add enough dummy expenses, subscriptions, and MSI records to verify the complete app from the current IAB date.

Files touched:

- Expanded `seed_demo_data` management command.
- Updated seed coverage tests.
- Updated domain documentation.

Behavior before:

- Demo data existed mostly in the next budget period.
- The current IAB date, `2026-04-20`, had limited visible data.
- The seed had fewer examples of pending versus confirmed commitments.

Behavior after:

- The seed clears old demo transactions and recreates a clean idempotent dataset.
- The current period, `2026-03-21` through `2026-04-20`, includes income, transfers, family expenses, personal expenses, confirmed subscription payments, confirmed MSI payments, pending subscriptions, and pending MSI.
- The next period still includes extra expenses for forward testing.
- Local seeded counts are 20 demo transactions, 5 recurring expenses, and 3 MSI plans.

Tests/checks:

- Ran `uv run python manage.py seed_demo_data` against the local configured database.
- Verified expected current-period charges: Oli recurrente, Seguro perros, Streaming Mama, Yoga mensual, and MSI personal Mama.
- `USE_SQLITE_FOR_TESTS=true uv run python manage.py test` passed with 22 tests.
- `pnpm test` passed with 2 tests.
- `pnpm build` passed.

Decisions:

- Seed data now targets the current visible budget period so the app can be tested immediately after reload.
- Confirmed commitment payments are real `expense` transactions linked to their recurring or MSI source.

## 2026-04-20 - Merge Global And Family Concepts

Objective: remove the duplicate user-facing distinction between `Global` and `Familia`.

Files touched:

- Updated budget summary scope handling.
- Updated Vue scope selector and labels.
- Updated backend tests and wiki docs.

Behavior before:

- The budget screen showed both `Familia` and `Global`.
- `Familia` meant an aggregate of global plus personal categories.
- `Global` meant shared household categories.

Behavior after:

- The UI shows `Familia` for the shared household budget and `Persona` for personal budgets.
- `Global` is no longer a visible filter label.
- The API treats `global` as a backwards-compatible alias for `family`.
- A technical `total` scope remains available for aggregate reports across family and personal categories.

Tests/checks:

- `USE_SQLITE_FOR_TESTS=true uv run python manage.py test` passed with 22 tests.
- `pnpm test` passed with 2 tests.
- `pnpm build` passed.

Decisions:

- One installation has one family, so `Familia` is the correct user-facing name for the shared category scope.

## 2026-04-20 - Category Expense Detail And Access Demo Users

Objective: make each budget category card open its expense detail and identify both the merchant and the user who registered each expense.

Files touched:

- Added a transaction `merchant` field and serializer/API validation for expense names.
- Updated confirmed expected-charge creation to preserve the charge name as the merchant.
- Updated Vue budget and expense screens to show merchant and registered-by user.
- Updated demo seed data to create access users for Papa and Mama while keeping Oli without login access.
- Updated backend tests, API docs, domain docs, and architecture notes.

Behavior before:

- Category cards only showed budget totals.
- Expenses had amount, category, account, date, and note, but no first-class merchant/name field.
- The UI did not show who registered a movement.
- Demo household members existed as budget people but did not model the requested access split.

Behavior after:

- Clicking a category card in `Presupuesto` shows the period expenses for that category.
- Expense capture requires `Comercio o nombre`.
- Expense rows show merchant/name and `created_by_username`.
- The demo seed creates `papa` as admin, `mama` as normal user, and `Oli` as a non-login household member.

Tests/checks:

- Applied migration `budget.0004`.
- Ran `uv run python manage.py seed_demo_data` against the local configured database.
- `USE_SQLITE_FOR_TESTS=true uv run python manage.py test` passed with 22 tests after fixing the seed fallback merchant name.
- `pnpm test` passed with 2 tests.
- `pnpm build` passed.
- Verified `/api/transactions/?category=1` returns merchant and `created_by_username`.
- Verified `/api/household-members/` returns Papa as admin, Mama as non-admin, and Oli without access.

Decisions:


## 2026-04-21 - Frontend hardening pass

Objective: harden the mobile-first family budget UI against real-world data, repeated actions, and partial backend failures without changing the flow or visual direction.

Files touched:

- `frontend/src/App.vue`
- `frontend/src/stores/api.ts`
- `frontend/src/stores/budget.ts`
- `frontend/src/style.css`
- `frontend/src/stores/api.test.ts`

Behavior after:

- API errors now surface friendlier messages, including login, permission, not-found, and rate-limit cases.
- Bootstrap no longer treats a normal unauthenticated session as an error state on the login screen.
- Period refreshes use a single store fetch path and ignore stale in-flight loads.
- Expense, account, person, category, recurring, and MSI forms now trim text and block empty or invalid submissions before they hit the API.
- Personal budget view now asks for a selected person instead of showing stale family data.

## 2026-04-21 - Frontend adapt pass

Objective: tighten the existing mobile-first UI for 320-390px phones, tablets, desktop, and short-height contexts without changing the product flow.

Files touched:

- `frontend/src/style.css`
- `docs/agent-history.md`

Behavior after:

- The login shell and main app shell now use dynamic viewport height so the interface behaves better on mobile browser chrome and short landscape windows.
- The plan filter now reflows into a compact grid on narrow screens instead of relying on horizontal scrolling.
- Plan totals, section headers, budget summary text, category rows, and commitment rows now wrap more safely on small screens.
- The category detail hero, commitment summary, and icon gallery modal keep their touch targets and content readable while fitting smaller widths and heights.

Tests/checks:

- `pnpm --prefix frontend test` passed with 5 tests.
- `pnpm --prefix frontend build` passed.
- Large currency values, long labels, and dense rows have more room to wrap instead of overflowing cards.

Tests/checks:

- `pnpm test` passed with 5 tests.
- `pnpm build` passed.

- Merchant/name is required for `expense` and expected-charge transactions at validation time, while the database column remains blank-compatible for old rows.
- `created_by` remains server-controlled from the authenticated session.

## 2026-04-20 - Automatic MSI Projection View

Objective: stop showing MSI as manual commitments and add a grouped view for current and future MSI pressure.

Files touched:

- Added backend projection services for budget periods and MSI payments.
- Added `GET /api/installments/projection/`.
- Updated Vue store and commitments screen.
- Updated backend tests and wiki docs.

Behavior before:

- MSI generated expected charges and appeared in the commitments action list with `Pagar` and `Omitir`.
- The commitments feed listed MSI plans, but did not show how the monthly load changes over future periods.

Behavior after:

- MSI still affects the budget automatically as expected spending.
- The commitments action list only shows recurring subscriptions.
- MSI appears in its own grouped panel with the current period total, per-plan current payment, remaining payments, and current plus six future budget periods.

Tests/checks:

- `USE_SQLITE_FOR_TESTS=true uv run python manage.py test` passed with 24 tests.
- `pnpm test` passed with 2 tests.
- `pnpm build` passed.
- Verified `/api/installments/projection/?date=2026-04-20&months=6` returns current and future MSI period totals from local seeded data.

Decisions:

- MSI projection is calculated server-side to respect the configured cutoff day and final-payment remainder.
- MSI confirmation remains supported at the service/API level for compatibility, but the main UI no longer presents MSI as a manual payable commitment.

## 2026-04-20 - Bottom Navigation Dead Space Fix

Objective: fix the bottom navigation area that made the fourth button feel inactive.

Files touched:

- Updated the Vue navigation click handler.
- Updated bottom navigation CSS.
- Updated agent history.

Behavior before:

- Non-admin users saw four navigation items, but the bottom bar still reserved five grid columns.
- On mobile, navigation labels were hidden, making the `Compromisos` button hard to distinguish.
- Switching tabs did not reset scroll position, so a tab change could look like no visible change if the user was lower on the page.

Behavior after:

- The bottom bar uses the actual visible item count, so there is no dead tap area.
- Mobile navigation keeps compact labels visible.
- Selecting any tab scrolls to the top of the new section.

Tests/checks:

- `pnpm test` passed with 2 tests.
- `pnpm build` passed.

Decisions:

- Keep icon plus text labels visible on phone because this app has several similarly weighted sections and ambiguity hurts navigation.

## 2026-04-20 - Commitment View Clarity And MSI Progress

Objective: make the `Compromisos` screen visibly useful and add progress tracking for months-without-interest payments.

Files touched:

- Updated the Vue commitments screen.
- Updated commitment/MSI CSS.
- Updated agent history.

Behavior before:

- `Compromisos` opened into separated lists without a clear period summary.
- MSI showed payment numbers as plain text only.
- The user could not quickly see total commitments, current MSI burden, or progress through each MSI plan.

Behavior after:

- `Compromisos` starts with a period summary showing total commitments, pending subscriptions, and automatic MSI.
- Subscriptions remain in a separate actionable section.
- MSI plans show current payment amount, `Pago X de Y`, remaining payments, and a visual progress bar.
- The MSI projection remains visible as current period plus the next six periods.

Tests/checks:

- `pnpm test` passed with 2 tests.
- `pnpm build` passed.
- Verified local API data for the screen: 4 current expected charges, 227900 cents in pending subscriptions, 515500 cents in current MSI, 7 projected periods, and 3 MSI plans.

Decisions:

- The screen should make the section change obvious from the first viewport, not rely on the user scrolling to discover MSI details.

## 2026-04-20 - Pencil Mobile Design Application

Objective: apply the active Pencil mobile designs to the Vue frontend navigation and visual system.

Files touched:

- Updated `frontend/src/App.vue`.
- Replaced the mobile-first styling in `frontend/src/style.css`.
- Updated product and architecture documentation.

Behavior before:

- The main navigation exposed `Presupuesto`, `Gastos`, `Cuentas`, `Compromisos`, and `Ajustes`.
- Cuentas was a standalone main view.
- Gastos and Compromisos used long stacked sections instead of Pencil-style subtabs.
- Category detail opened as an inline panel below the budget cards.

Behavior after:

- The main navigation follows the Pencil map: `Plan`, `Gastos`, `MSI`, and `Ajustes`.
- `Cuentas` now lives inside admin-only `Ajustes`.
- `Gastos` has `Registro de gasto` and `Movimientos` tabs.
- `MSI` groups subscriptions, MSI progress/projection, and a Pencil-style new commitment form.
- Category detail opens as a full mobile screen with a back action and period summary.
- The visual system uses the Pencil colors, 8px cards, segmented controls, dark summary panels, and compact fixed bottom navigation.

Tests/checks:

- `pnpm test` passed with 2 tests.
- `pnpm build` passed.
- Browser-validated mobile views at 390x844 with Playwright: login, Plan, Gastos registration, Gastos movements, MSI subscription tab, MSI tab, new MSI form, Ajustes, and category detail.

Decisions:

- Keep the existing backend/API contract unchanged and implement the Pencil behavior as a frontend navigation and presentation refactor.
- Keep `Ajustes` admin-only, so accounts move under the admin setup surface together with cutoff, people, and categories.

## 2026-04-20 - Category Icon Selection

Objective: let admins choose both icon and color when creating categories, and show those icons in the budget plan.

Files touched:

- Added `Category.icon` and migration `budget.0005`.
- Updated category API serialization, budget summaries, expected charges, MSI projection payloads, and demo seed data.
- Updated the Vue category types, category rendering, and admin category form.
- Updated domain, product, and API docs.

Behavior before:

- Categories stored a color only.
- The plan screen rendered every category with the same generic square marker.
- The admin category form exposed only a native color input.

Behavior after:

- Categories store an `icon` key, defaulting to `tag`.
- The frontend renders local SVG icons for category cards and category detail.
- The admin category form includes a visual icon picker and color swatches plus a custom color input.
- Demo categories now seed with domain-specific icons such as food, calendar, flame, wifi, paw, wrench, and box.

Tests/checks:

- `USE_SQLITE_FOR_TESTS=true uv run python manage.py test` passed with 25 tests.
- `pnpm test` passed with 2 tests.
- `pnpm build` passed.
- Applied migration `budget.0005` to the local configured database.
- Ran `uv run python manage.py seed_demo_data` so demo categories use their new icon keys.
- Browser-validated category icons in the plan screen and the icon/color picker in `Ajustes`.

Decisions:

- Use local SVG path icons keyed by string instead of storing SVG markup or depending on downloaded assets.

## 2026-04-20 - Login Logo

Objective: add a proper Burn Rate logo to the login screen.

Files touched:

- Added `frontend/src/assets/burn-rate-logo.svg`.
- Updated the login brand block in `frontend/src/App.vue`.
- Updated login branding CSS in `frontend/src/style.css`.

Behavior before:

- The login screen used a small `BR` text mark.

Behavior after:

- The login screen shows a local SVG logo with a budget-line symbol and Burn Rate wordmark.
- The visible duplicate heading was removed while keeping an accessible `h1` for the page.

Tests/checks:

- `pnpm test` passed with 2 tests.
- `pnpm build` passed.
- Rendered `frontend/src/assets/burn-rate-logo.svg` to PNG with `rsvg-convert` to verify the local SVG asset is valid.

Decisions:

- Keep the logo as a local SVG asset so it is versioned with the frontend and does not depend on external downloads.

## 2026-04-21 - Curated Searchable Category Icon Gallery

Objective: replace the small fixed category icon picker with a higher-quality curated icon gallery and package-backed rendering.

Files touched:

- Added a Lucide-backed category icon catalog in `frontend/src/categoryIcons.ts`.
- Installed `@lucide/vue` in the frontend.
- Updated `frontend/src/App.vue` to render category icons as Vue components and open a searchable gallery from the category form.
- Updated icon gallery and modal styling in `frontend/src/style.css`.
- Added catalog tests in `frontend/src/categoryIcons.test.ts`.
- Updated product, domain, API, architecture, and agent-history docs.

Behavior before:

- The frontend had 12 hardcoded SVG paths inside `App.vue`.
- Admins selected an icon from a fixed inline grid with no search.
- The implementation expected each icon to be a single SVG path.

Behavior after:

- The category icon catalog contains more than 80 curated Lucide icons for household budgeting, food, services, transport, health, finances, education, daily life, and leisure.
- The category form shows the selected icon and opens a modal gallery with search by label, group, id, and Spanish synonyms.
- Existing stored icon keys such as `tag`, `utensils`, `calendar`, `flame`, `wifi`, `paw`, `bolt`, and `box` remain compatible.
- Unknown icon keys still fall back to `tag`.

Tests/checks:

- `pnpm test` passed with 4 tests.
- `pnpm build` passed.
- `USE_SQLITE_FOR_TESTS=true uv run python manage.py test` passed with 25 tests.
- Browser-validated the admin category flow at 390x844 with Playwright: login as `papa`, open `Ajustes`, open the icon gallery, search `mascota`, and select `Mascotas`.
- Started local dev servers in tmux: Django on `http://localhost:8001/` and Vite on `http://localhost:5173/`.

Decisions:

- Use direct Lucide Vue imports for the curated catalog because consistency, offline rendering, and tree-shaking matter more here than exposing every possible icon at runtime.
- Keep database values as short local icon keys instead of storing SVG markup, URLs, or unbounded third-party identifiers.

## 2026-04-21 - UX Direction Alignment

Objective: document the agreed design direction for the full parent-focused simplification pass.

Files touched:

- Updated product documentation for the new mobile UX direction.
- Updated agent history.

Behavior before:

- Product docs described the existing navigation and budgeting concepts, but did not state the parent-first simple-flow direction from the design critique.

Behavior after:

- `Plan` is defined around available money, attention items, quick expense entry, and then the full category ledger.
- `Gastos` is defined as a guided capture flow with sensible defaults and quick helpers.
- `Cargos` and `Ajustes` are framed with plainer language and focused setup sections.
- The product principles now call for a clean family finance app: warm, parent-friendly, progressive, and low-jargon.

Tests/checks:

- Not run; documentation-only change.

Decisions:

- Keep this pass documentation-only so parallel frontend work can own source changes safely.

## 2026-04-21 - Parent-Focused UX Simplification

Objective: apply the P1/P2 critique findings for a simpler, cleaner family finance app for parents managing the household.

Files touched:

- Added `.impeccable.md` with the agreed design context.
- Updated `frontend/src/App.vue` for the simplified Plan, Gastos, Cargos, and Ajustes flows.
- Updated `frontend/src/style.css` for the cleaner family-finance visual system, responsive spacing, larger targets, and focused setup panels.
- Updated `frontend/index.html` to use the local Burn Rate favicon.
- Updated product and agent-history docs.

Behavior before:

- `Plan` led with detailed category accounting and pushed household attention items lower in the flow.
- `Gastos` used a dense accounting form before the fastest parent workflow.
- `Ajustes` exposed accounts, people, categories, and cutoff controls at once.
- The desktop bottom nav could overlap lower page actions.
- The icon gallery opened visually but did not fully isolate keyboard focus from the page behind it.

Behavior after:

- `Plan` now starts with available household money, plain-language status copy, quick actions, and attention items before the detailed category ledger.
- `Gastos` is a guided capture flow with amount/merchant first, quick category and account chips, and optional details collapsed by default.
- `Cargos` uses plainer household language for recurring charges and purchases paid over time.
- `Ajustes` starts with the month cutoff and then separates setup into focused Cuentas, Personas, and Categorias panels.
- Desktop navigation no longer covers lower actions, mobile targets meet the 44px touch baseline, and the icon gallery traps focus while open.

Tests/checks:

- `pnpm build` passed.
- `pnpm test` passed with 4 frontend tests.
- `USE_SQLITE_FOR_TESTS=true uv run python manage.py test` passed with 25 backend tests.
- Browser-validated mobile Plan, Gastos, and Ajustes at 390x844 with Playwright.
- Browser-validated desktop Ajustes and verified the bottom navigation no longer overlaps the form action area.
- Verified the icon gallery modal inert/focus behavior and Escape close behavior with Playwright.

Decisions:

- Keep the main navigation as `Plan`, `Gastos`, `Cargos`, and `Ajustes` so the app feels less technical for household use.
- Keep deeper accounting detail available, but only after the parent has seen the next practical action.

## 2026-04-21 - Layout Rhythm Arrange Pass

Objective: improve spacing, visual hierarchy, and responsive composition after the parent-focused simplification pass.

Files touched:

- Updated `frontend/src/App.vue` with panel-specific setup classes for layout control.
- Updated `frontend/src/style.css` spacing, grouping, navigation placement, mobile form rhythm, and desktop two-column compositions.
- Updated agent history.

Behavior before:

- Several screens used the same tight spacing rhythm, so primary actions, secondary groups, and detailed lists read with similar weight.
- The fixed mobile bottom navigation could visually cover category cards and form actions.
- Desktop settings stretched one long form across the full content width.

Behavior after:

- `Plan`, `Gastos`, `Cargos`, and `Ajustes` use clearer separation between headers, primary surfaces, helper choices, and detail lists.
- The app switcher is now an in-flow sticky navigation element above the active screen, keeping navigation available without covering content.
- Desktop `Ajustes` separates the account form and account list into a two-column layout.
- Desktop `Gastos` separates category and account choices into side-by-side groups while keeping the mobile form linear.

Tests/checks:

- `pnpm test` passed with 4 frontend tests.
- `pnpm build` passed.
- `USE_SQLITE_FOR_TESTS=true uv run python manage.py test` passed with 25 backend tests.
- Browser-validated mobile Plan, Gastos, and Ajustes screenshots at 390x844.
- Browser-validated desktop Plan, Gastos, and Ajustes screenshots at 1280x900.
- Verified no mobile navigation overlap against the first Plan category, the Gastos submit button, and the Ajustes create-account button.

Decisions:

- Use spacing and layout changes instead of adding more cards or decorative elements.
- Keep the simple parent flow intact; this pass changes arrangement, not product behavior.

## 2026-04-21 - UI Normalization Pass

Objective: reduce style drift after the adaptive mobile work by consolidating repeated surfaces, radii, and shadows back onto shared design tokens.

Files touched:

- Updated `frontend/src/style.css` with shared surface, radius, and shadow tokens plus a few grouped component rules for forms, segmented controls, setup tabs, dialogs, and feedback states.
- Updated `docs/agent-history.md` to record the normalization pass.

Behavior before:

- Several components repeated the same off-white, blue, and purple surface colors as one-off values.
- Similar controls used slightly different radius and shadow values even when they served the same visual role.
- Mobile-friendly breakpoint work had left a few duplicated surface decisions in the settings and modal areas.

Behavior after:

- Shared tokens now cover the recurring warm, blue, purple, and green surfaces, plus the common control, card, nav, and modal shadow treatments.
- Segmented controls, setup tabs, icon search, icon selection, feedback banners, and the bottom nav now inherit a more consistent radius language.
- The adapted mobile behavior remains intact, but the style sheet is cleaner and closer to a single system.

Tests/checks:

- `pnpm --prefix frontend test` passed.
- `pnpm --prefix frontend build` passed.

Decisions:

- Keep this pass limited to token consolidation and shared style cleanup.
- Leave spacing/rhythm reshaping for the next arrange agent.
