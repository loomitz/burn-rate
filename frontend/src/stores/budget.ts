import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ApiError, apiErrorMessage, apiRequest } from './api'

export type Scope = 'family' | 'member' | 'total'

export interface User {
  id: number
  username: string
  email: string
  is_staff: boolean
  is_superuser: boolean
}

export interface BootstrapStatus {
  has_users?: boolean
  user_count?: number
  needs_claim?: boolean
  can_claim?: boolean
  claim_required?: boolean
  requires_claim?: boolean
}

export interface OnboardingStatus {
  ready: boolean
  database: {
    connected: boolean
    message: string
    configured: {
      engine: string
      name: string
      user: string
      host: string
      port: string
      password_configured: boolean
    }
  }
  migrations: {
    applied: boolean
    pending_count: number | null
  }
  initial_config: {
    ready: boolean
    needs_first_admin: boolean
    has_users: boolean
    settings_ready: boolean
  }
}

export interface ClaimPayload {
  email: string
  full_name: string
  display_name: string
  password: string
}

export interface Invitation {
  id: number | string
  email: string
  full_name: string
  display_name: string
  message: string
  is_admin?: boolean
  is_staff?: boolean
  status?: string
  token?: string
  accept_url?: string
  url?: string
  link?: string
  created_at?: string
  expires_at?: string | null
  accepted_at?: string | null
}

export interface ResolvedInvitation {
  token: string
  email: string
  full_name: string
  display_name: string
  message: string
  is_admin?: boolean
  is_staff?: boolean
  status?: string
  household_name?: string
  invited_by?: string
  expires_at?: string | null
  accepted_at?: string | null
}

export interface InvitationCreatePayload {
  email: string
  is_admin: boolean
}

export interface InvitationAcceptPayload {
  token: string
  email: string
  full_name: string
  display_name: string
  password: string
}

export interface Settings {
  currency: string
  cutoff_day: number
}

export interface HouseholdMember {
  id: number
  name: string
  color: string
  is_active: boolean
  access_enabled: boolean
  user_username: string | null
  user_email: string | null
  user_is_admin: boolean
  has_access?: boolean
  username?: string
  email?: string
  password?: string
  is_admin?: boolean
}

export interface Category {
  id: number
  name: string
  color: string
  icon: string
  order: number
  is_active: boolean
  scope: 'global' | 'personal'
  member: number | null
  member_name: string | null
  monthly_budget_cents: number
}

export interface Account {
  id: number
  name: string
  account_type: string
  color: string
  initial_balance_cents: number
  current_balance_cents: number
  is_active: boolean
}

export interface Transaction {
  id: number
  transaction_type: string
  merchant: string
  amount_cents: number
  date: string
  account: number | null
  account_name: string | null
  destination_account: number | null
  destination_account_name: string | null
  category: number | null
  category_name: string | null
  member: number | null
  member_name: string | null
  note: string
  created_by: number | null
  created_by_username: string | null
}

export interface MerchantConcept {
  id: number
  name: string
  usage_count: number
  last_used_at: string | null
  created_at: string
}

export interface RecurringExpense {
  id: number
  name: string
  merchant: string
  amount_cents: number
  category: number
  category_name: string
  member_name: string | null
  account: number | null
  account_name: string | null
  start_date: string
  end_date: string | null
  charge_day: number
  is_active: boolean
}

export interface InstallmentPlan {
  id: number
  name: string
  merchant: string
  total_amount_cents: number
  monthly_amount_cents: number
  category: number
  category_name: string
  member_name: string | null
  account: number | null
  account_name: string | null
  start_date: string
  end_date: string
  first_payment_number: number
  installments_count: number
  round_up_monthly_payment: boolean
  is_active: boolean
}

export type InstallmentPlanCreatePayload = Partial<InstallmentPlan> & { months_count?: number }
export type InstallmentPlanUpdatePayload = Partial<Pick<InstallmentPlan, 'name' | 'merchant' | 'category'>>

export interface ExpectedCharge {
  key: string
  source_type: 'recurring' | 'installment'
  source_id: number
  name: string
  merchant: string
  amount_cents: number
  date: string
  category: { id: number; name: string; scope: string; color: string; icon: string }
  member: { id: number; name: string; color: string } | null
  account: { id: number; name: string } | null
  payment_number: number | null
  payments_total: number | null
  total_amount_cents: number | null
}

