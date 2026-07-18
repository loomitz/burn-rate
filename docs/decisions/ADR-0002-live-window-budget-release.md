# ADR-0002: Calendar-Month Budgets With Live-Window Release Per Credit Card

## Status

Accepted (2026-07-01). Implementation pending.

## Context

Burn Rate started with one global cutoff day (20) and one budget clock: periods ran from the 21st to the 20th. The household now has several credit cards with different owners and different statement closing days. The family pays each statement in full, so the number that matters per card is "what this statement will cost", while the budget question is "how much are we burning per category".

## Decision

Split the single clock into two:

- The budget period becomes the calendar month (1st through last day). The global `cutoff_day` disappears as a budget concept.
- Each credit card gets its own corte (statement closing day, validated 1–28 like the old global value). A card cycle runs from the day after a corte through the next corte, inclusive.

Category consumption follows the "live window" model:

- Available = budget − cash/debit/bank spending of the current calendar month − each card's spending since its last corte − pending expected charges.
- At a card's corte, that card's cycle spending is released: it stops consuming category budgets and becomes the card's statement, visible in payments as an obligation.
- Carryover categories are excluded from release; their pot only ever decreases when spent.
- Overspend is redefined as negative available (live), recorded historically as the negative snapshot at month close. Monthly flow above budget is informative, not overspend.
- MSI mensualidades anchor to their card's cycle (one per statement); plans without a card fall back to calendar months.
- Accounts gain an optional owner (household member) for grouping and filtering only; budget attribution stays with the category.

## Considered Options

- Assigning card spending to the calendar month of its corte (statement-month accounting). Rejected: no release at the corte, which is the behavior the household actually wants to see, and it hides current-cycle burn from the current month.
- Live window plus a hard monthly-flow cap. Rejected: contradicts the release semantics and is harder to explain than tracking flow as a separate informative metric.

## Consequences

- A category's total monthly outflow can legitimately exceed its budget, because each corte recharges that card's window. The budget acts as a cap per payment-medium cycle, not per calendar month.
- Spending after a corte keeps consuming the category across the month boundary until the next corte.
- Historical materialized data (allocations, overspend records, budget changes) anchored to the old 21–20 periods is re-derived onto calendar months (full recompute). The household accepts correcting edge data by hand afterward.
- Recurring expenses keep generating once per calendar month by charge day; the posted expense consumes whatever window its date and account fall into.
- Payment summaries become per-card statements (closed cycle purchases plus that cycle's MSI mensualidad) and can be totaled across cards or filtered by card or owner.
