<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { Laptop, Moon, Search, Sun, X } from '@lucide/vue'
import {
  useBudgetStore,
  type Account,
  type Category,
  type ExpectedCharge,
  type HouseholdMember,
  type Invitation,
  type Scope,
} from './stores/budget'
import { apiErrorMessage, centsFromInput, money } from './stores/api'
import { categoryIcons, getCategoryIcon } from './categoryIcons'
import burnRateLogoDark from './assets/brand/burn-rate-logo-dark.svg'
import burnRateLogoLight from './assets/brand/burn-rate-logo-light.svg'

const store = useBudgetStore()
const {
  user,
  authReady,
  onboardingStatus,
  onboardingReady,
  settings,
  members,
  categories,
  accounts,
  activeCategories,
  activeAccounts,
  merchantConcepts,
  transactions,
  recurringExpenses,
  expectedCharges,
  installmentProjection,
  summary,
  invitations,
  resolvedInvitation,
  loading,
  error,
  firstRunClaimRequired,
} = storeToRefs(store)

type View = 'budget' | 'expenses' | 'commitments' | 'settings'
type ExpensesTab = 'capture' | 'feed'
type CommitmentTab = 'subscriptions' | 'msi'
type CommitmentKind = 'subscription' | 'msi'
type SettingsPanel = 'accounts' | 'people' | 'categories' | 'invitations'
type NoticeType = 'success' | 'error' | 'info'
type MerchantSuggestionTarget = 'expense' | 'recurring' | 'installment'
type ThemePreference = 'auto' | 'light' | 'dark'
type ResolvedTheme = 'light' | 'dark'
type BudgetCycleOption = { value: string; label: string; start: string; end: string; offset: number }

const THEME_STORAGE_KEY = 'burn-rate-theme'
const AUTH_REFRESH_INTERVAL_MS = 10 * 60 * 1000
const AUTH_ACTIVITY_REFRESH_MS = 2 * 60 * 1000
const view = ref<View>('budget')
const expensesTab = ref<ExpensesTab>('capture')
const commitmentTab = ref<CommitmentTab>('subscriptions')
const commitmentKind = ref<CommitmentKind>('subscription')
const settingsPanel = ref<SettingsPanel>('accounts')
const theme = ref<ThemePreference>(storedThemePreference())
const systemTheme = ref<ResolvedTheme>(preferredSystemTheme())
const showCommitmentForm = ref(false)
const showPlanSummary = ref(false)
const iconGalleryOpen = ref(false)
const iconGalleryDialog = ref<HTMLElement | null>(null)
const iconGalleryOpener = ref<HTMLElement | null>(null)
const iconSearch = ref('')
const todayIso = new Date().toISOString().slice(0, 10)
const selectedDate = ref(todayIso)
const selectedScope = ref<Scope>('total')
const selectedCategoryId = ref<number | null>(null)
const expenseCategorySearch = ref('')
const expenseAccountSearch = ref('')
const merchantSuggestionsOpen = ref(false)
const merchantSuggestionTarget = ref<MerchantSuggestionTarget>('expense')
const inviteToken = ref(inviteTokenFromLocation())
const inviteLoading = ref(false)
const copiedInvitationId = ref<number | string | null>(null)
const createdInvitationLink = ref('')
const editingAccountId = ref<number | null>(null)
const editingMemberId = ref<number | null>(null)
const editingCategoryId = ref<number | null>(null)
const claimForm = reactive({ full_name: '', display_name: '', email: '', password: '', confirmPassword: '' })
const loginForm = reactive({ email: '', password: '' })
const acceptInviteForm = reactive({ full_name: '', display_name: '', password: '', confirmPassword: '' })
const invitationForm = reactive({
  email: '',
  is_admin: false,
})
const expenseForm = reactive({ merchant: '', amount: '', category: '', account: '', date: selectedDate.value, note: '' })
const accountForm = reactive({
  name: '',
  account_type: 'cash',
  initial_balance: '',
  color: '#7c6250',
  is_active: true,
})
const memberForm = reactive({
  name: '',
  color: '#b35320',
  has_access: false,
  username: '',
  email: '',
  password: '',
  is_admin: false,
})
const categoryForm = reactive({
  name: '',
  scope: 'global',
  member: '',
  monthly_budget: '',
  color: '#e11d48',
  icon: 'tag',
  is_active: true,
})
const recurringForm = reactive({
  name: '',
  merchant: '',
  amount: '',
  category: '',
  account: '',
  start_date: selectedDate.value,
  end_date: '',
  charge_day: 21,
})
const installmentForm = reactive({
  name: '',
  merchant: '',
  total_amount: '',
  category: '',
  account: '',
  start_date: selectedDate.value,
  end_date: selectedDate.value,
  first_payment_number: '1',
})
const settingsForm = reactive({ cutoff_day: 20 })
const notice = reactive<{ type: NoticeType; message: string }>({ type: 'info', message: '' })
const actionBusy = ref('')
let noticeTimer: ReturnType<typeof window.setTimeout> | undefined
let merchantSuggestionsTimer: ReturnType<typeof window.setTimeout> | undefined
let authRefreshTimer: ReturnType<typeof window.setInterval> | undefined
let lastActivityRefreshAttempt = 0
let copiedInvitationTimer: ReturnType<typeof window.setTimeout> | undefined
let systemThemeMediaQuery: MediaQueryList | undefined

const navItems = [
  { id: 'budget', label: 'Plan', icon: 'M4 5h16M4 12h16M4 19h10' },
  { id: 'expenses', label: 'Gastos', icon: 'M7 4h10v16H7zM9 8h6M9 12h6M9 16h4' },
  { id: 'commitments', label: 'Cargos', icon: 'M7 4h10v16H7zM9 8h6M9 12h6M9 16h6' },
  { id: 'settings', label: 'Ajustes', icon: 'M12 15a3 3 0 100-6 3 3 0 000 6ZM19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 0v-.09a1.65 1.65 0 00-1-1.51 1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06A1.65 1.65 0 004.6 15a1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09a1.65 1.65 0 001.51-1 1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 008.92 4.6a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06A1.65 1.65 0 0019.4 9c.24.54.78.9 1.37 1H21a2 2 0 110 4h-.23a1.65 1.65 0 00-1.37 1Z' },
] as const

const setupPanelItems = [
  { id: 'accounts', label: 'Cuentas' },
  { id: 'people', label: 'Personas' },
  { id: 'categories', label: 'Categorías' },
  { id: 'invitations', label: 'Invitar' },
] as const

const themeOptions = [
  { id: 'auto', label: 'Auto', icon: Laptop },
  { id: 'light', label: 'Light', icon: Sun },
  { id: 'dark', label: 'Dark', icon: Moon },
] as const

const categoryColors = [
  '#e11d48',
  '#f97316',
  '#f59e0b',
  '#16a34a',
  '#0d9488',
  '#0284c7',
  '#4f46e5',
  '#9333ea',
  '#db2777',
  '#7c2d12',
  '#374151',
]

const accountColors = [
  '#7c6250',
  '#2563eb',
  '#0d9488',
  '#16a34a',
  '#ca8a04',
  '#dc2626',
  '#9333ea',
  '#0891b2',
  '#4f46e5',
  '#be185d',
  '#475569',
]

const canManageSettings = computed(() => Boolean(user.value?.is_staff || user.value?.is_superuser))
const visibleNavItems = computed(() => navItems)
const activeTheme = computed<ResolvedTheme>(() => (theme.value === 'auto' ? systemTheme.value : theme.value))
const isDarkTheme = computed(() => activeTheme.value === 'dark')
const themeLogo = computed(() => (isDarkTheme.value ? burnRateLogoDark : burnRateLogoLight))
const themeCycleIcon = computed(() => themeOptions.find((option) => option.id === theme.value)?.icon ?? Laptop)
const themeCycleLabel = computed(() => `Tema: ${themeStatusLabel.value}`)
const themeStatusLabel = computed(() => {
  if (theme.value === 'auto') return `Auto / ${activeTheme.value === 'dark' ? 'Dark' : 'Light'}`
  return theme.value === 'dark' ? 'Dark' : 'Light'
})
const databaseConfiguredLabel = computed(() => {
  const configured = onboardingStatus.value?.database.configured
  if (!configured) return 'Sin datos de conexión'
  const host = configured.host || 'localhost'
  const port = configured.port || '5432'
  return `${configured.engine} · ${configured.name} · ${configured.user}@${host}:${port}`
})
const onboardingChecklist = computed(() => {
  const status = onboardingStatus.value
  return [
    {
      key: 'database',
      label: 'Conexión a DB',
      ok: Boolean(status?.database.connected),
      detail: status?.database.connected ? databaseConfiguredLabel.value : status?.database.message || 'No se pudo conectar con PostgreSQL.',
    },
    {
      key: 'migrations',
      label: 'Migraciones',
      ok: Boolean(status?.migrations.applied),
      detail:
        status?.migrations.pending_count === 0
          ? 'Base de datos al día.'
          : status?.migrations.pending_count == null
            ? 'No se pudieron revisar las migraciones.'
            : `${status.migrations.pending_count} migraciones pendientes.`,
    },
    {
      key: 'initial-config',
      label: 'Configuración inicial',
      ok: Boolean(status?.initial_config.ready),
      detail: status?.initial_config.needs_first_admin
        ? 'Lista para crear el primer admin.'
        : status?.initial_config.has_users
          ? 'Usuarios existentes detectados.'
          : 'Configuración base pendiente.',
    },
  ]
})

