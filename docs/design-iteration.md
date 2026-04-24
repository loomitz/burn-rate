# Burn Rate Design Iteration Handoff

This document coordinates the step-by-step `$impeccable` design pass requested on 2026-04-24. Each phase should append its own result before the next clean sub-agent starts.

## Shared Context

- Register: product UI. Burn Rate is a mobile-first household budgeting app for parents.
- Physical scene: a parent checks the family budget on a phone, often one-handed, between household tasks, wanting calm confidence before recording or approving another expense.
- Design direction: warm, home-like, clear, practical, restrained financial precision, plain Spanish.
- Current baseline from the design critique:
  - `Plan` is visually stable and responsive, but it exposes too many repeated actions in the category grid.
  - The house-level summary is too low in the screen, behind a disclosure after the categories.
  - `Gastos` has the strongest task flow: category, account, data, save.
  - `Ajustes` is too dense on mobile; configuration details compete with the main setup task.
  - The automated detector reported: low contrast, top-border accent on rounded panels, and tight leading.
- Avoid:
  - Side-stripe or thick one-side borders as decorative accents.
  - Gradient text.
  - Glassmorphism as default.
  - Identical card grids as the primary solution.
  - More copy explaining the app inside the app.

## Phase Plan

1. `$impeccable layout Plan`: raise the house summary and reduce repeated category actions.
2. `$impeccable distill Ajustes`: reduce mobile density and hide advanced configuration.
3. `$impeccable clarify`: review labels `Plan`, `Cargos`, `MSI`, `Light`, `Dark`, and improve field-level error/microcopy.
4. `$impeccable document`: create `DESIGN.md` from the actual implemented UI.
5. `$impeccable polish`: final responsive and visual pass.

## Phase Results

### 0. Initial Orchestration

- Created this handoff file before launching clean sub-agents.
- Existing uncommitted state before this pass included `PRODUCT.md` as untracked and `.impeccable.md` deleted, likely from prior context migration. Do not revert those changes unless explicitly instructed.

### 1. `$impeccable layout Plan`

- Raised the house-level summary directly under the Plan cycle controls so the remaining household budget is visible before the category ledger.
- Moved the attention state above the category list to keep urgent house context near the summary.
- Removed the repeated floating `+` action from every category card. Category registration remains available by opening a category detail and using its existing registrar action.
- Reduced Plan visual noise by removing the collapsed summary disclosure, removing the top accent stripe from the summary panel, and replacing one-side attention borders with full low-contrast tone borders.
- Verification: `pnpm --dir frontend build` passed. `localhost:5173` was running; Playwright mobile viewport was available at `390x844`, but the browser session landed on the login screen, so Plan visual inspection was blocked by auth in that browser context.

### 2. `$impeccable distill Ajustes`

- Reordered Ajustes around the primary task flow: cutoff day, section choice, current entities, then inline create/edit only when requested.
- Hid account, person, and category forms behind explicit `Nueva...` actions; editing an existing entity opens the same inline form without a modal.
- Moved account color/status, person access/admin/color, and category icon/color/status into collapsed advanced disclosures so the mobile default state no longer shows swatch grids or long secondary fields.
- Reduced visual noise by removing the accent top border from the essential setup panel and keeping the existing entity lists as the main settings surface.
- Verification: `pnpm --dir frontend build` passed. Playwright mobile inspection at `390x844` passed with `papa@example.com / burnrate123`: Ajustes showed the simplified default account view, and `Nueva cuenta` opened the inline form with `Color y estado` collapsed.

### 3. `$impeccable clarify`

