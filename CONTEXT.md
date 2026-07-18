# Burn Rate

Household budget tracker focused on where money goes (burn) rather than account balances. This glossary records the ubiquitous language agreed in the 2026-07-01 domain session; terms marked *(target)* describe the agreed model that is not yet implemented.

## Language

### Time

**Budget period** *(target)*:
The calendar month, from the 1st through the last day. The one clock for budgets, cash, debit, and bank spending.
_Avoid_: cutoff period, ciclo 21–20

**Corte** *(target)*:
The statement closing day of one credit card. Each credit card has its own corte; there is no global corte.
_Avoid_: cutoff day (global)

**Card cycle** *(target)*:
One credit card's statement window: the day after a corte through the next corte, inclusive. Card cycles cross calendar months.
_Avoid_: periodo (when referring to a card)

### Budget consumption

**Live window (ventana viva)** *(target)*:
The set of open spending windows that consume a category's budget at any moment: the current calendar month for cash/debit/bank spending, plus each credit card's open cycle.

**Release (liberación)** *(target)*:
What happens at a card's corte: that card's cycle spending stops consuming category budgets and becomes part of the card's statement. The category's available goes back up by the released amount.

**Available (disponible)** *(target)*:
Category budget minus consumption of all open windows minus pending expected charges. Can legitimately admit more total monthly outflow than the budget, because each corte recharges its window.

**Monthly flow (flujo mensual)** *(target)*:
Everything spent in a category during the calendar month regardless of windows. Informative metric only; exceeding the budget here is not an overspend.

**Overspend (sobregiro)** *(target)*:
A negative available — the open windows together exceeded the category budget. The historical record is the snapshot of negative available at calendar-month close.
_Avoid_: monthly flow above budget

**Carryover category**:
A category whose budget accumulates as a real pot: monthly credits minus all spending, permanently. Excluded from release — card cortes never give money back to a carryover pot.

### Commitments

**MSI mensualidad** *(target)*:
One installment of a months-without-interest plan. Anchored to its card's cycle: exactly one mensualidad per statement. Plans without a card fall back to calendar months.

**Statement (estado de cuenta)** *(target)*:
A card's closed cycle: its purchases plus that cycle's MSI mensualidades. What must be paid to avoid interest.
_Avoid_: por pagar (as a model term; UI label only)

**Payment deadline (fecha límite de pago)**:
The bank's recurring due day for one credit card. Burn Rate resolves the first occurrence after each corte; days `29`–`31` clamp to the last valid day of a shorter month.

**Safe payment date (fecha segura de pago)**:
The date Burn Rate marks for payment: exactly three calendar days before the bank's payment deadline, preserving a fixed safety margin.

### People and accounts

**Owner (titular)** *(target)*:
The household member a card or account belongs to. Grouping and filtering metadata only — it never decides which budget an expense consumes; the category does.

**Household member**:
A budget person in the home, optionally linked to a login user. Owns personal categories.

**Category**:
A budget envelope, either family-wide (scope `global`, shown as "Familia") or personal to one member. Which envelope an expense consumes is decided by its category, never by the payment medium.
