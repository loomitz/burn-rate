import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import CreditCardsSummary from './CreditCardsSummary.vue'
import type { CreditCardPaymentSummary } from '../stores/budget'

function summaryFixture(): CreditCardPaymentSummary {
  return {
    total_cents: 250000,
    as_of: '2026-05-10',
    cards: [
      {
        account_id: 3,
        account_name: 'Tarjeta oro',
        account_color: '#eab308',
        owner: { id: 2, name: 'Ana', color: '#dc2626' },
        closed_cycle: {
          start: '2026-03-21',
          end: '2026-04-20',
          payment_due_date: '2026-05-10',
          safe_payment_date: '2026-05-07',
          purchase_cents: 30000,
          installment_cents: 200000,
          total_cents: 230000,
        },
        open_cycle: {
          start: '2026-04-21',
          end: '2026-05-20',
          payment_due_date: '2026-06-10',
          safe_payment_date: '2026-06-07',
          purchase_cents: 50000,
          installment_cents: 200000,
          total_cents: 250000,
        },
      },
      {
        account_id: 4,
        account_name: 'Tarjeta azul',
        account_color: '#475569',
        owner: null,
        closed_cycle: {
          start: '2026-04-06',
          end: '2026-05-05',
          payment_due_date: null,
          safe_payment_date: null,
          purchase_cents: 20000,
          installment_cents: 0,
          total_cents: 20000,
        },
        open_cycle: {
          start: '2026-05-06',
          end: '2026-06-05',
          payment_due_date: null,
          safe_payment_date: null,
          purchase_cents: 40000,
          installment_cents: 0,
          total_cents: 40000,
        },
      },
    ],
    owners: [
      { member: { id: 2, name: 'Ana', color: '#dc2626' }, total_cents: 230000, account_ids: [3] },
      { member: null, total_cents: 20000, account_ids: [4] },
    ],
  }
}

describe('CreditCardsSummary', () => {
  it('renders the portfolio KPIs, charts and configured preventive date', () => {
    const wrapper = mount(CreditCardsSummary, {
      props: { summary: summaryFixture(), currency: 'MXN' },
    })

    expect(wrapper.get('h1').text()).toBe('Tarjetas')
    expect(wrapper.text()).toContain('$2,500.00')
    expect(wrapper.text()).toContain('$2,900.00')
    expect(wrapper.text()).toContain('Cortado vs. acumulando')
    expect(wrapper.text()).toContain('De qué viene el saldo')
    expect(wrapper.text()).toContain('Fecha preventiva pasada')
    expect(wrapper.findAll('[role="img"]').length).toBeGreaterThanOrEqual(5)
  })

  it('keeps cards without a bank deadline explicitly unconfigured', () => {
    const wrapper = mount(CreditCardsSummary, {
      props: { summary: summaryFixture(), currency: 'MXN' },
    })

    expect(wrapper.text()).toContain('Tarjeta azul')
    expect(wrapper.text()).toContain('Fecha pendiente')
    expect(wrapper.text()).toContain('Por configurar')
  })

  it('uses the open-cycle deadline when the closed cycle has no balance', () => {
    const summary = summaryFixture()
    const card = summary.cards[0]
    card.closed_cycle.purchase_cents = 0
    card.closed_cycle.installment_cents = 0
    card.closed_cycle.total_cents = 0

    const wrapper = mount(CreditCardsSummary, {
      props: { summary, currency: 'MXN' },
    })
    const row = wrapper.findAll('.card-statement-row').find((candidate) => candidate.text().includes('Tarjeta oro'))

    expect(row).toBeDefined()
    expect(row!.text()).toContain('7 jun')
    expect(row!.text()).toContain('10 jun')
    expect(row!.text()).not.toContain('7 may')
  })

  it('shows a configured zero-balance card as up to date', () => {
    const summary = summaryFixture()
    const card = summary.cards[0]
    card.closed_cycle.purchase_cents = 0
    card.closed_cycle.installment_cents = 0
    card.closed_cycle.total_cents = 0
    card.open_cycle.purchase_cents = 0
    card.open_cycle.installment_cents = 0
    card.open_cycle.total_cents = 0

    const wrapper = mount(CreditCardsSummary, {
      props: { summary, currency: 'MXN' },
    })
    const row = wrapper.findAll('.card-statement-row').find((candidate) => candidate.text().includes('Tarjeta oro'))

    expect(row).toBeDefined()
    expect(row!.text()).toContain('Sin saldo pendiente')
    expect(row!.text()).toContain('Al día')
    expect(row!.text()).not.toContain('Por configurar')
  })

  it('emits the two navigation actions', async () => {
    const wrapper = mount(CreditCardsSummary, {
      props: { summary: summaryFixture(), currency: 'MXN' },
    })
    const buttons = wrapper.findAll('button')
    const benefits = buttons.find((button) => button.text() === 'Beneficios')
    const settings = buttons.find((button) => button.text() === 'Ajustar tarjetas')

    expect(benefits).toBeDefined()
    expect(settings).toBeDefined()
    await benefits!.trigger('click')
    await settings!.trigger('click')

    expect(wrapper.emitted('openBenefits')).toHaveLength(1)
    expect(wrapper.emitted('openSettings')).toHaveLength(1)
  })

  it('renders an actionable empty state', async () => {
    const wrapper = mount(CreditCardsSummary, {
      props: { summary: null, currency: 'MXN' },
    })

    expect(wrapper.text()).toContain('Tu resumen aparecerá aquí')
    const addButton = wrapper.findAll('button').find((button) => button.text() === 'Agregar tarjeta')
    expect(addButton).toBeDefined()
    await addButton!.trigger('click')
    expect(wrapper.emitted('openSettings')).toHaveLength(1)
  })
})
