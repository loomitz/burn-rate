import type {
  CreditCardPaymentOwner,
  CreditCardPaymentSummary,
  CreditCardPaymentSummaryCard,
  InstallmentProjection,
  InstallmentProjectionPeriod,
} from './stores/budget'

// Pure derivations for the "Pagos" (commitments) tab. These mirror the computeds
// that live in App.vue so the calendar-card-cycle behavior can be unit tested
// without mounting the component. App.vue delegates to these functions.

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
