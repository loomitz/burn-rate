import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useBudgetStore } from './budget'

function jsonResponse(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('budget store auth flow', () => {
  const fetchMock = vi.fn()
  const readyOnboardingStatus = {
    ready: true,
    database: {
      connected: true,
      message: 'Conexion a base de datos lista.',
      configured: {
        engine: 'postgresql',
        name: 'burn_rate',
        user: 'burn_rate',
        host: 'db',
        port: '5432',
        password_configured: true,
      },
    },
    migrations: { applied: true, pending_count: 0 },
    initial_config: {
      ready: true,
      needs_first_admin: true,
      has_users: false,
      settings_ready: true,
    },
  }

  beforeEach(() => {
    setActivePinia(createPinia())
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  function mockFetchAllResponses() {
    fetchMock.mockResolvedValueOnce(jsonResponse({ created_count: 0, transactions: [] }))
    fetchMock.mockResolvedValueOnce(jsonResponse({ currency: 'MXN', cutoff_day: 20 }))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        period: { start: '2026-04-21', end: '2026-05-20' },
        scope: 'total',
        totals: { budget_cents: 0, spent_cents: 0, expected_cents: 0, consumed_cents: 0, available_cents: 0 },
        categories: [],
      }),
    )
    fetchMock.mockResolvedValueOnce(jsonResponse({ charges: [] }))
    fetchMock.mockResolvedValueOnce(jsonResponse({ periods: [], plans: [] }))
  }

  it('keeps auth unresolved until bootstrap status chooses first-run claim', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(readyOnboardingStatus))
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'ok' }))
    fetchMock.mockResolvedValueOnce(jsonResponse({ has_users: false, can_claim: true }))

    const store = useBudgetStore()
    expect(store.authReady).toBe(false)

    await store.bootstrap()

    expect(store.authReady).toBe(true)
    expect(store.user).toBeNull()
    expect(store.onboardingReady).toBe(true)
    expect(store.firstRunClaimRequired).toBe(true)
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      '/api/onboarding/status/',
      '/api/auth/csrf/',
      '/api/bootstrap/status/',
    ])
  })

  it('stops bootstrap on onboarding checks before auth endpoints', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        ...readyOnboardingStatus,
        ready: false,
        database: {
          ...readyOnboardingStatus.database,
          connected: false,
          message: 'connection refused',
        },
      }),
    )

    const store = useBudgetStore()

    await store.bootstrap()

    expect(store.authReady).toBe(true)
    expect(store.onboardingReady).toBe(false)
    expect(store.user).toBeNull()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/onboarding/status/')
  })

  it('clears local budget data on logout even after loading household state', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))

    const store = useBudgetStore()
    store.user = { id: 1, username: 'papa', email: 'papa@example.com', is_staff: true, is_superuser: false }
    store.members = [
      {
        id: 1,
        name: 'Casa',
        color: '#b35320',
        is_active: true,
        access_enabled: true,
        user_username: 'papa',
        user_email: 'papa@example.com',
        user_is_admin: true,
      },
    ]
    store.invitations = [
      {
        id: 1,
        email: 'familia@example.com',
        full_name: 'Familia Prueba',
        display_name: 'Familia',
        message: 'Hola',
        is_admin: false,
        token: 'abc',
      },
    ]

    await store.logout()

    expect(store.user).toBeNull()
    expect(store.members).toEqual([])
    expect(store.invitations).toEqual([])
    expect(store.summary).toBeNull()
  })

  it('resolves invitation tokens through the planned endpoint', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        email: 'familia@example.com',
        full_name: 'Familia Prueba',
        display_name: 'Familia',
        message: 'Hola',
        is_admin: false,
      }),
    )

    const store = useBudgetStore()
    const invitation = await store.resolveInvitation('abc/123')

    expect(invitation.token).toBe('abc/123')
    expect(invitation.email).toBe('familia@example.com')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/invitations/resolve/?token=abc%2F123')
  })

  it('deletes unaccepted invitations from the local list', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))

    const store = useBudgetStore()
    store.invitations = [
      {
        id: 4,
        email: 'pendiente@example.com',
        full_name: '',
        display_name: '',
        message: '',
        is_admin: false,
      },
      {
        id: 5,
        email: 'otra@example.com',
        full_name: '',
        display_name: '',
        message: '',
        is_admin: true,
      },
    ]

    await store.deleteInvitation(4)

    expect(fetchMock.mock.calls[0][0]).toBe('/api/invitations/4/')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'DELETE' })
    expect(store.invitations.map((invitation) => invitation.id)).toEqual([5])
  })

  it('updates accounts through the account endpoint', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'ok' }))
    fetchMock.mockResolvedValueOnce(jsonResponse({ created_count: 0, transactions: [] }))
    fetchMock.mockResolvedValueOnce(jsonResponse({ currency: 'MXN', cutoff_day: 20 }))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        period: { start: '2026-04-21', end: '2026-05-20' },
        scope: 'total',
        totals: { budget_cents: 0, spent_cents: 0, expected_cents: 0, consumed_cents: 0, available_cents: 0 },
        categories: [],
      }),
    )
    fetchMock.mockResolvedValueOnce(jsonResponse({ charges: [] }))
    fetchMock.mockResolvedValueOnce(jsonResponse({ periods: [], plans: [] }))

    const store = useBudgetStore()

    await store.updateAccount(3, { name: 'Banco casa', color: '#2563eb', is_active: false })

    expect(fetchMock.mock.calls[0][0]).toBe('/api/accounts/3/')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: 'PATCH',
      body: JSON.stringify({ name: 'Banco casa', color: '#2563eb', is_active: false }),
    })
  })

  it('updates household members through the member endpoint', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'ok' }))
    fetchMock.mockResolvedValueOnce(jsonResponse({ created_count: 0, transactions: [] }))
    fetchMock.mockResolvedValueOnce(jsonResponse({ currency: 'MXN', cutoff_day: 20 }))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        period: { start: '2026-04-21', end: '2026-05-20' },
        scope: 'total',
        totals: { budget_cents: 0, spent_cents: 0, expected_cents: 0, consumed_cents: 0, available_cents: 0 },
        categories: [],
      }),
    )
    fetchMock.mockResolvedValueOnce(jsonResponse({ charges: [] }))
    fetchMock.mockResolvedValueOnce(jsonResponse({ periods: [], plans: [] }))

    const store = useBudgetStore()

    await store.updateMember(7, { has_access: true, username: 'nuez', is_admin: true })

    expect(fetchMock.mock.calls[0][0]).toBe('/api/household-members/7/')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: 'PATCH',
      body: JSON.stringify({ has_access: true, username: 'nuez', is_admin: true }),
    })
  })

  it('creates monthly reset categories by default payload', async () => {
    const payload = {
      name: 'Despensa',
      scope: 'global' as const,
      member: null,
      monthly_budget_cents: 200000,
      budget_behavior: 'monthly_reset' as const,
      color: '#e11d48',
      icon: 'shopping-cart',
      is_active: true,
      order: 0,
    }
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'ok' }))
    mockFetchAllResponses()

    const store = useBudgetStore()

    await store.createCategory(payload)

    expect(fetchMock.mock.calls[0][0]).toBe('/api/categories/')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: 'POST',
      body: JSON.stringify(payload),
    })
  })

  it('creates carryover categories with initial balance and start date', async () => {
    const payload = {
      name: 'Viajes',
      scope: 'global' as const,
      member: null,
      monthly_budget_cents: 250000,
      budget_behavior: 'carryover' as const,
      carryover_initial_balance_cents: -50000,
      carryover_start_date: '2026-04-21',
      color: '#0284c7',
      icon: 'plane',
      is_active: true,
      order: 0,
    }
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'ok' }))
    mockFetchAllResponses()

    const store = useBudgetStore()

    await store.createCategory(payload)

    expect(fetchMock.mock.calls[0][0]).toBe('/api/categories/')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: 'POST',
      body: JSON.stringify(payload),
    })
  })

  it('updates category budget with an effective date', async () => {
    const payload = { monthly_budget_cents: 150000, budget_effective_date: '2026-04-21' }
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'ok' }))
    mockFetchAllResponses()

    const store = useBudgetStore()

    await store.updateCategory(8, payload)

    expect(fetchMock.mock.calls[0][0]).toBe('/api/categories/8/')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  })

  it('creates installment plans with first payment date and months count', async () => {
    const payload = {
      name: 'Laptop heredada',
      merchant: 'Liverpool',
      total_amount_cents: 1200000,
      category: 2,
      account: 1,
      start_date: '2026-04-21',
      months_count: 12,
      round_up_monthly_payment: true,
      is_active: true,
    }
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'ok' }))
    fetchMock.mockResolvedValueOnce(jsonResponse({ created_count: 0, transactions: [] }))
    fetchMock.mockResolvedValueOnce(jsonResponse({ currency: 'MXN', cutoff_day: 20 }))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        period: { start: '2026-04-21', end: '2026-05-20' },
        scope: 'total',
        totals: { budget_cents: 0, spent_cents: 0, expected_cents: 0, consumed_cents: 0, available_cents: 0 },
        categories: [],
      }),
    )
    fetchMock.mockResolvedValueOnce(jsonResponse({ charges: [] }))
    fetchMock.mockResolvedValueOnce(jsonResponse({ periods: [], plans: [] }))

    const store = useBudgetStore()

    await store.createInstallment(payload)

    expect(fetchMock.mock.calls[0][0]).toBe('/api/installment-plans/')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: 'POST',
      body: JSON.stringify(payload),
    })
  })

  it('creates recurring expenses with a shared merchant', async () => {
    const payload = {
      name: 'Internet mensual',
      merchant: 'Telmex',
      amount_cents: 59900,
      category: 2,
      account: 1,
      start_date: '2026-04-21',
      end_date: null,
      charge_day: 5,
      is_active: true,
    }
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'ok' }))
    fetchMock.mockResolvedValueOnce(jsonResponse({ created_count: 0, transactions: [] }))
    fetchMock.mockResolvedValueOnce(jsonResponse({ currency: 'MXN', cutoff_day: 20 }))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(jsonResponse([]))
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        period: { start: '2026-04-21', end: '2026-05-20' },
        scope: 'total',
        totals: { budget_cents: 0, spent_cents: 0, expected_cents: 0, consumed_cents: 0, available_cents: 0 },
        categories: [],
      }),
    )
    fetchMock.mockResolvedValueOnce(jsonResponse({ charges: [] }))
    fetchMock.mockResolvedValueOnce(jsonResponse({ periods: [], plans: [] }))

    const store = useBudgetStore()

    await store.createRecurring(payload)

    expect(fetchMock.mock.calls[0][0]).toBe('/api/recurring-expenses/')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: 'POST',
      body: JSON.stringify(payload),
    })
  })

  it('updates recurring expenses with only name and merchant', async () => {
    const payload = { name: 'Internet casa', merchant: 'Telmex Hogar' }
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'ok' }))
    mockFetchAllResponses()

    const store = useBudgetStore()

    await store.updateRecurring(9, payload)

    expect(fetchMock.mock.calls[0][0]).toBe('/api/recurring-expenses/9/')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  })

  it('deletes recurring expenses and refreshes the dashboard state', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))
    mockFetchAllResponses()

    const store = useBudgetStore()

    await store.deleteRecurring(9)

    expect(fetchMock.mock.calls[0][0]).toBe('/api/recurring-expenses/9/')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'DELETE' })
    expect(fetchMock.mock.calls.map((call) => call[0])).toContain('/api/recurring-expenses/')
    expect(fetchMock.mock.calls.map((call) => call[0])).toContain('/api/installment-plans/')
  })

  it('deletes installment plans and refreshes the projection state', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))
    mockFetchAllResponses()

    const store = useBudgetStore()

    await store.deleteInstallment(12)

    expect(fetchMock.mock.calls[0][0]).toBe('/api/installment-plans/12/')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'DELETE' })
    expect(fetchMock.mock.calls.map((call) => call[0])).toContain('/api/recurring-expenses/')
    expect(fetchMock.mock.calls.map((call) => call[0])).toContain('/api/installment-plans/')
  })

  it('updates installment plans with name, merchant, and category', async () => {
    const payload = { name: 'Laptop trabajo', merchant: 'Liverpool Online', category: 5 }
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'ok' }))
    mockFetchAllResponses()

    const store = useBudgetStore()

    await store.updateInstallment(12, payload)

    expect(fetchMock.mock.calls[0][0]).toBe('/api/installment-plans/12/')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  })
})