const visibleCategories = computed(() => activeCategories.value)
const activeBudgetPeriod = computed(() => budgetPeriodForDate(selectedDate.value, settings.value.cutoff_day))
const currentBudgetPeriod = computed(() => budgetPeriodForDate(todayIso, settings.value.cutoff_day))
const budgetCycleOptions = computed<BudgetCycleOption[]>(() => {
  const period = currentBudgetPeriod.value
  return Array.from({ length: 13 }, (_, index) => {
    const offset = index - 12
    const start = formatIsoDate(addMonths(parseIsoDate(period.start), offset))
    const end = formatIsoDate(addMonths(parseIsoDate(period.end), offset))
    const prefix = offset === 0 ? 'Ciclo actual' : `${Math.abs(offset)} antes`
    return {
      value: start,
      label: `${prefix} · ${formatPeriodLabel(start, end)}`,
      start,
      end,
      offset,
    }
  })
})
const periodRange = computed(() => `${activeBudgetPeriod.value.start} / ${activeBudgetPeriod.value.end}`)
const activePeriodLabel = computed(() => formatPeriodLabel(activeBudgetPeriod.value.start, activeBudgetPeriod.value.end))
const canShiftToPreviousCycle = computed(() => activeBudgetPeriod.value.start > (budgetCycleOptions.value[0]?.start ?? activeBudgetPeriod.value.start))
const canShiftToNextCycle = computed(() => activeBudgetPeriod.value.start < currentBudgetPeriod.value.start)
const overspent = computed(() => summary.value?.categories.filter((category) => category.is_overspent) ?? [])
const planSummaryCopy = computed(() => {
  if (!summary.value) return 'Carga tu plan para ver cómo va la casa.'
  const available = summary.value.totals.available_cents
  if (available < 0) {
    return 'La casa ya rebasó el plan de este periodo. Conviene revisar las categorías en rojo antes del siguiente gasto.'
  }
  if (overspent.value.length) {
    return 'Todavía hay margen, pero una categoría necesita atención antes de seguir gastando.'
  }
  return 'La casa va dentro del plan. Registra los gastos cuando pasen para mantener este número confiable.'
})
const planAttentionItems = computed(() => {
  const items = overspent.value.slice(0, 2).map((category) => ({
    key: `overspent-${category.category_id}`,
    tone: 'danger',
    title: category.category_name,
    body: `Va ${money(Math.abs(category.available_cents), settings.value.currency)} arriba del plan.`,
  }))
  const upcomingCharges = expectedCharges.value
    .filter((charge) => charge.source_type === 'recurring')
    .slice(0, 2)
    .map((charge) => ({
      key: `charge-${charge.key}`,
      tone: 'warm',
      title: charge.name,
      body: `${money(charge.amount_cents, settings.value.currency)} pendiente este periodo.`,
    }))
  return [...items, ...upcomingCharges].slice(0, 3)
})
const recentExpenses = computed(() =>
  transactions.value.filter((transaction) => transaction.transaction_type === 'expense').slice(0, 20),
)
const selectedDateExpenseTotal = computed(() =>
  recentExpenses.value
    .filter((transaction) => transaction.date === selectedDate.value)
    .reduce((total, transaction) => total + transaction.amount_cents, 0),
)
const recurringExpectedCharges = computed(() =>
  expectedCharges.value.filter((charge) => charge.source_type === 'recurring'),
)
const recurringExpectedTotal = computed(() =>
  recurringExpectedCharges.value.reduce((total, charge) => total + charge.amount_cents, 0),
)
const projectedInstallmentPeriods = computed(() => installmentProjection.value?.periods ?? [])
const projectedInstallmentPlans = computed(() =>
  (installmentProjection.value?.plans ?? []).filter((plan) => plan.projected_total_cents || plan.current_amount_cents),
)
const currentInstallmentTotal = computed(() => installmentProjection.value?.current_total_cents ?? 0)
const registeredInstallmentTotal = computed(() =>
  projectedInstallmentPlans.value.reduce((total, plan) => total + plan.total_amount_cents, 0),
)
const currentCommitmentTotal = computed(() => recurringExpectedTotal.value + currentInstallmentTotal.value)
const maxProjectedPeriodTotal = computed(() =>
  Math.max(1, ...projectedInstallmentPeriods.value.map((period) => period.total_cents)),
)
const totalAccountBalance = computed(() =>
  activeAccounts.value.reduce((total, account) => total + account.current_balance_cents, 0),
)
const filteredExpenseCategories = computed(() => {
  const query = expenseCategorySearch.value.trim().toLowerCase()
  if (!query) return visibleCategories.value
  return visibleCategories.value.filter((category) => {
    return `${category.name} ${category.member_name ?? ''}`.toLowerCase().includes(query)
  })
})
const filteredExpenseAccounts = computed(() => {
  const query = expenseAccountSearch.value.trim().toLowerCase()
  if (!query) return activeAccounts.value
  return activeAccounts.value.filter((account) => {
    return `${account.name} ${account.account_type}`.toLowerCase().includes(query)
  })
})
const merchantConceptSuggestions = computed(() => {
  const query = lookupText(merchantValueForTarget())
  return merchantConcepts.value
    .filter((concept) => {
      const name = lookupText(concept.name)
      if (query && name === query) return false
      return !query || name.includes(query)
    })
    .slice(0, 6)
})
const accountFormTitle = computed(() => (editingAccountId.value ? 'Editar cuenta' : 'Crear cuenta'))
const accountSubmitLabel = computed(() => {
  if (actionBusy.value === 'account') return 'Guardando...'
  return editingAccountId.value ? 'Guardar cambios' : 'Crear cuenta'
})
const memberFormTitle = computed(() => (editingMemberId.value ? 'Editar persona' : 'Crear persona'))
const memberSubmitLabel = computed(() => {
  if (actionBusy.value === 'member') return 'Guardando...'
  return editingMemberId.value ? 'Guardar cambios' : 'Crear persona'
})
const selectedCategoryIcon = computed(() => getCategoryIcon(categoryForm.icon))
const categoryFormTitle = computed(() => (editingCategoryId.value ? 'Editar categoría' : 'Crear categoría'))
const categorySubmitLabel = computed(() => {
  if (actionBusy.value === 'category') return 'Guardando...'
  return editingCategoryId.value ? 'Guardar cambios' : 'Crear categoría'
})
const filteredCategoryIcons = computed(() => {
  const query = iconSearch.value.trim().toLowerCase()
  if (!query) return categoryIcons
  return categoryIcons.filter((icon) => {
    return `${icon.id} ${icon.label} ${icon.group} ${icon.search}`.toLowerCase().includes(query)
  })
})
const selectedCategory = computed(() =>
  summary.value?.categories.find((category) => category.category_id === selectedCategoryId.value) ?? null,
)
const selectedCategoryTransactions = computed(() => {
  if (!selectedCategory.value || !summary.value) return []
  const start = summary.value.period.start
  const end = summary.value.period.end
  return transactions.value.filter((transaction) => {
    return (
      transaction.category === selectedCategory.value?.category_id &&
      transaction.date >= start &&
      transaction.date <= end &&
      transaction.transaction_type === 'expense'
    )
  })
})

onMounted(async () => {
  systemThemeMediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  updateSystemTheme(systemThemeMediaQuery)
  systemThemeMediaQuery.addEventListener('change', updateSystemTheme)
  await store.bootstrap()
  settingsForm.cutoff_day = settings.value.cutoff_day
  if (inviteToken.value && !user.value && !firstRunClaimRequired.value) {
    await resolveCurrentInvitation()
  }
  document.addEventListener('visibilitychange', handleVisibilityChange)
  window.addEventListener('pointerdown', handleAuthActivity, { passive: true })
  window.addEventListener('keydown', handleAuthActivity)
})

watch(selectedDate, async () => {
  selectedCategoryId.value = null
  if (!user.value) return
  try {
    await refreshSelectedPeriod()
  } catch {
    showNotice('No pudimos actualizar el periodo. Intenta de nuevo.', 'error')
  }
})

watch(iconGalleryOpen, (isOpen) => {
  document.body.classList.toggle('modal-open', isOpen)
})

watch(
  () => [theme.value, activeTheme.value] as const,
  ([nextTheme, nextActiveTheme]) => applyThemePreference(nextTheme, nextActiveTheme),
  { immediate: true },
)

watch(
  user,
  (nextUser) => {
    if (nextUser) {
      startAuthRefreshLoop()
      return
    }
    stopAuthRefreshLoop()
  },
  { immediate: true },
)

watch(
  () => [settingsPanel.value, canManageSettings.value] as const,
  ([nextPanel, canManage]) => {
    if (nextPanel === 'invitations' && canManage) {
      void loadInvitations()
    }
  },
)

onUnmounted(() => {
  document.body.classList.remove('modal-open')
  if (merchantSuggestionsTimer) window.clearTimeout(merchantSuggestionsTimer)
  if (copiedInvitationTimer) window.clearTimeout(copiedInvitationTimer)
  stopAuthRefreshLoop()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  window.removeEventListener('pointerdown', handleAuthActivity)
  window.removeEventListener('keydown', handleAuthActivity)
  systemThemeMediaQuery?.removeEventListener('change', updateSystemTheme)
})

function normalizeText(value: string) {
  return value.trim()
}

function lookupText(value: string) {
  return normalizeText(value).toLocaleLowerCase('es-MX')
}

function inviteTokenFromLocation() {
  const params = new URLSearchParams(window.location.search)
  const queryToken = params.get('invite')
  if (queryToken?.trim()) return queryToken.trim()
  const match = window.location.pathname.match(/^\/invite\/([^/?#]+)/)
  if (!match?.[1]) return ''
  try {
    return decodeURIComponent(match[1])
  } catch {
    return match[1]
  }
}

function clearInviteFromUrl() {
  if (!inviteToken.value) return
  const nextUrl = new URL(window.location.href)
  nextUrl.searchParams.delete('invite')
  if (nextUrl.pathname.startsWith('/invite/')) {
    nextUrl.pathname = '/'
  }
  window.history.replaceState({}, '', `${nextUrl.pathname}${nextUrl.search}${nextUrl.hash}`)
  inviteToken.value = ''
}

function startAuthRefreshLoop() {
  stopAuthRefreshLoop()
  if (!user.value) return
  authRefreshTimer = window.setInterval(() => {
    void quietlyRefreshAuth('interval', true)
  }, AUTH_REFRESH_INTERVAL_MS)
}

function stopAuthRefreshLoop() {
  if (!authRefreshTimer) return
  window.clearInterval(authRefreshTimer)
  authRefreshTimer = undefined
}

async function quietlyRefreshAuth(reason: 'interval' | 'visible' | 'activity', force = false) {
  if (!user.value) return
  try {
    await store.refreshAuth({ reason, force })
  } catch {
    // Interactive actions already surface errors. Background refresh should not interrupt a parent mid-capture.
  }
}

function handleVisibilityChange() {
  if (document.visibilityState === 'visible') {
    void quietlyRefreshAuth('visible', true)
  }
}

function handleAuthActivity() {
  if (!user.value || document.visibilityState !== 'visible') return
  const now = Date.now()
  if (now - lastActivityRefreshAttempt < AUTH_ACTIVITY_REFRESH_MS) return
  lastActivityRefreshAttempt = now
  void quietlyRefreshAuth('activity')
}

function storedThemePreference(): ThemePreference {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY)
    return stored === 'auto' || stored === 'light' || stored === 'dark' ? stored : 'auto'
  } catch {
    return 'auto'
  }
}

function preferredSystemTheme(): ResolvedTheme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function updateSystemTheme(event: MediaQueryList | MediaQueryListEvent) {
  systemTheme.value = event.matches ? 'dark' : 'light'
}

function applyThemePreference(nextTheme: ThemePreference, nextActiveTheme: ResolvedTheme) {
  document.documentElement.dataset.theme = nextActiveTheme
  document.documentElement.dataset.themePreference = nextTheme
  document.documentElement.style.colorScheme = nextActiveTheme
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme)
  } catch {
    // Local storage can be unavailable in private browsing contexts.
  }
}

function selectThemePreference(nextTheme: ThemePreference) {
  theme.value = nextTheme
}

function cycleThemePreference() {
  const currentIndex = themeOptions.findIndex((option) => option.id === theme.value)
  const nextOption = themeOptions[(currentIndex + 1) % themeOptions.length]
  theme.value = nextOption.id
}