export interface InstallmentProjectionPlan {
  id: number
  name: string
  merchant: string
  amount_cents?: number
  total_amount_cents: number
  round_up_monthly_payment: boolean
  current_amount_cents?: number
  current_payment_number?: number | null
  payment_number?: number
  payments_total: number
  remaining_payments: number
  projected_total_cents?: number
  monthly_amounts?: Array<{ period_end: string; amount_cents: number }>
  category: { id: number; name: string; scope: string; color: string; icon: string }
  member: { id: number; name: string; color: string } | null
  account: { id: number; name: string } | null
}

export interface InstallmentProjectionPeriod {
  key: string
  start: string
  end: string
  label: string
  total_cents: number
  plans: InstallmentProjectionPlan[]
}

export interface InstallmentProjection {
  current_period_key: string
  current_total_cents: number
  periods: InstallmentProjectionPeriod[]
  plans: InstallmentProjectionPlan[]
}

export interface BudgetCategorySummary {
  category_id: number
  category_name: string
  scope: string
  member: { id: number; name: string; color: string } | null
  color: string
  icon: string
  budget_cents: number
  spent_cents: number
  expected_cents: number
  consumed_cents: number
  available_cents: number
  percent_available: number
  is_overspent: boolean
}

export interface BudgetSummary {
  period: { start: string; end: string }
  scope: Scope
  member_id: number | null
  totals: {
    budget_cents: number
    spent_cents: number
    expected_cents: number
    available_cents: number
  }
  breakdown: Array<{
    key: string
    label: string
    color: string
    budget_cents: number
    spent_cents: number
    expected_cents: number
    available_cents: number
  }>
  categories: BudgetCategorySummary[]
}

type AuthResponse = { user?: User | null } | null
type InvitationListResponse = Invitation[] | { invitations?: Invitation[]; results?: Invitation[] }

const DEFAULT_SETTINGS: Settings = { currency: 'MXN', cutoff_day: 20 }
const AUTH_REFRESH_THROTTLE_MS = 2 * 60 * 1000

function normalizeInvitationList(response: InvitationListResponse) {
  if (Array.isArray(response)) return response
  return response.invitations ?? response.results ?? []
}

