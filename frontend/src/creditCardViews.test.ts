import { describe, expect, it } from 'vitest'

import {
  cardPaymentOwnerGroupsFrom,
  computeProjectionPeriodsView,
  focusedMsiCardId,
  msiCardChipsFrom,
  msiOwnerChipsFrom,
} from './creditCardViews'
import type {
  CreditCardPaymentSummary,
  InstallmentProjection,
  InstallmentProjectionPlan,
} from './stores/budget'

// Fixtures mirror docs/api.md: two owned/unowned credit cards plus a plan
// without a card, exercised through both month mode and cycle mode.
const ana = { id: 2, name: 'Ana', color: '#dc2626' }
const beto = { id: 5, name: 'Beto', color: '#2563eb' }
const cardOro = { id: 3, name: 'Tarjeta oro', account_type: 'credit_card', color: '#eab308' }
const cardAzul = { id: 4, name: 'Tarjeta azul', account_type: 'credit_card', color: '#475569' }

function makePlan(
  overrides: Partial<InstallmentProjectionPlan> & Pick<InstallmentProjectionPlan, 'id' | 'name'>,
): InstallmentProjectionPlan {
  return {
    merchant: 'Tienda',
    total_amount_cents: 0,
    round_up_monthly_payment: true,
    payments_total: 3,
    remaining_payments: 2,
    category: { id: 2, name: 'Meses', scope: 'global', budget_treatment: 'budgeted', color: '#0f766e', icon: 'tag' },
    member: null,
    account: null,
    owner: null,
    ...overrides,
  }
}

const planPantalla = makePlan({ id: 1, name: 'Pantalla', amount_cents: 300000, account: cardOro, owner: ana })
const planColchon = makePlan({ id: 2, name: 'Colchón sin tarjeta', amount_cents: 100000, account: null, owner: null })
const planRefri = makePlan({ id: 3, name: 'Refri', amount_cents: 200000, account: cardAzul, owner: beto })

function monthProjection(): InstallmentProjection {
  return {
    mode: 'month',
    account: null,
    current_period_key: '2026-04',
    current_total_cents: 600000,
    periods: [
      {
        key: '2026-04',
        start: '2026-04-01',
        end: '2026-04-30',
        label: '2026-04-01 / 2026-04-30',
        total_cents: 600000,
        cards: [
          { account_id: 3, account_name: 'Tarjeta oro', total_cents: 300000 },
          { account_id: 4, account_name: 'Tarjeta azul', total_cents: 200000 },
          { account_id: null, account_name: null, total_cents: 100000 },
        ],
        plans: [planPantalla, planColchon, planRefri],
      },
      {
        key: '2026-05',
        start: '2026-05-01',
        end: '2026-05-31',
        label: '2026-05-01 / 2026-05-31',
        total_cents: 500000,
        cards: [
          { account_id: 3, account_name: 'Tarjeta oro', total_cents: 300000 },
          { account_id: 4, account_name: 'Tarjeta azul', total_cents: 200000 },
        ],
        plans: [planPantalla, planRefri],
      },
    ],
    plans: [planPantalla, planColchon, planRefri],
  }
}

// Cycle mode for card 3: columns keyed by real cutoff dates instead of months.
function cycleProjection(): InstallmentProjection {
  return {
    mode: 'cycle',
    account: { id: 3, name: 'Tarjeta oro', color: '#eab308', cutoff_day: 20, owner: ana },
    current_period_key: '2026-05-20',
    current_total_cents: 300000,
    periods: [
      {
        key: '2026-05-20',
        start: '2026-04-21',
        end: '2026-05-20',
        label: '2026-04-21 / 2026-05-20',
        total_cents: 300000,
        cards: [{ account_id: 3, account_name: 'Tarjeta oro', total_cents: 300000 }],
        plans: [planPantalla],
      },
      {
        key: '2026-06-20',
        start: '2026-05-21',
        end: '2026-06-20',
        label: '2026-05-21 / 2026-06-20',
        total_cents: 300000,
        cards: [{ account_id: 3, account_name: 'Tarjeta oro', total_cents: 300000 }],
        plans: [planPantalla],
      },
    ],
    plans: [planPantalla],
  }
}