function parseIsoDate(value: string) {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function formatIsoDate(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function addMonths(value: Date, months: number) {
  return new Date(value.getFullYear(), value.getMonth() + months, value.getDate())
}

function budgetPeriodForDate(value: string, cutoffDay: number) {
  const dateValue = parseIsoDate(value)
  const safeCutoff = Math.min(28, Math.max(1, cutoffDay || 20))
  if (dateValue.getDate() <= safeCutoff) {
    const end = new Date(dateValue.getFullYear(), dateValue.getMonth(), safeCutoff)
    const previousEnd = addMonths(end, -1)
    const start = new Date(previousEnd.getFullYear(), previousEnd.getMonth(), safeCutoff + 1)
    return { start: formatIsoDate(start), end: formatIsoDate(end) }
  }
  const start = new Date(dateValue.getFullYear(), dateValue.getMonth(), safeCutoff + 1)
  const end = addMonths(new Date(dateValue.getFullYear(), dateValue.getMonth(), safeCutoff), 1)
  return { start: formatIsoDate(start), end: formatIsoDate(end) }
}

function formatPeriodLabel(start: string, end: string) {
  const formatter = new Intl.DateTimeFormat('es-MX', { day: '2-digit', month: 'short', year: 'numeric' })
  return `${formatter.format(parseIsoDate(start))} - ${formatter.format(parseIsoDate(end))}`
}

function scrollToTop() {
  window.scrollTo({
    top: 0,
    behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
  })
}

function showNotice(message: string, type: NoticeType = 'success') {
  if (noticeTimer) window.clearTimeout(noticeTimer)
  notice.type = type
  notice.message = message
  noticeTimer = type === 'error' ? undefined : window.setTimeout(clearNotice, 4200)
}

function clearNotice() {
  if (noticeTimer) window.clearTimeout(noticeTimer)
  noticeTimer = undefined
  notice.message = ''
}

function merchantValueForTarget(target = merchantSuggestionTarget.value) {
  if (target === 'recurring') return recurringForm.merchant
  if (target === 'installment') return installmentForm.merchant
  return expenseForm.merchant
}

function setMerchantValueForTarget(target: MerchantSuggestionTarget, value: string) {
  if (target === 'recurring') {
    recurringForm.merchant = value
    return
  }
  if (target === 'installment') {
    installmentForm.merchant = value
    return
  }
  expenseForm.merchant = value
}

function showMerchantSuggestionList(target: MerchantSuggestionTarget) {
  return merchantSuggestionsOpen.value && merchantSuggestionTarget.value === target && merchantConceptSuggestions.value.length > 0
}

function openMerchantSuggestions(target: MerchantSuggestionTarget = 'expense') {
  if (merchantSuggestionsTimer) window.clearTimeout(merchantSuggestionsTimer)
  merchantSuggestionTarget.value = target
  merchantSuggestionsOpen.value = true
}

function closeMerchantSuggestionsSoon() {
  if (merchantSuggestionsTimer) window.clearTimeout(merchantSuggestionsTimer)
  merchantSuggestionsTimer = window.setTimeout(() => {
    merchantSuggestionsOpen.value = false
  }, 120)
}

function chooseMerchantConcept(name: string) {
  if (merchantSuggestionsTimer) window.clearTimeout(merchantSuggestionsTimer)
  setMerchantValueForTarget(merchantSuggestionTarget.value, name)
  merchantSuggestionsOpen.value = false
}

async function runAction(key: string, successMessage: string, action: () => Promise<void>) {
  if (actionBusy.value) return
  actionBusy.value = key
  clearNotice()
  try {
    await action()
    showNotice(successMessage)
  } catch (err) {
    showNotice(apiErrorMessage(err, 'No pudimos guardar el cambio. Revisa los datos e intenta de nuevo.'), 'error')
  } finally {
    actionBusy.value = ''
  }
}

async function refreshSelectedPeriod() {
  if (!user.value) return
  await store.fetchAll(selectedDate.value, selectedScope.value)
}

async function submitClaim() {
  const fullName = normalizeText(claimForm.full_name)
  const displayName = normalizeText(claimForm.display_name)
  const email = normalizeText(claimForm.email)
  const password = normalizeText(claimForm.password)
  if (!fullName || !displayName || !email || !password) {
    showNotice('Completa nombre, nombre visible, email y password para reclamar la instalación.', 'error')
    return
  }
  if (password !== claimForm.confirmPassword) {
    showNotice('Los passwords no coinciden.', 'error')
    return
  }
  await runAction('claim', 'Burn Rate quedó listo para tu casa.', async () => {
    await store.claimFirstRun({ full_name: fullName, display_name: displayName, email, password })
    claimForm.password = ''
    claimForm.confirmPassword = ''
    settingsForm.cutoff_day = settings.value.cutoff_day
  })
}

async function refreshOnboardingStatus() {
  await runAction('onboarding-status', 'Revisión actualizada.', async () => {
    await store.fetchOnboardingStatus()
  })
}

async function submitLogin() {
  await runAction('login', 'Listo. Entraste a Burn Rate.', async () => {
    await store.login(loginForm.email, loginForm.password)
    loginForm.password = ''
    settingsForm.cutoff_day = settings.value.cutoff_day
  })
}

async function resolveCurrentInvitation() {
  if (!inviteToken.value) return
  inviteLoading.value = true
  clearNotice()
  try {
    const invitation = await store.resolveInvitation(inviteToken.value)
    acceptInviteForm.full_name = invitation.full_name || ''
    acceptInviteForm.display_name = invitation.display_name || ''
  } catch (err) {
    showNotice(apiErrorMessage(err, 'No pudimos abrir esa invitación. Pide que te manden un link nuevo.'), 'error')
  } finally {
    inviteLoading.value = false
  }
}

async function submitInvitationAccept() {
  const invitation = resolvedInvitation.value
  if (!invitation) return
  const fullName = normalizeText(acceptInviteForm.full_name)
  const displayName = normalizeText(acceptInviteForm.display_name)
  const password = normalizeText(acceptInviteForm.password)
  if (!fullName || !displayName || !password) {
    showNotice('Completa tu nombre, nombre visible y un password.', 'error')
    return
  }
  if (password !== acceptInviteForm.confirmPassword) {
    showNotice('Los passwords no coinciden.', 'error')
    return
  }
  await runAction('accept-invite', 'Invitación aceptada. Entraste a Burn Rate.', async () => {
    await store.acceptInvitation({
      token: invitation.token ?? inviteToken.value,
      email: invitation.email,
      full_name: fullName,
      display_name: displayName,
      password,
    })
    acceptInviteForm.password = ''
    acceptInviteForm.confirmPassword = ''
    clearInviteFromUrl()
    settingsForm.cutoff_day = settings.value.cutoff_day
  })
}

async function loadInvitations() {
  if (!canManageSettings.value) return
  try {
    await store.fetchInvitations()
  } catch (err) {
    showNotice(apiErrorMessage(err, 'No pudimos cargar las invitaciones.'), 'error')
  }
}

async function submitInvitation() {
  const email = normalizeText(invitationForm.email)
  if (!email) {
    showNotice('Escribe el email para la invitación.', 'error')
    return
  }
  await runAction('invitation', 'Invitación lista.', async () => {
    const invitation = await store.createInvitation({
      email,
      is_admin: invitationForm.is_admin,
    })
    createdInvitationLink.value = invitationLink(invitation)
    invitationForm.email = ''
    invitationForm.is_admin = false
  })
}

function invitationLink(invitation: Pick<Invitation, 'accept_url' | 'url' | 'link' | 'token'>) {
  const rawLink = invitation.accept_url || invitation.url || invitation.link
  if (rawLink?.startsWith('http://') || rawLink?.startsWith('https://')) return rawLink
  if (rawLink?.startsWith('/')) return new URL(rawLink, window.location.origin).toString()
  if (invitation.token) return new URL(`/invite/${encodeURIComponent(invitation.token)}`, window.location.origin).toString()
  return rawLink ?? ''
}

async function copyInvitationLink(link: string, id: number | string) {
  if (!link) {
    showNotice('Esta invitación todavía no tiene link para copiar.', 'error')
    return
  }
  try {
    await navigator.clipboard.writeText(link)
    copiedInvitationId.value = id
    if (copiedInvitationTimer) window.clearTimeout(copiedInvitationTimer)
    copiedInvitationTimer = window.setTimeout(() => {
      copiedInvitationId.value = null
    }, 2400)
    showNotice('Link copiado.', 'success')
  } catch {
    showNotice('No pudimos copiar el link. Puedes seleccionarlo manualmente.', 'error')
  }
}

async function deleteInvitation(invitation: Invitation) {
  if (invitation.accepted_at) {
    showNotice('No se puede eliminar una invitación aceptada.', 'error')
    return
  }
  if (!window.confirm(`Eliminar la invitación para ${invitation.email}?`)) return
  await runAction(`delete-invitation-${invitation.id}`, 'Invitación eliminada.', async () => {
    await store.deleteInvitation(invitation.id)
    if (copiedInvitationId.value === invitation.id) copiedInvitationId.value = null
  })
}

function selectInputText(event: FocusEvent) {
  if (event.target instanceof HTMLInputElement) {
    event.target.select()
  }
}

async function submitExpense() {
  const merchant = normalizeText(expenseForm.merchant)
  const amountCents = centsFromInput(expenseForm.amount)
  if (!merchant) {
    showNotice('Escribe un comercio o concepto.', 'error')
    return
  }
  if (amountCents <= 0) {
    showNotice('Escribe un monto mayor a cero.', 'error')
    return
  }
  if (!expenseForm.category || !expenseForm.account) {
    showNotice('Elige una categoría y una cuenta antes de guardar.', 'error')
    return
  }
  await runAction('expense', 'Gasto guardado. El plan ya está actualizado.', async () => {
    await store.createTransaction({
      transaction_type: 'expense',
      merchant,
      amount_cents: amountCents,
      date: expenseForm.date,
      account: Number(expenseForm.account),
      category: Number(expenseForm.category),
      note: expenseForm.note,
    })
    expenseForm.merchant = ''
    expenseForm.amount = ''
    expenseForm.note = ''
    merchantSuggestionsOpen.value = false
    expensesTab.value = 'feed'
  })
}

async function submitAccount() {
  const name = normalizeText(accountForm.name)
  if (!name) {
    showNotice('Escribe un nombre para la cuenta.', 'error')
    return
  }
  await runAction('account', editingAccountId.value ? 'Cuenta actualizada.' : 'Cuenta guardada para la casa.', async () => {
    const payload = {
      name,
      account_type: accountForm.account_type,
      initial_balance_cents: accountForm.account_type === 'cash' ? centsFromInput(accountForm.initial_balance || '0') : 0,
      color: accountForm.color,
      is_active: accountForm.is_active,
    }
    if (editingAccountId.value) {
      await store.updateAccount(editingAccountId.value, payload)
    } else {
      await store.createAccount(payload)
    }
    resetAccountForm()
  })
}

function editAccount(account: Account) {
  editingAccountId.value = account.id
  accountForm.name = account.name
  accountForm.account_type = account.account_type
  accountForm.initial_balance = String(account.initial_balance_cents / 100)
  accountForm.color = account.color || '#7c6250'
  accountForm.is_active = account.is_active
}

function resetAccountForm() {
  editingAccountId.value = null
  accountForm.name = ''
  accountForm.account_type = 'cash'
  accountForm.initial_balance = ''
  accountForm.color = '#7c6250'
  accountForm.is_active = true
}

function accountTypeLabel(accountType: string) {
  if (accountType === 'cash') return 'Efectivo'
  if (accountType === 'bank') return 'Banco'
  if (accountType === 'debit_card') return 'Tarjeta débito'
  if (accountType === 'credit_card') return 'Tarjeta crédito'
  return accountType
}

function setMemberAccess(enabled: boolean) {
  memberForm.has_access = enabled
  if (!enabled) memberForm.is_admin = false
}

function setMemberAdmin(enabled: boolean) {
  memberForm.is_admin = enabled
  if (enabled) memberForm.has_access = true
}

function setMemberAccessFromEvent(event: Event) {
  setMemberAccess(event.target instanceof HTMLInputElement ? event.target.checked : false)
}

function setMemberAdminFromEvent(event: Event) {
  setMemberAdmin(event.target instanceof HTMLInputElement ? event.target.checked : false)
}

async function submitMember() {
  const name = normalizeText(memberForm.name)
  const username = normalizeText(memberForm.username)
  const email = normalizeText(memberForm.email)
  const password = normalizeText(memberForm.password)
  if (!name) {
    showNotice('Escribe el nombre de la persona.', 'error')
    return
  }
  if (memberForm.is_admin) memberForm.has_access = true
  if (memberForm.has_access && !username) {
    showNotice('Hace falta usuario para dar acceso.', 'error')
    return
  }
  if (!editingMemberId.value && memberForm.has_access && !password) {
    showNotice('Hace falta clave temporal para dar acceso.', 'error')
    return
  }
  await runAction('member', editingMemberId.value ? 'Persona actualizada.' : 'Persona guardada.', async () => {
    const payload = {
      name,
      color: memberForm.color,
      is_active: true,
      has_access: memberForm.has_access,
      username: memberForm.has_access ? username : '',
      email: memberForm.has_access ? email : '',
      password: memberForm.has_access ? password : '',
      is_admin: memberForm.is_admin,
    }
    if (editingMemberId.value) {
      await store.updateMember(editingMemberId.value, payload)
    } else {
      await store.createMember(payload)
    }
    resetMemberForm()
  })
}

function editMember(member: HouseholdMember) {
  editingMemberId.value = member.id
  memberForm.name = member.name
  memberForm.color = member.color
  memberForm.has_access = member.access_enabled
  memberForm.username = member.user_username || usernameSuggestionFromName(member.name)
  memberForm.email = member.user_email || ''
  memberForm.password = ''
  memberForm.is_admin = member.user_is_admin
}

function resetMemberForm() {
  editingMemberId.value = null
  memberForm.name = ''
  memberForm.color = '#b35320'
  memberForm.has_access = false
  memberForm.username = ''
  memberForm.email = ''
  memberForm.password = ''
  memberForm.is_admin = false
}

function usernameSuggestionFromName(name: string) {
  return name
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

async function submitCategory() {
  const name = normalizeText(categoryForm.name)
  const memberId = categoryForm.scope === 'personal' ? Number(categoryForm.member) : null
  const monthlyBudgetCents = centsFromInput(categoryForm.monthly_budget)
  if (!name) {
    showNotice('Escribe un nombre para la categoría.', 'error')
    return
  }
  if (categoryForm.scope === 'personal' && !memberId) {
    showNotice('Elige una persona para esta categoría personal.', 'error')
    return
  }
  if (monthlyBudgetCents <= 0) {
    showNotice('Escribe un presupuesto mensual mayor a cero.', 'error')
    return
  }
  await runAction('category', editingCategoryId.value ? 'Categoría actualizada.' : 'Categoría guardada en el plan.', async () => {
    const payload = {
      name,
      scope: categoryForm.scope as 'global' | 'personal',
      member: memberId,
      monthly_budget_cents: monthlyBudgetCents,
      color: categoryForm.color,
      icon: categoryForm.icon,
      is_active: categoryForm.is_active,
      order: 0,
    }
    if (editingCategoryId.value) {
      await store.updateCategory(editingCategoryId.value, payload)
    } else {
      await store.createCategory(payload)
    }
    resetCategoryForm()
  })
}

function editCategory(category: Category) {
  editingCategoryId.value = category.id
  categoryForm.name = category.name
  categoryForm.scope = category.scope
  categoryForm.member = category.member ? String(category.member) : ''
  categoryForm.monthly_budget = String(category.monthly_budget_cents / 100)
  categoryForm.color = category.color
  categoryForm.icon = category.icon || 'tag'
  categoryForm.is_active = category.is_active
}

function resetCategoryForm() {
  editingCategoryId.value = null
  categoryForm.name = ''
  categoryForm.scope = 'global'
  categoryForm.member = ''
  categoryForm.monthly_budget = ''
  categoryForm.color = '#e11d48'
  categoryForm.icon = 'tag'
  categoryForm.is_active = true
}

async function submitRecurring() {
  const name = normalizeText(recurringForm.name)
  const merchant = normalizeText(recurringForm.merchant)
  const amountCents = centsFromInput(recurringForm.amount)
  const chargeDay = Math.min(28, Math.max(1, Number(recurringForm.charge_day) || 1))
  if (!name) {
    showNotice('Escribe un nombre para el cargo mensual.', 'error')
    return
  }
  if (!merchant) {
    showNotice('Escribe el comercio del cargo mensual.', 'error')
    return
  }
  if (amountCents <= 0) {
    showNotice('Escribe un monto mensual mayor a cero.', 'error')
    return
  }
  if (recurringForm.end_date && recurringForm.end_date < recurringForm.start_date) {
    showNotice('La fecha final no puede ir antes del inicio.', 'error')
    return
  }
  await runAction('recurring', 'Cargo mensual guardado.', async () => {
    await store.createRecurring({
      name,
      merchant,
      amount_cents: amountCents,
      category: Number(recurringForm.category),
      account: recurringForm.account ? Number(recurringForm.account) : null,
      start_date: recurringForm.start_date,
      end_date: recurringForm.end_date || null,
      charge_day: chargeDay,
      is_active: true,
    })
    recurringForm.name = ''
    recurringForm.merchant = ''
    recurringForm.amount = ''
    showCommitmentForm.value = false
    commitmentTab.value = 'subscriptions'
  })
}

async function submitInstallment() {
  const name = normalizeText(installmentForm.name)
  const merchant = normalizeText(installmentForm.merchant)
  const totalAmountCents = centsFromInput(installmentForm.total_amount)
  const firstPaymentNumber = Number(installmentForm.first_payment_number)
  if (!name) {
    showNotice('Escribe un nombre para la compra a meses.', 'error')
    return
  }
  if (!merchant) {
    showNotice('Escribe el comercio de la compra a meses.', 'error')
    return
  }
  if (totalAmountCents <= 0) {
    showNotice('Escribe un monto total mayor a cero.', 'error')
    return
  }
  if (!Number.isInteger(firstPaymentNumber) || firstPaymentNumber < 1) {
    showNotice('Indica el número de pago inicial.', 'error')
    return
  }
  if (installmentForm.end_date < installmentForm.start_date) {
    showNotice('La fecha final no puede ir antes del inicio.', 'error')
    return
  }
  await runAction('installment', 'Compra a meses guardada.', async () => {
    await store.createInstallment({
      name,
      merchant,
      total_amount_cents: totalAmountCents,
      category: Number(installmentForm.category),
      account: installmentForm.account ? Number(installmentForm.account) : null,
      start_date: installmentForm.start_date,
      end_date: installmentForm.end_date,
      first_payment_number: firstPaymentNumber,
      is_active: true,
    })
    installmentForm.name = ''
    installmentForm.merchant = ''
    installmentForm.total_amount = ''
    installmentForm.first_payment_number = '1'
    showCommitmentForm.value = false
    commitmentTab.value = 'msi'
  })
}

async function saveSettings() {
  const cutoffDay = Math.min(28, Math.max(1, Number(settingsForm.cutoff_day) || 1))
  await runAction('settings', 'Día de corte actualizado.', async () => {
    await store.saveSettings({ ...settings.value, cutoff_day: cutoffDay })
    await refreshSelectedPeriod()
  })
}

async function confirmCharge(charge: ExpectedCharge) {
  const fallback = charge.account?.id ?? activeAccounts.value[0]?.id
  if (!fallback) {
    showNotice('No hay una cuenta activa para marcar este cargo como pagado.', 'error')
    return
  }
  await runAction(`charge-${charge.key}`, `${charge.name} marcado como pagado.`, async () => {
    await store.confirmCharge(charge, fallback)
  })
}

async function dismissCharge(charge: ExpectedCharge) {
  await runAction(`dismiss-${charge.key}`, `${charge.name} omitido para este periodo.`, async () => {
    await store.dismissCharge(charge)
  })
}

function selectView(nextView: View) {
  view.value = nextView
  selectedCategoryId.value = null
  scrollToTop()
}

function goToExpenseCaptureForSelectedCategory() {
  if (!selectedCategory.value) return
  goToExpenseCaptureForCategory(selectedCategory.value.category_id)
}

function goToExpenseCaptureForCategory(categoryId: number) {
  expenseForm.category = String(categoryId)
  expenseForm.date = selectedDate.value
  view.value = 'expenses'
  expensesTab.value = 'capture'
  selectedCategoryId.value = null
  scrollToTop()
}

function selectBudgetCycle(event: Event) {
  const target = event.target
  if (target instanceof HTMLSelectElement) {
    selectedDate.value = target.value
  }
}

function shiftBudgetCycle(offset: number) {
  if (offset < 0 && !canShiftToPreviousCycle.value) return
  if (offset > 0 && !canShiftToNextCycle.value) return
  const currentStart = parseIsoDate(activeBudgetPeriod.value.start)
  const nextStart = formatIsoDate(addMonths(currentStart, offset))
  selectedDate.value = nextStart > currentBudgetPeriod.value.start ? currentBudgetPeriod.value.start : nextStart
}

function syncPlanSummary(event: Event) {
  if (event.target instanceof HTMLDetailsElement) {
    showPlanSummary.value = event.target.open
  }
}

function openCommitmentForm(kind: CommitmentKind) {
  commitmentKind.value = kind
  showCommitmentForm.value = true
  scrollToTop()
}

function closeCommitmentForm() {
  showCommitmentForm.value = false
}

function chooseExpenseCategory(categoryId: number) {
  expenseForm.category = String(categoryId)
}

function chooseExpenseAccount(accountId: number) {
  expenseForm.account = String(accountId)
}

function openIconGallery(event?: MouseEvent) {
  iconGalleryOpener.value = event?.currentTarget instanceof HTMLElement ? event.currentTarget : null
  iconSearch.value = ''
  iconGalleryOpen.value = true
  nextTick(() => {
    iconGalleryDialog.value?.querySelector<HTMLInputElement>('input[type="search"]')?.focus()
  })
}

function closeIconGallery() {
  iconGalleryOpen.value = false
  nextTick(() => iconGalleryOpener.value?.focus())
}

function selectCategoryIcon(iconId: string) {
  categoryForm.icon = iconId
  closeIconGallery()
}

function handleIconGalleryKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.preventDefault()
    closeIconGallery()
    return
  }
  if (event.key !== 'Tab' || !iconGalleryDialog.value) return
  const focusable = Array.from(
    iconGalleryDialog.value.querySelectorAll<HTMLElement>(
      'button, input, select, textarea, [tabindex]:not([tabindex="-1"])',
    ),
  ).filter((element) => !element.hasAttribute('disabled') && element.offsetParent !== null)
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (!first || !last) return
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

function installmentProgressPercent(plan: { current_payment_number?: number | null; payments_total: number }) {
  if (!plan.current_payment_number || !plan.payments_total) return 0
  return Math.max(0, Math.min(100, Math.round((plan.current_payment_number / plan.payments_total) * 100)))
}

function projectionBarWidth(total: number) {
  if (!total) return '0%'
  return `${Math.max(8, Math.round((total / maxProjectedPeriodTotal.value) * 100))}%`
}

function projectionPeriodLabel(index: number) {
  return index === 0 ? 'Act.' : `+${index}`
}

function projectionPaymentCountLabel(count: number) {
  if (count === 1) return '1 pago MSI'
  return `${count} pagos MSI`
}

function projectionSettledPlans(period: { plans: Array<{ name: string; remaining_payments: number }> }) {
  return period.plans.filter((plan) => plan.remaining_payments === 0)
}

function projectionSettledLabel(period: { plans: Array<{ name: string; remaining_payments: number }> }) {
  const settled = projectionSettledPlans(period)
  if (!settled.length) return ''
  const names = settled.slice(0, 2).map((plan) => plan.name).join(', ')
  const extra = settled.length > 2 ? ` +${settled.length - 2}` : ''
  return `Liquida ${names}${extra}`
}

function categoryIconComponent(icon?: string | null) {
  return getCategoryIcon(icon).component
}
</script>

<template>
  <main v-if="!authReady" class="login-shell">
    <section class="login-panel auth-panel">
      <button class="login-theme-button" type="button" :aria-label="themeCycleLabel" :title="themeCycleLabel" @click="cycleThemePreference">
        <component :is="themeCycleIcon" aria-hidden="true" />
      </button>
      <div class="login-brand">
        <img class="login-logo" :src="themeLogo" alt="Burn Rate" width="400" height="430" />
        <div>
          <h1 class="sr-only">Burn Rate</h1>
          <p>Presupuesto familiar con corte claro.</p>
        </div>
      </div>
      <p class="auth-state-line" role="status">Preparando Burn Rate...</p>
    </section>
  </main>

  <main v-else-if="!onboardingReady" class="login-shell">
    <section class="login-panel onboarding-panel">
      <button class="login-theme-button" type="button" :aria-label="themeCycleLabel" :title="themeCycleLabel" @click="cycleThemePreference">
        <component :is="themeCycleIcon" aria-hidden="true" />
      </button>
      <div class="login-brand">
        <img class="login-logo" :src="themeLogo" alt="Burn Rate" width="400" height="430" />
        <div>
          <h1>Revisión inicial</h1>
          <p>Verifica que Docker Compose esté apuntando a una base PostgreSQL lista.</p>
        </div>
      </div>
      <section class="onboarding-checklist" aria-label="Estado inicial de Burn Rate">
        <div
          v-for="item in onboardingChecklist"
          :key="item.key"
          class="onboarding-check"
          :class="{ ready: item.ok, blocked: !item.ok }"
        >
          <span aria-hidden="true">{{ item.ok ? 'OK' : '!' }}</span>
          <div>
            <strong>{{ item.label }}</strong>
            <p>{{ item.detail }}</p>
          </div>
        </div>
        <button class="primary expense-primary" type="button" :disabled="actionBusy === 'onboarding-status'" @click="refreshOnboardingStatus">
          {{ actionBusy === 'onboarding-status' ? 'Revisando...' : 'Revisar otra vez' }}
        </button>
        <p class="status-line error" role="alert">
          Ajusta DB_HOST, DB_NAME, DB_USER, DB_PASSWORD y DB_PORT en Docker Compose, reinicia el contenedor y vuelve a revisar.
        </p>
      </section>
    </section>
  </main>

  <main v-else-if="firstRunClaimRequired" class="login-shell">
    <section class="login-panel claim-panel">
      <button class="login-theme-button" type="button" :aria-label="themeCycleLabel" :title="themeCycleLabel" @click="cycleThemePreference">
        <component :is="themeCycleIcon" aria-hidden="true" />
      </button>
      <div class="login-brand">
        <img class="login-logo" :src="themeLogo" alt="Burn Rate" width="400" height="430" />
        <div>
          <h1>Reclamar Burn Rate</h1>
          <p>Crea el primer acceso admin para esta casa.</p>
        </div>
      </div>
      <form class="form-stack login-form" @submit.prevent="submitClaim">
        <section class="onboarding-checklist compact" aria-label="Revisión inicial completa">
          <div v-for="item in onboardingChecklist" :key="item.key" class="onboarding-check ready">
            <span aria-hidden="true">OK</span>
            <div>
              <strong>{{ item.label }}</strong>
              <p>{{ item.detail }}</p>
            </div>
          </div>
        </section>
        <label>
          Nombre completo
          <input v-model="claimForm.full_name" autocomplete="name" placeholder="Luis Hernández" required />
        </label>
        <label>
          Nombre visible
          <input v-model="claimForm.display_name" autocomplete="nickname" placeholder="Papá, Mamá, Casa" required />
        </label>
        <label>
          Email
          <input v-model="claimForm.email" type="email" autocomplete="email" placeholder="papa@example.com" required />
        </label>
        <div class="field-row auth-password-row">
          <label>
            Password
            <input v-model="claimForm.password" type="password" autocomplete="new-password" required />
          </label>
          <label>
            Confirmar
            <input v-model="claimForm.confirmPassword" type="password" autocomplete="new-password" required />
          </label>
        </div>
        <button class="primary expense-primary" type="submit" :disabled="actionBusy === 'claim'">
          {{ actionBusy === 'claim' ? 'Reclamando...' : 'Reclamar instalación' }}
        </button>
        <p v-if="error" class="error-line" role="alert">{{ error }}</p>
        <p v-if="notice.message" class="status-line" :class="notice.type" :role="notice.type === 'error' ? 'alert' : 'status'">
          {{ notice.message }}
        </p>
      </form>
    </section>
  </main>

  <main v-else-if="inviteToken && !user" class="login-shell">
    <section class="login-panel invite-panel">
      <button class="login-theme-button" type="button" :aria-label="themeCycleLabel" :title="themeCycleLabel" @click="cycleThemePreference">
        <component :is="themeCycleIcon" aria-hidden="true" />
      </button>
      <div class="login-brand">
        <img class="login-logo" :src="themeLogo" alt="Burn Rate" width="400" height="430" />
        <div>
          <h1>Invitación</h1>
          <p v-if="resolvedInvitation">Acceso para {{ resolvedInvitation.email }}</p>
          <p v-else>Validando tu link de invitación.</p>
        </div>
      </div>
      <p v-if="inviteLoading" class="auth-state-line" role="status">Abriendo invitación...</p>
      <form v-else-if="resolvedInvitation && !resolvedInvitation.accepted_at" class="form-stack login-form" @submit.prevent="submitInvitationAccept">
        <div v-if="resolvedInvitation.message" class="invite-message">
          {{ resolvedInvitation.message }}
        </div>
        <div class="invite-meta">
          <span>{{ resolvedInvitation.is_admin || resolvedInvitation.is_staff ? 'Acceso admin' : 'Acceso usuario' }}</span>
          <span v-if="resolvedInvitation.expires_at">Vence {{ resolvedInvitation.expires_at }}</span>
        </div>
        <label>
          Nombre completo
          <input v-model="acceptInviteForm.full_name" autocomplete="name" required />
        </label>
        <label>
          Nombre visible
          <input v-model="acceptInviteForm.display_name" autocomplete="nickname" required />
        </label>
        <div class="field-row auth-password-row">
          <label>
            Password
            <input v-model="acceptInviteForm.password" type="password" autocomplete="new-password" required />
          </label>
          <label>
            Confirmar
            <input v-model="acceptInviteForm.confirmPassword" type="password" autocomplete="new-password" required />
          </label>
        </div>
        <button class="primary expense-primary" type="submit" :disabled="actionBusy === 'accept-invite'">
          {{ actionBusy === 'accept-invite' ? 'Aceptando...' : 'Aceptar invitación' }}
        </button>
      </form>
      <div v-else class="form-stack login-form">
        <p class="auth-state-line">Este link no está disponible.</p>
        <button class="secondary" type="button" @click="clearInviteFromUrl">Ir al login</button>
      </div>
      <p v-if="error" class="error-line" role="alert">{{ error }}</p>
      <p v-if="notice.message" class="status-line" :class="notice.type" :role="notice.type === 'error' ? 'alert' : 'status'">
        {{ notice.message }}
      </p>
    </section>
  </main>

  <main v-else-if="!user" class="login-shell">
    <section class="login-panel">
      <button class="login-theme-button" type="button" :aria-label="themeCycleLabel" :title="themeCycleLabel" @click="cycleThemePreference">
        <component :is="themeCycleIcon" aria-hidden="true" />
      </button>
      <div class="login-brand">
        <img class="login-logo" :src="themeLogo" alt="Burn Rate" width="400" height="430" />
        <div>
          <h1 class="sr-only">Burn Rate</h1>
          <p>Presupuesto familiar con corte claro.</p>
        </div>
      </div>
      <form class="form-stack login-form" @submit.prevent="submitLogin">
        <label>
          Email
          <input v-model="loginForm.email" type="email" autocomplete="email" placeholder="papa@example.com" required />
        </label>
        <label>
          Password
          <input v-model="loginForm.password" type="password" autocomplete="current-password" required />
        </label>
        <button class="primary expense-primary" type="submit" :disabled="actionBusy === 'login'">
          {{ actionBusy === 'login' ? 'Entrando...' : 'Entrar' }}
        </button>
        <p v-if="error" class="error-line" role="alert">{{ error }}</p>
        <p v-if="notice.message" class="status-line" :class="notice.type" :role="notice.type === 'error' ? 'alert' : 'status'">
          {{ notice.message }}
        </p>
      </form>
    </section>
  </main>

  <main v-else class="app-shell" :class="`view-${view}`">
    <p v-if="error" class="error-line" role="alert">{{ error }}</p>
    <p v-if="notice.message" class="status-line" :class="notice.type" :role="notice.type === 'error' ? 'alert' : 'status'">
      {{ notice.message }}
    </p>
    <p v-if="loading" class="loading-line" role="status" aria-live="polite">Actualizando la casa...</p>

    <section
      v-if="view === 'budget' && selectedCategory"
      class="screen detail-screen"
      :style="{ '--category-color': selectedCategory.color, '--section-accent': selectedCategory.color }"
      :inert="iconGalleryOpen || undefined"
      :aria-hidden="iconGalleryOpen ? 'true' : undefined"
    >
      <header class="mobile-header compact-header detail-header">
        <button class="square-action" type="button" aria-label="Volver" @click="selectedCategoryId = null">
          <svg viewBox="0 0 24 24"><path d="M15 6l-6 6 6 6" /></svg>
        </button>
        <span class="category-icon detail-icon" :style="{ '--category-color': selectedCategory.color }">
          <component :is="categoryIconComponent(selectedCategory.icon)" aria-hidden="true" />
        </span>
        <div>
          <span>Presupuesto / Categoría</span>
          <h1>{{ selectedCategory.category_name }}</h1>
        </div>
        <button
          class="detail-expense-button"
          type="button"
          :aria-label="`Registrar gasto en ${selectedCategory.category_name}`"
          @click="goToExpenseCaptureForSelectedCategory"
        >
          <svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></svg>
          <span>Gasto</span>
        </button>
      </header>

      <div class="context-chip">
        {{ selectedCategory.member?.name ?? 'Familia' }} · {{ periodRange }}
      </div>

      <section class="budget-hero detail-hero">
        <div class="summary-top">
          <span>Disponible</span>
          <strong>{{ money(selectedCategory.available_cents, settings.currency) }}</strong>
        </div>
        <div class="hero-metrics">
          <article>
            <span>Presupuesto</span>
            <b>{{ money(selectedCategory.budget_cents, settings.currency) }}</b>
          </article>
          <article>
            <span>Gastado</span>
            <b>{{ money(selectedCategory.spent_cents, settings.currency) }}</b>
          </article>
          <article>
            <span>Esperado</span>
            <b>{{ money(selectedCategory.expected_cents, settings.currency) }}</b>
          </article>
        </div>
        <div class="meter hero-meter">
          <i :style="{ width: `${Math.max(0, Math.min(100, selectedCategory.percent_available))}%` }"></i>
        </div>
      </section>

      <div class="section-title-row">
        <h2>Gastos del periodo</h2>
        <span>{{ selectedCategoryTransactions.length }} gastos</span>
      </div>

      <section class="feed">
        <article v-for="transaction in selectedCategoryTransactions" :key="transaction.id" class="feed-row accent-left">
          <div>
            <b>{{ transaction.merchant }}</b>
            <span>{{ transaction.date }} · {{ transaction.account_name }} · {{ transaction.created_by_username ?? 'sin usuario' }}</span>
            <small v-if="transaction.note">{{ transaction.note }}</small>
          </div>
          <strong>{{ money(transaction.amount_cents, settings.currency) }}</strong>
        </article>
        <article v-if="!selectedCategoryTransactions.length" class="empty-card">
          <b>Sin gastos</b>
          <span>Sin gastos en este periodo.</span>
        </article>
      </section>
    </section>

    <section
      v-else-if="view === 'budget'"
      class="screen plan-screen"
      :inert="iconGalleryOpen || undefined"
      :aria-hidden="iconGalleryOpen ? 'true' : undefined"
    >
      <section class="plan-top-section" aria-label="Plan de casa">
        <header class="plan-top-header">
          <h1>Plan de casa</h1>
          <p>{{ activePeriodLabel }}</p>
        </header>

        <div class="plan-cycle-controls" aria-label="Seleccionar ciclo del plan">
          <button
            class="cycle-step-button"
            type="button"
            aria-label="Ciclo anterior"
            :disabled="!canShiftToPreviousCycle"
            @click="shiftBudgetCycle(-1)"
          >
            <svg viewBox="0 0 24 24"><path d="M15 6l-6 6 6 6" /></svg>
          </button>
          <select aria-label="Ciclo del plan" :value="activeBudgetPeriod.start" @change="selectBudgetCycle">
            <option v-for="cycle in budgetCycleOptions" :key="cycle.value" :value="cycle.value">
              {{ cycle.label }}
            </option>
          </select>
          <button
            class="cycle-step-button"
            type="button"
            aria-label="Ciclo siguiente"
            :disabled="!canShiftToNextCycle"
            @click="shiftBudgetCycle(1)"
          >
            <svg viewBox="0 0 24 24"><path d="M9 6l6 6-6 6" /></svg>
          </button>
        </div>
      </section>

      <section class="category-ledger">
        <div class="section-title-row budget-list-title">
          <div>
            <h2>Detalle por categoría</h2>
          </div>
          <span>{{ summary?.categories.length ?? 0 }} activas</span>
        </div>

        <div class="category-grid">
          <article
            v-for="item in summary?.categories"
            :key="item.category_id"
            class="category-card"
            :class="{ danger: item.is_overspent }"
            :style="{ '--category-color': item.color }"
          >
            <button
              class="category-card-main"
              type="button"
              :aria-label="`Abrir ${item.category_name}`"
              @click="selectedCategoryId = item.category_id; scrollToTop()"
            >
              <div class="category-line">
                <span class="category-icon" :style="{ '--category-color': item.color }">
                  <component :is="categoryIconComponent(item.icon)" aria-hidden="true" />
                </span>
                <div>
                  <h2>{{ item.category_name }}</h2>
                  <p>{{ item.spent_cents ? money(item.spent_cents, settings.currency) : '$0.00' }} de {{ money(item.budget_cents, settings.currency) }}</p>
                </div>
                <span class="status-pill" :class="{ warning: item.is_overspent }">
                  {{ item.is_overspent ? 'Revisar' : 'Bien' }}
                </span>
              </div>
              <div class="meter" aria-hidden="true">
                <i :style="{ width: `${Math.max(0, Math.min(100, item.percent_available))}%`, background: item.is_overspent ? '#d64309' : item.color }"></i>
              </div>
              <footer>
                <span>{{ item.member?.name ?? 'Casa' }}</span>
                <strong>{{ money(item.available_cents, settings.currency) }}</strong>
              </footer>
            </button>
            <button
              class="category-card-add"
              type="button"
              :aria-label="`Registrar gasto en ${item.category_name}`"
              @click="goToExpenseCaptureForCategory(item.category_id)"
            >
              <svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></svg>
            </button>
          </article>
        </div>
      </section>

      <section class="attention-panel" :class="{ calm: !planAttentionItems.length }">
        <div class="section-title-row">
          <h2>{{ planAttentionItems.length ? 'Atención de casa' : 'Casa tranquila' }}</h2>
          <span>Casa completa</span>
        </div>
        <div v-if="planAttentionItems.length" class="attention-list">
          <article v-for="item in planAttentionItems" :key="item.key" :class="`tone-${item.tone}`">
            <b>{{ item.title }}</b>
            <span>{{ item.body }}</span>
          </article>
        </div>
        <p v-else>No hay categorías rebasadas ni cargos urgentes en este ciclo.</p>
      </section>

      <details v-if="summary" class="plan-summary-disclosure" :open="showPlanSummary" @toggle="syncPlanSummary">
        <summary>
          <span>{{ showPlanSummary ? 'Ocultar resumen' : 'Mostrar resumen' }}</span>
          <strong :class="{ negative: summary.totals.available_cents < 0 }">
            {{ money(summary.totals.available_cents, settings.currency) }}
          </strong>
        </summary>
        <section class="plan-overview">
          <div class="plan-balance">
            <span>Presupuesto de casa</span>
            <strong :class="{ negative: summary.totals.available_cents < 0 }">
              {{ money(summary.totals.available_cents, settings.currency) }}
            </strong>
            <p>{{ planSummaryCopy }}</p>
          </div>
          <dl class="home-totals">
            <div>
              <dt>Plan del periodo</dt>
              <dd>{{ money(summary.totals.budget_cents, settings.currency) }}</dd>
            </div>
            <div>
              <dt>Ya gastado</dt>
              <dd>{{ money(summary.totals.spent_cents, settings.currency) }}</dd>
            </div>
            <div>
              <dt>Por venir</dt>
              <dd>{{ money(summary.totals.expected_cents, settings.currency) }}</dd>
            </div>
          </dl>
        </section>
      </details>
    </section>

    <section
      v-if="view === 'expenses'"
      class="screen expenses-screen"
      :inert="iconGalleryOpen || undefined"
      :aria-hidden="iconGalleryOpen ? 'true' : undefined"
    >
      <header class="mobile-header">
        <div>
          <span>Burn Rate</span>
          <h1>Gastos</h1>
          <p>{{ expensesTab === 'capture' ? 'Guarda el gasto en pocos pasos. Usa los accesos rápidos si coincide con lo de siempre.' : 'Revisa los gastos recientes y confirma que quedaron en la cuenta correcta.' }}</p>
        </div>
      </header>

      <div class="segmented">
        <button :class="{ active: expensesTab === 'capture' }" type="button" @click="expensesTab = 'capture'">Registro de gasto</button>
        <button :class="{ active: expensesTab === 'feed' }" type="button" @click="expensesTab = 'feed'">Movimientos</button>
      </div>

      <form v-if="expensesTab === 'capture'" class="panel form-stack expense-form" @submit.prevent="submitExpense">
        <section class="choice-block">
          <div class="section-title-row">
            <h2>Categoría</h2>
            <span>{{ expenseForm.category ? 'Lista' : 'Elige una' }}</span>
          </div>

          <label class="search-field category-search-field">
            Buscar categoría
            <input v-model="expenseCategorySearch" type="search" placeholder="Comida, gas, internet" autocomplete="off" />
          </label>

          <div class="choice-chips category-card-list" role="list">
            <button
              v-for="category in filteredExpenseCategories"
              :key="category.id"
              type="button"
              :class="{ active: String(category.id) === expenseForm.category }"
              :style="{ '--category-color': category.color }"
              @click="chooseExpenseCategory(category.id)"
            >
              <span class="category-icon" :style="{ '--category-color': category.color }">
                <component :is="categoryIconComponent(category.icon)" aria-hidden="true" />
              </span>
              {{ category.name }}
            </button>
            <p v-if="!filteredExpenseCategories.length" class="empty-line">No encontramos esa categoría.</p>
          </div>
        </section>

        <section class="choice-block">
          <div class="section-title-row">
            <h2>Cuenta</h2>
            <span>{{ expenseForm.account ? 'Lista' : 'Desde dónde se pagó' }}</span>
          </div>

          <label class="search-field account-search-field">
            Buscar cuenta
            <input v-model="expenseAccountSearch" type="search" placeholder="BBVA, caja, tarjeta" autocomplete="off" />
          </label>

          <div class="choice-chips account-card-list" role="list">
            <button
              v-for="account in filteredExpenseAccounts"
              :key="account.id"
              class="account-choice-card"
              type="button"
              :class="{ active: String(account.id) === expenseForm.account }"
              :style="{ '--account-color': account.color }"
              @click="chooseExpenseAccount(account.id)"
            >
              <span class="account-color-dot" aria-hidden="true"></span>
              {{ account.name }}
            </button>
            <p v-if="!filteredExpenseAccounts.length" class="empty-line">No encontramos esa cuenta.</p>
          </div>
        </section>

        <section class="expense-final-section">
          <h2>Datos del gasto</h2>
          <div class="field-row featured-fields">
            <div class="form-field merchant-field">
              <label for="expense-merchant">Comercio o concepto</label>
              <input
                id="expense-merchant"
                v-model="expenseForm.merchant"
                placeholder="Super, farmacia, escuela"
                required
                autocomplete="off"
                aria-autocomplete="list"
                aria-controls="merchant-concept-suggestions"
                :aria-expanded="showMerchantSuggestionList('expense')"
                @focus="openMerchantSuggestions('expense')"
                @input="openMerchantSuggestions('expense')"
                @blur="closeMerchantSuggestionsSoon"
              />
              <div
                v-if="showMerchantSuggestionList('expense')"
                id="merchant-concept-suggestions"
                class="merchant-suggestions"
                role="listbox"
                aria-label="Sugerencias de comercios y conceptos"
              >
                <button
                  v-for="concept in merchantConceptSuggestions"
                  :key="concept.id"
                  type="button"
                  role="option"
                  @mousedown.prevent
                  @click="chooseMerchantConcept(concept.name)"
                >
                  <span>{{ concept.name }}</span>
                  <small>{{ concept.usage_count }} {{ concept.usage_count === 1 ? 'uso' : 'usos' }}</small>
                </button>
              </div>
            </div>
            <label>Monto<input v-model="expenseForm.amount" inputmode="decimal" placeholder="$ 850.00" required /></label>
          </div>
          <div class="field-row">
            <label>Fecha<input v-model="expenseForm.date" type="date" required /></label>
            <label>Nota opcional<textarea v-model="expenseForm.note" rows="2" placeholder="Ticket pendiente, gasto familiar"></textarea></label>
          </div>
        </section>

        <button class="primary expense-primary" type="submit" :disabled="actionBusy === 'expense'">
          <svg viewBox="0 0 24 24"><path d="M5 12l4 4L19 6" /></svg>
          {{ actionBusy === 'expense' ? 'Guardando...' : 'Guardar gasto' }}
        </button>
      </form>

      <section v-else class="feed movement-list">
        <div class="section-title-row">
          <h2>Gastos recientes</h2>
          <span>Hoy: {{ money(selectedDateExpenseTotal, settings.currency) }}</span>
        </div>
        <article v-for="transaction in recentExpenses" :key="transaction.id" class="feed-row accent-left">
          <div>
            <b>{{ transaction.merchant || transaction.category_name || transaction.transaction_type }}</b>
            <span>
              {{ transaction.category_name ?? transaction.transaction_type }} ·
              {{ transaction.created_by_username ?? 'sin usuario' }} · {{ transaction.date }}
            </span>
          </div>
          <strong>-{{ money(transaction.amount_cents, settings.currency) }}</strong>
        </article>
        <p v-if="!recentExpenses.length" class="empty-line">No hay gastos registrados.</p>
      </section>
    </section>

    <section
      v-if="view === 'commitments'"
      class="screen commitments-screen"
      :inert="iconGalleryOpen || undefined"
      :aria-hidden="iconGalleryOpen ? 'true' : undefined"
    >
      <template v-if="showCommitmentForm">
        <header class="mobile-header compact-header">
          <button class="square-action purple-action" type="button" aria-label="Volver" @click="closeCommitmentForm">
            <svg viewBox="0 0 24 24"><path d="M15 6l-6 6 6 6" /></svg>
          </button>
          <div>
            <span>Compromisos</span>
          <h1>Nuevo cargo planeado</h1>
          </div>
        </header>

        <div class="segmented purple">
          <button :class="{ active: commitmentKind === 'subscription' }" type="button" @click="commitmentKind = 'subscription'">Cargo mensual</button>
          <button :class="{ active: commitmentKind === 'msi' }" type="button" @click="commitmentKind = 'msi'">Compra a meses</button>
        </div>

        <form v-if="commitmentKind === 'subscription'" class="commitment-form form-stack" @submit.prevent="submitRecurring">
          <div class="field-row">
            <label>Nombre<input v-model="recurringForm.name" required /></label>
            <div class="form-field merchant-field">
              <label for="recurring-merchant">Comercio</label>
              <input
                id="recurring-merchant"
                v-model="recurringForm.merchant"
                placeholder="Netflix, CFE, gimnasio"
                required
                autocomplete="off"
                aria-autocomplete="list"
                aria-controls="recurring-merchant-suggestions"
                :aria-expanded="showMerchantSuggestionList('recurring')"
                @focus="openMerchantSuggestions('recurring')"
                @input="openMerchantSuggestions('recurring')"
                @blur="closeMerchantSuggestionsSoon"
              />
              <div
                v-if="showMerchantSuggestionList('recurring')"
                id="recurring-merchant-suggestions"
                class="merchant-suggestions"
                role="listbox"
                aria-label="Sugerencias de comercios y conceptos"
              >
                <button
                  v-for="concept in merchantConceptSuggestions"
                  :key="concept.id"
                  type="button"
                  role="option"
                  @mousedown.prevent
                  @click="chooseMerchantConcept(concept.name)"
                >
                  <span>{{ concept.name }}</span>
                  <small>{{ concept.usage_count }} {{ concept.usage_count === 1 ? 'uso' : 'usos' }}</small>
                </button>
              </div>
            </div>
            <label>Monto mensual<input v-model="recurringForm.amount" inputmode="decimal" required /></label>
          </div>
          <div class="field-row">
            <label>
              Categoría
              <select v-model="recurringForm.category" required>
                <option value="">Categoría</option>
                <option v-for="category in activeCategories" :key="category.id" :value="category.id">
                  {{ category.name }}{{ category.member_name ? ` - ${category.member_name}` : '' }}
                </option>
              </select>
            </label>
            <label>
              Cuenta
              <select v-model="recurringForm.account">
                <option value="">Sin cuenta</option>
                <option v-for="account in activeAccounts" :key="account.id" :value="account.id">{{ account.name }}</option>
              </select>
            </label>
          </div>
          <section class="purple-panel">
            <div class="section-title-row">
              <h2>Cargo mensual</h2>
              <span>Indefinida</span>
            </div>
            <p>Solo indica el día de pago. El cargo se repite cada mes hasta que lo omitas o lo desactives.</p>
            <label>Día de pago<input v-model.number="recurringForm.charge_day" type="number" min="1" max="28" /></label>
            <div class="preview-box">
              <b>Cómo se verá</b>
              <span>Primer cargo {{ recurringForm.start_date }}</span>
              <span>Duración indefinida</span>
            </div>
            <label>Inicio<input v-model="recurringForm.start_date" type="date" required /></label>
            <label>Fin opcional<input v-model="recurringForm.end_date" type="date" /></label>
          </section>
          <div class="action-row">
            <button class="secondary purple-secondary" type="button" @click="closeCommitmentForm">Cancelar</button>
            <button class="primary purple-primary" type="submit" :disabled="actionBusy === 'recurring'">
              {{ actionBusy === 'recurring' ? 'Guardando...' : 'Guardar cargo' }}
            </button>
          </div>
        </form>

        <form v-else class="commitment-form form-stack" @submit.prevent="submitInstallment">
          <div class="field-row">
            <label>Nombre<input v-model="installmentForm.name" required /></label>
            <div class="form-field merchant-field">
              <label for="installment-merchant">Comercio</label>
              <input
                id="installment-merchant"
                v-model="installmentForm.merchant"
                placeholder="Liverpool, Amazon, banco"
                required
                autocomplete="off"
                aria-autocomplete="list"
                aria-controls="installment-merchant-suggestions"
                :aria-expanded="showMerchantSuggestionList('installment')"
                @focus="openMerchantSuggestions('installment')"
                @input="openMerchantSuggestions('installment')"
                @blur="closeMerchantSuggestionsSoon"
              />
              <div
                v-if="showMerchantSuggestionList('installment')"
                id="installment-merchant-suggestions"
                class="merchant-suggestions"
                role="listbox"
                aria-label="Sugerencias de comercios y conceptos"
              >
                <button
                  v-for="concept in merchantConceptSuggestions"
                  :key="concept.id"
                  type="button"
                  role="option"
                  @mousedown.prevent
                  @click="chooseMerchantConcept(concept.name)"
                >
                  <span>{{ concept.name }}</span>
                  <small>{{ concept.usage_count }} {{ concept.usage_count === 1 ? 'uso' : 'usos' }}</small>
                </button>
              </div>
            </div>
            <label>Monto total<input v-model="installmentForm.total_amount" inputmode="decimal" required /></label>
          </div>
          <div class="field-row">
            <label>
              Categoría
              <select v-model="installmentForm.category" required>
                <option value="">Categoría</option>
                <option v-for="category in activeCategories" :key="category.id" :value="category.id">
                  {{ category.name }}{{ category.member_name ? ` - ${category.member_name}` : '' }}
                </option>
              </select>
            </label>
            <label>
              Cuenta
              <select v-model="installmentForm.account">
                <option value="">Sin cuenta</option>
                <option v-for="account in activeAccounts" :key="account.id" :value="account.id">{{ account.name }}</option>
              </select>
            </label>
          </div>
          <section class="purple-panel">
            <div class="section-title-row">
              <h2>Compra a meses</h2>
              <span>Plazo definido</span>
            </div>
            <p>Indica el primer y último pago. Burn Rate proyecta los cargos mensuales hasta terminar el plazo.</p>
            <div class="field-row">
              <label>Primer pago<input v-model="installmentForm.start_date" type="date" required /></label>
              <label>Último pago<input v-model="installmentForm.end_date" type="date" required /></label>
              <label>Pago inicial<input v-model="installmentForm.first_payment_number" type="number" inputmode="numeric" min="1" step="1" required /></label>
            </div>
            <div class="preview-box">
              <b>Cómo se verá</b>
              <span>Primer cargo {{ installmentForm.start_date }}</span>
              <span>Último cargo {{ installmentForm.end_date }}</span>
              <span>Empieza en pago {{ installmentForm.first_payment_number || 1 }}</span>
            </div>
          </section>
          <div class="action-row">
            <button class="secondary purple-secondary" type="button" @click="closeCommitmentForm">Cancelar</button>
            <button class="primary purple-primary" type="submit" :disabled="actionBusy === 'installment'">
              {{ actionBusy === 'installment' ? 'Guardando...' : 'Guardar compra' }}
            </button>
          </div>
        </form>
      </template>

      <template v-else>
        <header class="mobile-header commitments-header">
          <div>
            <span>Burn Rate</span>
            <h1>Cargos del mes</h1>
            <small class="commitment-inline-summary">
              <b>{{ money(currentCommitmentTotal, settings.currency) }}</b>
              <em>{{ recurringExpectedCharges.length }} mensuales · {{ projectedInstallmentPlans.length }} a meses</em>
            </small>
          </div>
          <button class="month-chip" type="button" @click="openCommitmentForm('subscription')">Agregar</button>
        </header>

        <div class="segmented">
          <button :class="{ active: commitmentTab === 'subscriptions' }" type="button" @click="commitmentTab = 'subscriptions'">Mensuales</button>
          <button :class="{ active: commitmentTab === 'msi' }" type="button" @click="commitmentTab = 'msi'">A meses</button>
        </div>

        <section v-if="commitmentTab === 'subscriptions'" class="commitment-section">
          <div class="section-title-row">
            <h2>Cargos mensuales</h2>
          </div>
          <article v-for="charge in recurringExpectedCharges" :key="charge.key" class="expected-row">
            <div>
              <b>{{ charge.name }}</b>
              <span>
                {{ charge.merchant }} · {{ charge.category.name }}
                <template v-if="charge.member"> · {{ charge.member.name }}</template>
              </span>
            </div>
            <strong>{{ money(charge.amount_cents, settings.currency) }}</strong>
            <button class="primary purple-primary" type="button" :disabled="actionBusy === `charge-${charge.key}`" @click="confirmCharge(charge)">Pagado</button>
            <button class="secondary" type="button" :disabled="actionBusy === `dismiss-${charge.key}`" @click="dismissCharge(charge)">Omitir</button>
          </article>
          <p v-if="!recurringExpectedCharges.length" class="empty-line">Sin pendientes. Liquidado u omitido todo.</p>
        </section>

        <section v-else class="commitment-section">
          <div class="section-title-row">
            <h2>Compras a meses</h2>
            <span>{{ money(currentInstallmentTotal, settings.currency) }}</span>
          </div>
          <article v-for="plan in projectedInstallmentPlans" :key="plan.id" class="installment-row">
            <div class="installment-main">
              <div>
                <b>{{ plan.name }}</b>
                <span>
                  {{ plan.merchant }} · {{ plan.category.name }}
                  <template v-if="plan.member"> · {{ plan.member.name }}</template>
                </span>
              </div>
              <strong>{{ money(plan.current_amount_cents ?? 0, settings.currency) }}</strong>
            </div>
            <div class="progress-row">
              <div class="progress-track" :aria-label="`Avance ${installmentProgressPercent(plan)}%`">
                <i :style="{ width: `${installmentProgressPercent(plan)}%` }"></i>
              </div>
              <span>
                Pago {{ plan.current_payment_number ?? '-' }} de {{ plan.payments_total }}
                <template v-if="plan.remaining_payments"> · quedan {{ plan.remaining_payments }}</template>
                <template v-else> · termina este periodo</template>
              </span>
            </div>
          </article>
          <p v-if="!projectedInstallmentPlans.length" class="empty-line">No hay compras a meses activas en la proyección.</p>
          <button class="wide-secondary" type="button" @click="openCommitmentForm('msi')">Agregar compra a meses</button>
        </section>

        <section class="projection-card">
          <div class="projection-header">
            <div>
              <h2>Pagos a meses registrados</h2>
              <span>Total de compras MSI activas en esta proyección</span>
            </div>
            <strong>{{ money(registeredInstallmentTotal, settings.currency) }}</strong>
          </div>
          <div class="projection-timeline">
            <article
              v-for="(period, index) in projectedInstallmentPeriods"
              :key="period.key"
              :class="{ empty: !period.total_cents, settled: projectionSettledPlans(period).length }"
            >
              <div class="projection-period-main">
                <span>{{ projectionPeriodLabel(index) }}</span>
                <strong>{{ money(period.total_cents, settings.currency) }}</strong>
              </div>
              <div class="projection-period-bar" :aria-label="`${money(period.total_cents, settings.currency)} en ${projectionPeriodLabel(index)}`">
                <i :style="{ width: projectionBarWidth(period.total_cents) }"></i>
              </div>
              <div class="projection-period-meta">
                <span>{{ period.plans.length ? projectionPaymentCountLabel(period.plans.length) : 'Sin pagos MSI' }}</span>
                <b v-if="projectionSettledPlans(period).length">{{ projectionSettledLabel(period) }}</b>
              </div>
            </article>
          </div>
        </section>
      </template>
    </section>

    <section
      v-if="view === 'settings'"
      class="screen settings-screen"
      :inert="iconGalleryOpen || undefined"
      :aria-hidden="iconGalleryOpen ? 'true' : undefined"
    >
      <header class="mobile-header">
        <div>
          <h1>Ajustes</h1>
          <span>La base de tu casa</span>
        </div>
      </header>

      <template v-if="canManageSettings">
        <form class="setup-intro form-stack" @submit.prevent="saveSettings">
          <div>
            <h2>Primero lo esencial</h2>
            <p>Configura solo lo que necesitas para que el plan familiar calcule bien.</p>
          </div>
          <div class="cutoff-row">
            <label>Día de corte<input v-model.number="settingsForm.cutoff_day" type="number" min="1" max="28" /></label>
            <button class="primary blue-primary" type="submit" :disabled="actionBusy === 'settings'">
              {{ actionBusy === 'settings' ? 'Guardando...' : 'Guardar corte' }}
            </button>
          </div>
          <small>El periodo siempre se arma con días del 1 al 28 para evitar meses raros.</small>
        </form>

        <div class="setup-tabs" aria-label="Secciones de ajustes">
          <button
            v-for="item in setupPanelItems"
            :key="item.id"
            type="button"
            :class="{ active: settingsPanel === item.id }"
            @click="settingsPanel = item.id"
          >
            {{ item.label }}
          </button>
        </div>

        <section class="settings-grid focused">
          <section v-if="settingsPanel === 'accounts'" class="panel form-stack compact-panel accounts-panel">
            <div class="section-title-row">
              <div>
                <h2>Cuentas de pago</h2>
                <p>Crea o ajusta las cuentas que usas para pagar gastos de la casa.</p>
              </div>
              <span>Saldo: {{ money(totalAccountBalance, settings.currency) }}</span>
            </div>
            <form class="form-stack account-edit-form" @submit.prevent="submitAccount">
              <div class="section-title-row compact-title-row">
                <h3>{{ accountFormTitle }}</h3>
                <button v-if="editingAccountId" class="secondary" type="button" @click="resetAccountForm">Cancelar</button>
              </div>
              <label>Nombre<input v-model="accountForm.name" placeholder="Cartera casa" required /></label>
              <div class="segmented account-type-tabs">
                <button type="button" :class="{ active: accountForm.account_type === 'cash' }" @click="accountForm.account_type = 'cash'">Efectivo</button>
                <button type="button" :class="{ active: accountForm.account_type === 'bank' }" @click="accountForm.account_type = 'bank'">Banco</button>
                <button type="button" :class="{ active: accountForm.account_type === 'debit_card' }" @click="accountForm.account_type = 'debit_card'">Tarjeta débito</button>
                <button type="button" :class="{ active: accountForm.account_type === 'credit_card' }" @click="accountForm.account_type = 'credit_card'">Tarjeta crédito</button>
              </div>
              <label v-if="accountForm.account_type === 'cash'">
                Saldo inicial visible para efectivo
                <input v-model="accountForm.initial_balance" inputmode="decimal" placeholder="$ 2,000.00" />
              </label>
              <div class="field-group">
                <span>Color</span>
                <div class="color-picker-row" role="group" aria-label="Color de cuenta">
                  <button
                    v-for="color in accountColors"
                    :key="color"
                    type="button"
                    :aria-label="color"
                    :class="{ active: accountForm.color === color }"
                    :style="{ background: color }"
                    @click="accountForm.color = color"
                  ></button>
                  <input v-model="accountForm.color" type="color" aria-label="Color personalizado" />
                </div>
              </div>
              <label class="check-row">
                <input v-model="accountForm.is_active" type="checkbox" />
                Activa: aparece como medio de pago
              </label>
              <button class="primary account-primary" type="submit" :disabled="actionBusy === 'account'">
                {{ accountSubmitLabel }}
              </button>
            </form>
            <div class="account-list">
              <article v-for="account in accounts" :key="account.id" class="account-row" :class="{ muted: !account.is_active }">
                <span :style="{ background: account.color }"></span>
                <div>
                  <b>{{ account.name }}</b>
                  <small>{{ accountTypeLabel(account.account_type) }} · {{ account.is_active ? 'activa' : 'inactiva' }}</small>
                </div>
                <strong>{{ money(account.current_balance_cents, settings.currency) }}</strong>
                <button class="secondary" type="button" @click="editAccount(account)">Editar</button>
              </article>
              <p v-if="!accounts.length" class="empty-line">Sin cuentas creadas.</p>
            </div>
          </section>

          <form v-if="settingsPanel === 'people'" class="panel form-stack compact-panel people-panel" @submit.prevent="submitMember">
            <h2>Personas de casa</h2>
            <p>Usa personas para separar gastos personales dentro del mismo plan familiar.</p>
            <div class="people-pills">
              <button
                v-for="member in members"
                :key="member.id"
                type="button"
                class="people-pill"
                :class="{ active: editingMemberId === member.id }"
                :style="{ '--member-color': member.color }"
                @click="editMember(member)"
              >
                <span>{{ member.name }}</span>
                <small>{{ member.access_enabled ? (member.user_is_admin ? 'admin' : 'usuario') : 'sin login' }}</small>
              </button>
            </div>
            <div class="section-title-row compact-title-row">
              <h3>{{ memberFormTitle }}</h3>
              <button v-if="editingMemberId" class="secondary" type="button" @click="resetMemberForm">Cancelar</button>
            </div>
            <label>Nombre de la persona<input v-model="memberForm.name" required /></label>
            <label class="switch-row">
              <input :checked="memberForm.has_access" type="checkbox" role="switch" @change="setMemberAccessFromEvent" />
              <span class="switch-track" aria-hidden="true"></span>
              <span>
                <b>Acceso a la app</b>
                <small>Puede iniciar sesión con usuario y clave</small>
              </span>
            </label>
            <label class="switch-row">
              <input :checked="memberForm.is_admin" type="checkbox" role="switch" @change="setMemberAdminFromEvent" />
              <span class="switch-track" aria-hidden="true"></span>
              <span>
                <b>Admin</b>
                <small>También activa el acceso a la app</small>
              </span>
            </label>
            <template v-if="memberForm.has_access">
              <div class="field-row">
                <label>Usuario<input v-model="memberForm.username" autocomplete="username" required /></label>
                <label>Email<input v-model="memberForm.email" type="email" autocomplete="email" /></label>
              </div>
              <label>Clave temporal<input v-model="memberForm.password" type="password" autocomplete="new-password" :required="!editingMemberId" /></label>
            </template>
            <label>Color<input v-model="memberForm.color" type="color" /></label>
            <button class="primary blue-primary" type="submit" :disabled="actionBusy === 'member'">
              {{ memberSubmitLabel }}
            </button>
          </form>

          <section v-if="settingsPanel === 'categories'" class="panel form-stack compact-panel categories-panel">
            <div class="section-title-row">
              <div>
                <h2>Categorías del plan</h2>
                <p>Crea o ajusta categorías, presupuesto mensual, icono, color y estado.</p>
              </div>
              <span>{{ categories.length }} totales</span>
            </div>
            <form class="form-stack category-edit-form" @submit.prevent="submitCategory">
              <div class="section-title-row compact-title-row">
                <h3>{{ categoryFormTitle }}</h3>
                <button v-if="editingCategoryId" class="secondary" type="button" @click="resetCategoryForm">Cancelar</button>
              </div>
              <div class="segmented blue-segmented">
                <button type="button" :class="{ active: categoryForm.scope === 'global' }" @click="categoryForm.scope = 'global'">Familia</button>
                <button type="button" :class="{ active: categoryForm.scope === 'personal' }" @click="categoryForm.scope = 'personal'">Personal</button>
              </div>
              <label>Nombre<input v-model="categoryForm.name" required /></label>
              <label v-if="categoryForm.scope === 'personal'">
                Persona
                <select v-model="categoryForm.member" required>
                  <option value="">Elige persona</option>
                  <option v-for="member in members" :key="member.id" :value="member.id">{{ member.name }}</option>
                </select>
              </label>
              <label>Presupuesto mensual<input v-model="categoryForm.monthly_budget" inputmode="decimal" required /></label>
              <div class="field-group">
                <span>Icono</span>
                <button class="icon-select-button" type="button" :style="{ '--category-color': categoryForm.color }" @click="openIconGallery($event)">
                  <span class="category-icon selected-icon-preview" :style="{ '--category-color': categoryForm.color }">
                    <component :is="selectedCategoryIcon.component" aria-hidden="true" />
                  </span>
                  <span>
                    <b>{{ selectedCategoryIcon.label }}</b>
                    <small>Cambiar icono</small>
                  </span>
                </button>
              </div>
              <div class="field-group">
                <span>Color</span>
                <div class="color-picker-row" role="group" aria-label="Color de categoría">
                  <button
                    v-for="color in categoryColors"
                    :key="color"
                    type="button"
                    :aria-label="color"
                    :class="{ active: categoryForm.color === color }"
                    :style="{ background: color }"
                    @click="categoryForm.color = color"
                  ></button>
                  <input v-model="categoryForm.color" type="color" aria-label="Color personalizado" />
                </div>
              </div>
              <label class="check-row">
                <input v-model="categoryForm.is_active" type="checkbox" />
                Activa: aparece en plan y captura de gastos
              </label>
              <button class="primary blue-primary" type="submit" :disabled="actionBusy === 'category'">
                {{ categorySubmitLabel }}
              </button>
            </form>
            <section class="category-edit-list" aria-label="Categorías existentes">
              <article
                v-for="category in categories"
                :key="category.id"
                class="category-edit-row"
                :class="{ muted: !category.is_active }"
                :style="{ '--category-color': category.color }"
              >
                <span class="category-icon" :style="{ '--category-color': category.color }">
                  <component :is="categoryIconComponent(category.icon)" aria-hidden="true" />
                </span>
                <div>
                  <b>{{ category.name }}</b>
                  <span>
                    {{ category.scope === 'global' ? 'Familia' : category.member_name || 'Personal' }} ·
                    {{ money(category.monthly_budget_cents, settings.currency) }} ·
                    {{ category.is_active ? 'activa' : 'inactiva' }}
                  </span>
                </div>
                <button class="secondary" type="button" @click="editCategory(category)">Editar</button>
              </article>
              <p v-if="!categories.length" class="empty-line">Sin categorías creadas.</p>
            </section>
          </section>

          <form v-if="settingsPanel === 'invitations'" class="panel form-stack compact-panel invitations-panel" @submit.prevent="submitInvitation">
            <div class="section-title-row">
              <div>
                <h2>Invitaciones</h2>
                <p>Genera un link para que otra persona entre a Burn Rate sin compartir tu password.</p>
              </div>
              <span>{{ invitations.length }} activas</span>
            </div>
            <label>
              Email
              <input v-model="invitationForm.email" type="email" autocomplete="email" placeholder="familia@example.com" required />
            </label>
            <label class="check-row">
              <input v-model="invitationForm.is_admin" type="checkbox" />
              Admin: puede cambiar ajustes e invitar personas
            </label>
            <button class="primary blue-primary" type="submit" :disabled="actionBusy === 'invitation'">
              {{ actionBusy === 'invitation' ? 'Creando...' : 'Crear invitación' }}
            </button>

            <section v-if="createdInvitationLink" class="copy-link-card" aria-label="Última invitación creada">
              <label>
                Link para compartir
                <input :value="createdInvitationLink" readonly @focus="selectInputText" />
              </label>
              <button class="secondary" type="button" @click="copyInvitationLink(createdInvitationLink, 'created')">
                {{ copiedInvitationId === 'created' ? 'Copiado' : 'Copiar link' }}
              </button>
            </section>

            <section class="invitation-list" aria-label="Invitaciones existentes">
              <article v-for="invitation in invitations" :key="invitation.id" class="invitation-row">
                <div class="invitation-row-top">
                  <div>
                    <b>{{ invitation.display_name || invitation.email }}</b>
                    <span>{{ invitation.is_admin || invitation.is_staff ? 'admin' : 'usuario' }} · {{ invitation.email }}</span>
                  </div>
                  <small>{{ invitation.accepted_at ? 'aceptada' : invitation.status ?? 'pendiente' }}</small>
                </div>
                <p v-if="invitation.message">{{ invitation.message }}</p>
                <div v-if="invitationLink(invitation)" class="copy-link-inline">
                  <input
                    :value="invitationLink(invitation)"
                    readonly
                    aria-label="Link de invitación"
                    @focus="selectInputText"
                  />
                  <button class="secondary" type="button" @click="copyInvitationLink(invitationLink(invitation), invitation.id)">
                    {{ copiedInvitationId === invitation.id ? 'Copiado' : 'Copiar' }}
                  </button>
                </div>
                <p v-else class="invitation-link-missing">El link solo se muestra al crear la invitación. Crea otra si necesitas reenviarlo.</p>
                <div v-if="!invitation.accepted_at" class="invitation-actions">
                  <button
                    class="secondary danger-secondary"
                    type="button"
                    :disabled="actionBusy === `delete-invitation-${invitation.id}`"
                    @click="deleteInvitation(invitation)"
                  >
                    {{ actionBusy === `delete-invitation-${invitation.id}` ? 'Eliminando...' : 'Eliminar' }}
                  </button>
                </div>
              </article>
              <p v-if="!invitations.length" class="empty-line">Sin invitaciones creadas.</p>
            </section>
          </form>
        </section>
      </template>

      <section class="theme-panel" aria-labelledby="theme-title">
        <div class="section-title-row theme-title-row">
          <h2 id="theme-title">Tema</h2>
          <span>{{ themeStatusLabel }}</span>
        </div>
        <div class="theme-switch" role="radiogroup" aria-label="Tema de la interfaz">
          <button
            v-for="option in themeOptions"
            :key="option.id"
            type="button"
            role="radio"
            :aria-checked="theme === option.id"
            :class="{ active: theme === option.id }"
            @click="selectThemePreference(option.id)"
          >
            <component :is="option.icon" aria-hidden="true" />
            <span>{{ option.label }}</span>
          </button>
        </div>
      </section>

      <button class="settings-logout-button" type="button" @click="store.logout">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 6H6v12h4M14 8l4 4-4 4M8 12h10" /></svg>
        <span>Salir de Burn Rate</span>
      </button>
    </section>

    <div v-if="iconGalleryOpen" class="icon-gallery-backdrop" @click.self="closeIconGallery">
      <section
        ref="iconGalleryDialog"
        class="icon-gallery-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="icon-gallery-title"
        @keydown="handleIconGalleryKeydown"
      >
        <header class="icon-gallery-header">
          <div>
            <h2 id="icon-gallery-title">Galería de iconos</h2>
            <span>{{ filteredCategoryIcons.length }} disponibles</span>
          </div>
          <button class="square-action icon-gallery-close" type="button" aria-label="Cerrar galería" @click="closeIconGallery">
            <X aria-hidden="true" />
          </button>
        </header>

        <label class="icon-gallery-search">
          <Search aria-hidden="true" />
          <input v-model="iconSearch" type="search" placeholder="Buscar comida, renta, salud..." />
        </label>

        <div v-if="filteredCategoryIcons.length" class="icon-gallery-grid" role="listbox" aria-label="Iconos de categoría">
          <button
            v-for="icon in filteredCategoryIcons"
            :key="icon.id"
            type="button"
            role="option"
            :aria-selected="categoryForm.icon === icon.id"
            :class="{ active: categoryForm.icon === icon.id }"
            :style="{ '--category-color': categoryForm.color }"
            @click="selectCategoryIcon(icon.id)"
          >
            <component :is="icon.component" aria-hidden="true" />
            <span>{{ icon.label }}</span>
            <small>{{ icon.group }}</small>
          </button>
        </div>
        <p v-else class="icon-gallery-empty">Sin resultados.</p>
      </section>
    </div>

    <nav
      class="bottom-nav"
      :style="{ gridTemplateColumns: `repeat(${visibleNavItems.length}, minmax(0, 1fr))` }"
      aria-label="Principal"
      :inert="iconGalleryOpen || undefined"
      :aria-hidden="iconGalleryOpen ? 'true' : undefined"
    >
      <button
        v-for="item in visibleNavItems"
        :key="item.id"
        type="button"
        :aria-label="item.label"
        :class="[`nav-${item.id}`, { active: view === item.id }]"
        @click="selectView(item.id)"
      >
        <svg viewBox="0 0 24 24"><path :d="item.icon" /></svg>
        <span>{{ item.label }}</span>
      </button>
    </nav>
  </main>
</template>
