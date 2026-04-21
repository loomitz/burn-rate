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
})