- Standardized the main navigation and related headers for plain Mexican Spanish: `Plan` became `Presupuesto`, `Cargos` became `Pagos`, and payment language now favors `Pago mensual`, `Pagos del mes`, and `Compras a meses`.
- Replaced English theme labels with Spanish labels: `Sistema`, `Claro`, and `Oscuro`, including the compact theme status shown in login/settings.
- Removed visible `MSI` shorthand from the payments UI and projection copy. The UI now says `a meses` or `compras a meses` so parents do not need to know the acronym.
- Improved submit-time validation notices so each one names the missing field and the next action, without adding field-level layouts or new form structure.
- Updated API fallback copy for auth, network, and unknown status errors to be calmer and less technical.
- Verification: `pnpm --dir frontend build` passed. Playwright mobile snapshot at `390x844` loaded the login screen and confirmed visible Spanish labels: `Tema: Sistema / claro`, `Correo`, and `Contraseña`.

### 3b. `$impeccable clarify` cleanup

- Rechecked `App.vue` for visible `Email`, `Password`, `Light`, `Dark`, `MSI`, `Cargos`, and `Plan` labels after Phase 3.
- Changed the two remaining visible `Email` labels in member access and invitations to `Correo`, preserving technical field names, placeholders, and autocomplete attributes.

### 4. `$impeccable document`

- Created root `DESIGN.md` in scan mode from the implemented UI after layout, distill, clarify, and clarify cleanup.
- Captured the current Burn Rate design system as a mobile-first product UI: warm paper surfaces, task-specific accents for `Presupuesto`, `Gastos`, `Pagos`, and settings, Google Sans typography, soft paper-like elevation, large tactile controls, guided forms, sticky navigation, and disclosure-first settings.
- Created `DESIGN.json` sidecar for metadata not supported by Stitch frontmatter, including color metadata, shadow tokens, motion tokens, breakpoints, and renderable component snippets for primary button, secondary button, text field, panel, segmented control, and bottom navigation.
- Kept the documented vocabulary aligned with Phase 3/3b: `Presupuesto`, `Gastos`, `Pagos`, `Sistema`, `Claro`, `Oscuro`, `compras a meses`, `Correo`, and `Contraseña`.
- Verification: `DESIGN.md` shape was checked for YAML frontmatter, required section order, and absence of extra top-level markdown sections beyond the title plus the six required sections. `DESIGN.json` parsed successfully with Node.

### 5. `$impeccable polish`

- Aligned the documented display/headline `letterSpacing` values with the current no-negative-letter-spacing rule and renamed the remaining design-system `Plan overview` reference to `Presupuesto overview`.
- Removed decorative blur from the login panel and sticky navigation so the app stays in the warm paper surface vocabulary instead of default glassmorphism.
- Set visible heading/number letter spacing back to `0` in the UI while preserving Google Sans hierarchy, weights, and tabular numeric treatment.
- Raised small interactive controls to the 44px touch target floor: login theme action, compact edit icon actions, destructive inline actions, and the mobile payment-row actions.
- Verification: `DESIGN.json` parsed successfully with Node. `pnpm --dir frontend build` passed. `pnpm --dir frontend test` passed with 21 tests across 3 files. Playwright inspection passed at `390x844` and `1280x900` for `Presupuesto`, `Gastos`, `Pagos`, and `Ajustes`: no horizontal overflow, no visible old labels (`Plan`, `Cargos`, `MSI`, `Email`, `Password`, `Light`, `Dark`), and no sub-44px visible touch targets in the mobile pass.

### 6. Browser review follow-up

- Moved `Resumen de casa` and `Atención de casa` to the end of the `Presupuesto` screen, after `Detalle por categoría`, per browser comments 2 and 3.
- Replaced the native cycle select arrow with a normally sized custom chevron and added right-side inset so the affordance is separated from the edge.
- Upgraded the cycle control from native select to a tactile cycle picker with a readable trigger, recent-cycle menu, current-cycle badge, and full-width mobile dropdown.
- Updated main navigation icons: house/control for `Presupuesto`, bill for `Gastos`, credit card for `Pagos`, and retained gear for `Ajustes`.
- Tightened the desktop `Gastos` date field, added `Nuevo pago mensual` in `Pagos > Mensuales`, and made focused `Ajustes` panels full-width to remove asymmetric right padding.
- Updated `DESIGN.md` so the documented `Presupuesto overview` placement matches the reviewed layout.