function paymentSummary(): CreditCardPaymentSummary {
  return {
    total_cents: 250000,
    as_of: '2026-05-10',
    cards: [
      {
        account_id: 3,
        account_name: 'Tarjeta oro',
        account_color: '#eab308',
        owner: ana,
        closed_cycle: { start: '2026-03-21', end: '2026-04-20', purchase_cents: 30000, installment_cents: 200000, total_cents: 230000 },
        open_cycle: { start: '2026-04-21', end: '2026-05-20', purchase_cents: 50000, installment_cents: 200000, total_cents: 250000 },
      },
      {
        account_id: 4,
        account_name: 'Tarjeta azul',
        account_color: '#475569',
        owner: null,
        closed_cycle: { start: '2026-04-06', end: '2026-05-05', purchase_cents: 20000, installment_cents: 0, total_cents: 20000 },
        open_cycle: { start: '2026-05-06', end: '2026-06-05', purchase_cents: 40000, installment_cents: 0, total_cents: 40000 },
      },
    ],
    owners: [
      { member: ana, total_cents: 230000, account_ids: [3] },
      { member: null, total_cents: 20000, account_ids: [4] },
    ],
  }
}

describe('MSI projection filters', () => {
  it('shows the global month-calendar projection with a per-card breakdown when nothing is filtered', () => {
    const base = monthProjection()
    const view = computeProjectionPeriodsView(base, null, [], [])

    expect(view).toBe(base.periods)
    expect(view.map((period) => period.key)).toEqual(['2026-04', '2026-05'])
    expect(view.every((period) => /^\d{4}-\d{2}$/.test(period.key))).toBe(true)
    // Per-card breakdown survives, including the null-account bucket for plans without a card.
    expect(view[0].cards).toEqual([
      { account_id: 3, account_name: 'Tarjeta oro', total_cents: 300000 },
      { account_id: 4, account_name: 'Tarjeta azul', total_cents: 200000 },
      { account_id: null, account_name: null, total_cents: 100000 },
    ])
    expect(view[0].total_cents).toBe(600000)
  })

  it('exposes one chip per card in the breakdown, skipping plans without a card', () => {
    expect(msiCardChipsFrom(monthProjection())).toEqual([
      { id: 3, name: 'Tarjeta oro' },
      { id: 4, name: 'Tarjeta azul' },
    ])
    expect(msiCardChipsFrom(null)).toEqual([])
  })

  it('exposes one chip per plan owner and dedupes across periods', () => {
    expect(msiOwnerChipsFrom(monthProjection())).toEqual([ana, beto])
    expect(msiOwnerChipsFrom(null)).toEqual([])
  })

  it('reduces rows and totals when a single card is filtered', () => {
    const base = monthProjection()
    const view = computeProjectionPeriodsView(base, null, [3], [])

    expect(view[0].plans.map((plan) => plan.id)).toEqual([1])
    expect(view[0].total_cents).toBe(300000)
    expect(view[1].plans.map((plan) => plan.id)).toEqual([1])
    expect(view[1].total_cents).toBe(300000)
    // Original fixture is not mutated.
    expect(base.periods[0].plans).toHaveLength(3)
    expect(base.periods[0].total_cents).toBe(600000)
  })

  it('keeps several cards but drops plans without a card when multiple cards are filtered', () => {
    const view = computeProjectionPeriodsView(monthProjection(), null, [3, 4], [])

    expect(view[0].plans.map((plan) => plan.id)).toEqual([1, 3])
    expect(view[0].total_cents).toBe(500000)
  })

  it('filters by owner across cards', () => {
    const view = computeProjectionPeriodsView(monthProjection(), null, [], [2])

    expect(view[0].plans.map((plan) => plan.id)).toEqual([1])
    expect(view[0].total_cents).toBe(300000)
    expect(view[1].plans.map((plan) => plan.id)).toEqual([1])
  })

  it('intersects owner and card filters (AND semantics)', () => {
    const kept = computeProjectionPeriodsView(monthProjection(), null, [3], [2])
    expect(kept[0].plans.map((plan) => plan.id)).toEqual([1])
    expect(kept[0].total_cents).toBe(300000)

    // Ana owns card 3, not card 4, so the intersection is empty.
    const empty = computeProjectionPeriodsView(monthProjection(), null, [4], [2])
    expect(empty[0].plans).toEqual([])
    expect(empty[0].total_cents).toBe(0)
  })

  it('focuses a single selected card and only then switches to real card cycles', () => {
    expect(focusedMsiCardId([3])).toBe(3)
    expect(focusedMsiCardId([])).toBeNull()
    expect(focusedMsiCardId([3, 4])).toBeNull()
  })

  it('returns the card cycle columns verbatim when a card is focused', () => {
    const base = monthProjection()
    const focused = cycleProjection()
    const view = computeProjectionPeriodsView(base, focused, [3], [])

    // Focus wins over base + filters: the cycle-mode periods are returned as-is.
    expect(view).toBe(focused.periods)
    // Columns are real cutoff dates (full ISO date) rather than generic month keys.
    expect(view.map((period) => period.key)).toEqual(['2026-05-20', '2026-06-20'])
    expect(view.every((period) => /^\d{4}-\d{2}-\d{2}$/.test(period.key))).toBe(true)
  })
})

