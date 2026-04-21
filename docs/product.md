# Product

Burn Rate is a small family budgeting app for one household. It helps a household track monthly spending against planned budgets without requiring bank sync, multi-tenant setup, or personal-finance complexity.

## Principles

- Fast expense capture on a phone.
- Simple guided flows for parents managing the household.
- Put available money, attention items, and the next expense action before detailed ledgers.
- Clear available budget per category.
- Negative available amounts are shown directly when a category is overspent.
- Household budgets and personal budgets live together in one family view.
- Recurring charges and interest-free installments are visible before they surprise the month.
- Use warm, plain family-finance language instead of unexplained jargon.
- Reveal setup and advanced decisions only when needed.
- Documentation is part of the product, not an afterthought.

## Brand Assets

- The official Burn Rate logo set lives in `frontend/src/assets/brand/`.
- `burn-rate-logo-dark.svg` is used when the resolved interface theme is dark.
- `burn-rate-logo-light.svg` is used when the resolved interface theme is light.
- `favicon.svg` is the browser favicon and mirrors the supplied `Logos/favicon.svg` asset.
- `burn-rate-logo-black.svg` is preserved as an official variant for monochrome or high-contrast surfaces.

## Visual Theme

Burn Rate supports `Auto`, `Light`, and `Dark` theme preferences. `Auto` follows the browser or operating-system color-scheme preference. The interface keeps the same product accents by job area: teal for `Plan`, orange for `Gastos`, purple for `Cargos`, and blue for `Ajustes`.

Users change the theme from a switch-style segmented control inside `Ajustes`, placed just above the final logout action. The login screen also exposes a small icon-only theme cycle so users can adjust the surface before signing in. The preference is stored locally in the browser.

The resolved dark theme uses neutral charcoal backgrounds and surfaces so the app does not read as warm brown in low-light mode. Section colors stay as accents for navigation, states, and primary actions.

## Mobile Interface Map

The primary phone navigation follows the product jobs:

- `Plan`: whole-house budget cycles with a compact past-to-current selector, category status cards first, centered progress bars, direct color-matched category expense actions, category expense detail, attention items styled like ledger cards, and a collapsed summary for totals.
- `Gastos`: guided expense capture with searchable category and account cards, account color cues, reusable merchant/concept suggestions, a final expense details block for merchant, amount, date, and note, and recent movement review.
- `Cargos`: recurring charges, interest-free installment pressure, a compact inline cycle total, transparent action buttons for each pending charge, MSI totals by cycle with liquidation markers, and new commitment creation using plain labels.
- `Ajustes`: admin-only setup sections for cutoff day, accounts, household people, and categories, then theme for every authenticated user, and a large logout action at the end of the screen.

Accounts are managed from `Ajustes` instead of being a separate main tab because the normal daily flow is planning, spending, and commitment review.
Logout also lives in `Ajustes` so the daily Plan screen stays focused on budget actions.

## In Scope

- Local authenticated users for the same household.
- Read-only onboarding status that checks database connectivity, migrations, and initial app configuration before login or first-admin claim.
- First-run setup where the first user claims the installation as the initial admin.
- Admin-issued invitations for additional household users, with optional email delivery and a copyable link fallback.
- Household members with optional app access.
- Admin access for users who can change settings, people, and categories.
- Family household categories.
- Personal categories owned by a household member.
- Category color and searchable curated icon selection for quick visual scanning.
- Payment media or accounts with simple balances.
- Manual expenses, income, and transfers.
- Recurring monthly expenses.
- Interest-free installment plans.
- Monthly budget periods using a configurable cutoff day.

## Out of Scope For MVP

- Multi-tenant organizations.
- Public self-registration outside the first-admin claim and admin-issued invitation links.
- Bank connections, CSV imports, and statement reconciliation.
- Credit-card statement cycles, interest, minimum payments, or debt payoff modeling.
- Attachments and receipts.
- Offline-first capture and synchronization.
- Advanced analytics.
