import type {
  CreditCardPaymentOwner,
  CreditCardPaymentSummary,
  CreditCardPaymentSummaryCard,
  InstallmentProjection,
  InstallmentProjectionPeriod,
} from './stores/budget'

// Pure derivations shared by the Pagos and Tarjetas views. Keeping chart and
// cycle aggregation outside Vue makes the financial display rules easy to test
// without mounting the application shell.

export interface MsiCardChip {
  id: number
  name: string
}

export interface MsiOwnerChip {
  id: number
  name: string
  color: string
}

export interface CardPaymentOwnerGroup {
  owner: CreditCardPaymentOwner
  cards: CreditCardPaymentSummaryCard[]
}

export interface CardPaymentDistributionItem {
  account_id: number
  account_name: string
  account_color: string
  total_cents: number
  percent: number
}

export interface CardPortfolioPayment {
  account_id: number
  account_name: string
  account_color: string
  cycle: 'closed' | 'open'
  total_cents: number
  safe_payment_date: string
  payment_due_date: string
}

export interface CardPortfolioStats {
  card_count: number
  due_total_cents: number
  accumulating_total_cents: number
  due_purchase_cents: number
  due_installment_cents: number
  accumulating_purchase_cents: number
  accumulating_installment_cents: number
  max_cycle_total_cents: number
  next_payment: CardPortfolioPayment | null
}

// A single selected card focuses the projection on that card's real cycles.
// Zero or several selected cards keep the calendar-month (global) view.
export function focusedMsiCardId(cardFilter: number[]): number | null {
  return cardFilter.length === 1 ? cardFilter[0] : null
}

// One chip per credit card that appears in the month-mode per-card breakdown.
// Plans without a card (account_id === null) never produce a chip.
export function msiCardChipsFrom(projection: InstallmentProjection | null): MsiCardChip[] {
  const map = new Map<number, MsiCardChip>()
  for (const period of projection?.periods ?? [])
    for (const card of period.cards)
      if (card.account_id != null)
        map.set(card.account_id, { id: card.account_id, name: card.account_name ?? 'Cuenta' })
  return [...map.values()]
}

// One chip per plan owner (household member) present in the projection.
export function msiOwnerChipsFrom(projection: InstallmentProjection | null): MsiOwnerChip[] {
  const map = new Map<number, MsiOwnerChip>()
  for (const plan of projection?.plans ?? []) if (plan.owner) map.set(plan.owner.id, plan.owner)
  return [...map.values()]
}

// The periods actually rendered in the MSI timeline.
// - When a single card is focused, `focused` carries that card's cycle-mode
//   projection (columns keyed by real cutoff dates) and is returned verbatim.
// - Otherwise the calendar-month projection is filtered by the selected cards
//   and/or owners, recomputing each column total from the surviving plans.
export function computeProjectionPeriodsView(
  base: InstallmentProjection | null,
  focused: InstallmentProjection | null,
  cardFilter: number[],
  ownerFilter: number[],
): InstallmentProjectionPeriod[] {
  if (focused) return focused.periods
  const periods = base?.periods ?? []
  const cardSet = new Set(cardFilter)
  const ownerSet = new Set(ownerFilter)
  if (!cardSet.size && !ownerSet.size) return periods
  return periods.map((period) => {
    const plans = period.plans.filter(
      (plan) =>
        (!cardSet.size || (plan.account && cardSet.has(plan.account.id))) &&
        (!ownerSet.size || (plan.owner && ownerSet.has(plan.owner.id))),
    )
    return { ...period, plans, total_cents: plans.reduce((total, plan) => total + (plan.amount_cents ?? 0), 0) }
  })
}

// Groups the closed-cycle statement cards under each owner bucket. Every owner
// bucket resolves its own cards from `account_ids`, so a card belongs to exactly
// one group and cards without an owner land in the `member === null` bucket.
export function cardPaymentOwnerGroupsFrom(summary: CreditCardPaymentSummary | null): CardPaymentOwnerGroup[] {
  const cards = summary?.cards ?? []
  return (summary?.owners ?? []).map((owner) => ({
    owner,
    cards: cards.filter((card) => owner.account_ids.includes(card.account_id)),
  }))
}

// Portfolio-level figures for the dedicated credit-card summary view. The API
// remains the source of truth for every cycle; this helper only aggregates the
// already-calculated blocks for charts and scan-friendly KPIs.
export function cardPortfolioStatsFrom(summary: CreditCardPaymentSummary | null): CardPortfolioStats {
  const cards = summary?.cards ?? []
  const paymentCandidates: CardPortfolioPayment[] = []

  let accumulatingTotal = 0
  let duePurchase = 0
  let dueInstallment = 0
  let accumulatingPurchase = 0
  let accumulatingInstallment = 0
  let maxCycleTotal = 0

  for (const card of cards) {
    duePurchase += card.closed_cycle.purchase_cents
    dueInstallment += card.closed_cycle.installment_cents
    accumulatingPurchase += card.open_cycle.purchase_cents
    accumulatingInstallment += card.open_cycle.installment_cents
    accumulatingTotal += card.open_cycle.total_cents
    maxCycleTotal = Math.max(maxCycleTotal, card.closed_cycle.total_cents, card.open_cycle.total_cents)

    for (const cycle of ['closed', 'open'] as const) {
      const block = cycle === 'closed' ? card.closed_cycle : card.open_cycle
      if (!block.total_cents || !block.safe_payment_date || !block.payment_due_date) continue
      paymentCandidates.push({
        account_id: card.account_id,
        account_name: card.account_name,
        account_color: card.account_color,
        cycle,
        total_cents: block.total_cents,
        safe_payment_date: block.safe_payment_date,
        payment_due_date: block.payment_due_date,
      })
    }
  }

  paymentCandidates.sort((left, right) => {
    if (left.cycle !== right.cycle) return left.cycle === 'closed' ? -1 : 1
    return left.safe_payment_date.localeCompare(right.safe_payment_date)
  })

  return {
    card_count: cards.length,
    due_total_cents: summary?.total_cents ?? 0,
    accumulating_total_cents: accumulatingTotal,
    due_purchase_cents: duePurchase,
    due_installment_cents: dueInstallment,
    accumulating_purchase_cents: accumulatingPurchase,
    accumulating_installment_cents: accumulatingInstallment,
    max_cycle_total_cents: maxCycleTotal,
    next_payment: paymentCandidates[0] ?? null,
  }
}

export function cardPaymentDistributionFrom(
  summary: CreditCardPaymentSummary | null,
): CardPaymentDistributionItem[] {
  const cards = summary?.cards ?? []
  const total = cards.reduce((sum, card) => sum + card.closed_cycle.total_cents, 0)

  return cards
    .filter((card) => card.closed_cycle.total_cents > 0)
    .map((card) => ({
      account_id: card.account_id,
      account_name: card.account_name,
      account_color: card.account_color,
      total_cents: card.closed_cycle.total_cents,
      percent: total > 0 ? (card.closed_cycle.total_cents / total) * 100 : 0,
    }))
    .sort((left, right) => right.total_cents - left.total_cents || left.account_name.localeCompare(right.account_name, 'es-MX'))
}