export const useBudgetStore = defineStore('budget', () => {
  const user = ref<User | null>(null)
  const authReady = ref(false)
  const onboardingStatus = ref<OnboardingStatus | null>(null)
  const bootstrapStatus = ref<BootstrapStatus | null>(null)
  const settings = ref<Settings>({ ...DEFAULT_SETTINGS })
  const members = ref<HouseholdMember[]>([])
  const categories = ref<Category[]>([])
  const accounts = ref<Account[]>([])
  const merchantConcepts = ref<MerchantConcept[]>([])
  const transactions = ref<Transaction[]>([])
  const recurringExpenses = ref<RecurringExpense[]>([])
  const installmentPlans = ref<InstallmentPlan[]>([])
  const expectedCharges = ref<ExpectedCharge[]>([])
  const installmentProjection = ref<InstallmentProjection | null>(null)
  const summary = ref<BudgetSummary | null>(null)
  const invitations = ref<Invitation[]>([])
  const resolvedInvitation = ref<ResolvedInvitation | null>(null)
  const loading = ref(false)
  const error = ref('')
  let fetchAllRequestId = 0
  let authRefreshInFlight: Promise<User | null> | null = null
  let lastAuthRefreshAt = 0

  const activeCategories = computed(() => categories.value.filter((category) => category.is_active))
  const activeAccounts = computed(() => accounts.value.filter((account) => account.is_active))
  const onboardingReady = computed(() => onboardingStatus.value?.ready !== false)
  const firstRunClaimRequired = computed(() => {
    const status = bootstrapStatus.value
    if (!status) return false
    return Boolean(
      status.needs_claim ||
        status.can_claim ||
        status.claim_required ||
        status.requires_claim ||
        status.has_users === false ||
        status.user_count === 0,
    )
  })

  function clearBudgetData(clearUser = false) {
    fetchAllRequestId += 1
    if (clearUser) user.value = null
    settings.value = { ...DEFAULT_SETTINGS }
    members.value = []
    categories.value = []
    accounts.value = []
    merchantConcepts.value = []
    transactions.value = []
    recurringExpenses.value = []
    installmentPlans.value = []
    expectedCharges.value = []
    installmentProjection.value = null
    summary.value = null
    invitations.value = []
    resolvedInvitation.value = null
  }

  async function fetchBootstrapStatus() {
    try {
      bootstrapStatus.value = await apiRequest<BootstrapStatus>('/api/bootstrap/status/')
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        bootstrapStatus.value = { has_users: true }
        return
      }
      throw err
    }
  }

  async function fetchOnboardingStatus() {
    onboardingStatus.value = await apiRequest<OnboardingStatus>('/api/onboarding/status/')
    return onboardingStatus.value
  }

  async function setAuthenticatedUser(nextUser: User | null) {
    if (!nextUser) {
      clearBudgetData(true)
      return
    }
    user.value = nextUser
    bootstrapStatus.value = { ...(bootstrapStatus.value ?? {}), has_users: true, needs_claim: false, can_claim: false }
    await fetchAll()
  }

  async function bootstrap() {
    loading.value = true
    authReady.value = false
    error.value = ''
    try {
      await fetchOnboardingStatus()
      if (!onboardingReady.value) {
        clearBudgetData(true)
        return
      }
      await apiRequest('/api/auth/csrf/')
      await fetchBootstrapStatus()
      if (firstRunClaimRequired.value) {
        clearBudgetData(true)
        return
      }
      const me = await apiRequest<{ user: User | null }>('/api/auth/me/')
      if (!me.user) {
        clearBudgetData(true)
        return
      }
      await setAuthenticatedUser(me.user)
    } catch (err) {
      clearBudgetData(true)
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        error.value = ''
        return
      }
      error.value = apiErrorMessage(err, 'No pudimos iniciar Burn Rate.')
    } finally {
      loading.value = false
      authReady.value = true
    }
  }

  async function claimFirstRun(payload: ClaimPayload) {
    await apiRequest('/api/auth/csrf/')
    const response = await apiRequest<AuthResponse>('/api/bootstrap/claim/', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    bootstrapStatus.value = { ...(bootstrapStatus.value ?? {}), has_users: true, needs_claim: false, can_claim: false }
    if (response?.user) {
      await setAuthenticatedUser(response.user)
      return
    }
    const me = await apiRequest<{ user: User | null }>('/api/auth/me/')
    await setAuthenticatedUser(me.user)
  }

  async function login(email: string, password: string) {
    await apiRequest('/api/auth/csrf/')
    const response = await apiRequest<{ user: User }>('/api/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    await setAuthenticatedUser(response.user)
  }

  async function refreshAuth(options: { force?: boolean; reason?: 'interval' | 'visible' | 'activity' | 'manual' } = {}) {
    if (!user.value) return null
    const now = Date.now()
    if (!options.force && now - lastAuthRefreshAt < AUTH_REFRESH_THROTTLE_MS) {
      return user.value
    }
    if (authRefreshInFlight) return authRefreshInFlight
    authRefreshInFlight = (async () => {
      try {
        const response = await apiRequest<AuthResponse>('/api/auth/refresh/', { method: 'POST' })
        lastAuthRefreshAt = Date.now()
        if (response?.user) {
          user.value = response.user
        }
        return user.value
      } catch (err) {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          clearBudgetData(true)
          return null
        }
        if (err instanceof ApiError && err.status === 404) {
          lastAuthRefreshAt = Date.now()
          return user.value
        }
        throw err
      } finally {
        authRefreshInFlight = null
      }
    })()
    return authRefreshInFlight
  }

  async function logout() {
    try {
      await apiRequest('/api/auth/logout/', { method: 'POST' })
    } finally {
      clearBudgetData(true)
      bootstrapStatus.value = { ...(bootstrapStatus.value ?? {}), has_users: true, needs_claim: false, can_claim: false }
    }
  }

  async function fetchAll(date = new Date().toISOString().slice(0, 10), scope: Scope = 'total', memberId?: number) {
    const requestId = ++fetchAllRequestId
    const summaryParams = new URLSearchParams({ date, scope })
    if (memberId !== undefined) summaryParams.set('member_id', String(memberId))
    loading.value = true
    error.value = ''
    try {
      const [
        settingsData,
        membersData,
        categoriesData,
        accountsData,
        merchantConceptsData,
        transactionsData,
        recurringData,
        plansData,
        summaryData,
        expectedData,
        installmentData,
      ] = await Promise.all([
        apiRequest<Settings>('/api/settings/'),
        apiRequest<HouseholdMember[]>('/api/household-members/'),
        apiRequest<Category[]>('/api/categories/'),
        apiRequest<Account[]>('/api/accounts/'),
        apiRequest<MerchantConcept[]>('/api/merchant-concepts/'),
        apiRequest<Transaction[]>('/api/transactions/'),
        apiRequest<RecurringExpense[]>('/api/recurring-expenses/'),
        apiRequest<InstallmentPlan[]>('/api/installment-plans/'),
        apiRequest<BudgetSummary>(`/api/budget/summary/?${summaryParams}`),
        apiRequest<{ charges: ExpectedCharge[] }>(`/api/expected-charges/?date=${date}`),
        apiRequest<InstallmentProjection>(`/api/installments/projection/?date=${date}&months=6`),
      ])
      if (requestId !== fetchAllRequestId) return
      settings.value = settingsData
      members.value = membersData
      categories.value = categoriesData
      accounts.value = accountsData
      merchantConcepts.value = merchantConceptsData
      transactions.value = transactionsData
      recurringExpenses.value = recurringData
      installmentPlans.value = plansData
      summary.value = summaryData
      expectedCharges.value = expectedData.charges
      installmentProjection.value = installmentData
    } catch (err) {
      if (requestId !== fetchAllRequestId) return
      error.value = 'No se pudo cargar Burn Rate.'
      error.value = apiErrorMessage(err, error.value)
      throw err
    } finally {
      if (requestId === fetchAllRequestId) {
        loading.value = false
      }
    }
  }

  async function fetchSummary(date: string, scope: Scope, memberId?: number) {
    const params = new URLSearchParams({ date, scope })
    if (memberId !== undefined) params.set('member_id', String(memberId))
    summary.value = await apiRequest<BudgetSummary>(`/api/budget/summary/?${params}`)
  }

  async function fetchExpectedCharges(date: string) {
    const data = await apiRequest<{ charges: ExpectedCharge[] }>(`/api/expected-charges/?date=${date}`)
    expectedCharges.value = data.charges
  }

  async function fetchInstallmentProjection(date: string) {
    installmentProjection.value = await apiRequest<InstallmentProjection>(
      `/api/installments/projection/?date=${date}&months=6`,
    )
  }

  async function saveSettings(payload: Settings) {
    settings.value = await apiRequest<Settings>('/api/settings/', {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  }

  async function createMember(payload: Partial<HouseholdMember>) {
    await apiRequest('/api/household-members/', { method: 'POST', body: JSON.stringify(payload) })
    await fetchAll()
  }

  async function updateMember(id: number, payload: Partial<HouseholdMember>) {
    await apiRequest(`/api/household-members/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) })
    await fetchAll()
  }

  async function createCategory(payload: Partial<Category>) {
    await apiRequest('/api/categories/', { method: 'POST', body: JSON.stringify(payload) })
    await fetchAll()
  }

  async function updateCategory(id: number, payload: Partial<Category>) {
    await apiRequest(`/api/categories/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) })
    await fetchAll()
  }

  async function createAccount(payload: Partial<Account>) {
    await apiRequest('/api/accounts/', { method: 'POST', body: JSON.stringify(payload) })
    await fetchAll()
  }

  async function updateAccount(id: number, payload: Partial<Account>) {
    await apiRequest(`/api/accounts/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) })
    await fetchAll()
  }

  async function createTransaction(payload: Partial<Transaction>) {
    await apiRequest('/api/transactions/', { method: 'POST', body: JSON.stringify(payload) })
    await fetchAll(payload.date ?? new Date().toISOString().slice(0, 10))
  }

  async function createRecurring(payload: Partial<RecurringExpense>) {
    await apiRequest('/api/recurring-expenses/', { method: 'POST', body: JSON.stringify(payload) })
    await fetchAll()
  }

  async function updateRecurring(id: RecurringExpense['id'], payload: Pick<RecurringExpense, 'name' | 'merchant'>) {
    await apiRequest(`/api/recurring-expenses/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) })
    await fetchAll()
  }

  async function deleteRecurring(id: RecurringExpense['id']) {
    await apiRequest(`/api/recurring-expenses/${id}/`, { method: 'DELETE' })
    await fetchAll()
  }

  async function createInstallment(payload: InstallmentPlanCreatePayload) {
    await apiRequest('/api/installment-plans/', { method: 'POST', body: JSON.stringify(payload) })
    await fetchAll()
  }

  async function updateInstallment(id: InstallmentPlan['id'], payload: InstallmentPlanUpdatePayload) {
    await apiRequest(`/api/installment-plans/${id}/`, { method: 'PATCH', body: JSON.stringify(payload) })
    await fetchAll()
  }

  async function deleteInstallment(id: InstallmentPlan['id']) {
    await apiRequest(`/api/installment-plans/${id}/`, { method: 'DELETE' })
    await fetchAll()
  }

  async function confirmCharge(charge: ExpectedCharge, accountId: number) {
    await apiRequest('/api/expected-charges/confirm/', {
      method: 'POST',
      body: JSON.stringify({
        source_type: charge.source_type,
        source_id: charge.source_id,
        date: charge.date,
        account: accountId,
      }),
    })
    await fetchAll(charge.date)
  }

  async function dismissCharge(charge: ExpectedCharge) {
    await apiRequest('/api/expected-charges/dismiss/', {
      method: 'POST',
      body: JSON.stringify({
        source_type: charge.source_type,
        source_id: charge.source_id,
        date: charge.date,
      }),
    })
    await fetchAll(charge.date)
  }

  async function fetchInvitations() {
    if (!user.value?.is_staff && !user.value?.is_superuser) return
    const response = await apiRequest<InvitationListResponse>('/api/invitations/')
    invitations.value = normalizeInvitationList(response)
  }

  async function createInvitation(payload: InvitationCreatePayload) {
    const invitation = await apiRequest<Invitation>('/api/invitations/', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    invitations.value = [invitation, ...invitations.value.filter((item) => item.id !== invitation.id)]
    return invitation
  }

  async function deleteInvitation(id: Invitation['id']) {
    await apiRequest(`/api/invitations/${id}/`, { method: 'DELETE' })
    invitations.value = invitations.value.filter((item) => item.id !== id)
  }

  async function resolveInvitation(token: string) {
    const params = new URLSearchParams({ token })
    const invitation = await apiRequest<ResolvedInvitation>(`/api/invitations/resolve/?${params}`)
    resolvedInvitation.value = { ...invitation, token: invitation.token || token }
    return resolvedInvitation.value
  }

  async function acceptInvitation(payload: InvitationAcceptPayload) {
    await apiRequest('/api/auth/csrf/')
    const response = await apiRequest<AuthResponse>('/api/invitations/accept/', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    resolvedInvitation.value = null
    bootstrapStatus.value = { ...(bootstrapStatus.value ?? {}), has_users: true, needs_claim: false, can_claim: false }
    if (response?.user) {
      await setAuthenticatedUser(response.user)
      return
    }
    const me = await apiRequest<{ user: User | null }>('/api/auth/me/')
    await setAuthenticatedUser(me.user)
  }

  return {
    user,
    authReady,
    onboardingStatus,
    onboardingReady,
    bootstrapStatus,
    settings,
    members,
    categories,
    accounts,
    merchantConcepts,
    transactions,
    recurringExpenses,
    installmentPlans,
    expectedCharges,
    installmentProjection,
    summary,
    invitations,
    resolvedInvitation,
    loading,
    error,
    activeCategories,
    activeAccounts,
    firstRunClaimRequired,
    bootstrap,
    claimFirstRun,
    login,
    refreshAuth,
    logout,
    clearBudgetData,
    fetchAll,
    fetchOnboardingStatus,
    fetchSummary,
    fetchExpectedCharges,
    fetchInstallmentProjection,
    saveSettings,
    createMember,
    updateMember,
    createCategory,
    updateCategory,
    createAccount,
    updateAccount,
    createTransaction,
    createRecurring,
    updateRecurring,
    deleteRecurring,
    createInstallment,
    updateInstallment,
    deleteInstallment,
    confirmCharge,
    dismissCharge,
    fetchInvitations,
    createInvitation,
    deleteInvitation,
    resolveInvitation,
    acceptInvitation,
  }
})