describe('Credit card payment panel', () => {
  it('resolves each card closed cycle "por pagar" as purchases plus MSI installment', () => {
    const [oro, azul] = paymentSummary().cards

    expect(oro.closed_cycle.purchase_cents + oro.closed_cycle.installment_cents).toBe(oro.closed_cycle.total_cents)
    expect(oro.closed_cycle.total_cents).toBe(230000)
    expect(azul.closed_cycle.purchase_cents + azul.closed_cycle.installment_cents).toBe(azul.closed_cycle.total_cents)
    expect(azul.closed_cycle.total_cents).toBe(20000)
  })

  it('resolves each card open cycle "acumulando" as purchases plus MSI installment', () => {
    const [oro, azul] = paymentSummary().cards

    expect(oro.open_cycle.purchase_cents + oro.open_cycle.installment_cents).toBe(oro.open_cycle.total_cents)
    expect(oro.open_cycle.total_cents).toBe(250000)
    expect(azul.open_cycle.total_cents).toBe(40000)
  })

  it('reports a global due total equal to the sum of every card closed cycle', () => {
    const summary = paymentSummary()
    const sumOfCards = summary.cards.reduce((total, card) => total + card.closed_cycle.total_cents, 0)
    const sumOfOwners = summary.owners.reduce((total, owner) => total + owner.total_cents, 0)

    expect(summary.total_cents).toBe(sumOfCards)
    expect(summary.total_cents).toBe(sumOfOwners)
    expect(summary.total_cents).toBe(250000)
  })

  it('groups cards by owner without double counting', () => {
    const summary = paymentSummary()
    const groups = cardPaymentOwnerGroupsFrom(summary)

    expect(groups).toHaveLength(2)
    expect(groups[0].owner.member?.name).toBe('Ana')
    expect(groups[0].cards.map((card) => card.account_id)).toEqual([3])

    // Each card lands in exactly one group.
    const groupedIds = groups.flatMap((group) => group.cards.map((card) => card.account_id))
    expect(groupedIds).toEqual([3, 4])
    expect(new Set(groupedIds).size).toBe(groupedIds.length)

    // Each owner subtotal equals the sum of its cards' closed cycles.
    for (const group of groups) {
      const groupSum = group.cards.reduce((total, card) => total + card.closed_cycle.total_cents, 0)
      expect(group.owner.total_cents).toBe(groupSum)
    }
  })

  it('places a card without owner in the unnamed group', () => {
    const groups = cardPaymentOwnerGroupsFrom(paymentSummary())
    const unnamed = groups.find((group) => group.owner.member === null)

    expect(unnamed).toBeDefined()
    expect(unnamed?.cards.map((card) => card.account_id)).toEqual([4])
  })

  it('returns no groups when there is no summary', () => {
    expect(cardPaymentOwnerGroupsFrom(null)).toEqual([])
  })
})
