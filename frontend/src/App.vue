<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, shallowRef, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { Check, ChevronRight, Laptop, ListChecks, Moon, Pencil, Search, Sun, Trash2, X } from '@lucide/vue'
import {
  useBudgetStore,
  type Account,
  type Category,
  type BudgetCategorySummary,
  type ExpectedCharge,
  type HouseholdMember,
  type InstallmentProjectionPlan,
  type Invitation,
  type RecurringExpense,
  type Scope,
  type Transaction,
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
  appToday,
  members,
  categories,
  accounts,
  activeCategories,
  activeAccounts,
  merchantConcepts,
  transactions,
  recurringExpenses,
  installmentPlans,
  expectedCharges,
  installmentProjection,
  creditCardPaymentSummary,
  offBudgetSummary,
  summary,
  invitations,
  resolvedInvitation,
  loading,
  error,
  firstRunClaimRequired,
} = storeToRefs(store)

type View = 'budget' | 'expenses' | 'commitments' | 'benefits' | 'settings'
type ExpensesTab = 'capture' | 'feed'
type CommitmentTab = 'subscriptions' | 'msi'
type CommitmentKind = 'subscription' | 'msi'
type CommitmentEditKind = 'recurring' | 'installment'
type SettingsPanel = 'accounts' | 'people' | 'categories' | 'invitations'
type NoticeType = 'success' | 'error' | 'info'
type MerchantSuggestionTarget = 'expense' | 'recurring' | 'installment'
type ThemePreference = 'auto' | 'light' | 'dark'
type ResolvedTheme = 'light' | 'dark'
type BudgetCycleOption = { value: string; label: string; start: string; end: string; offset: number }
type SpendingChartSegment = {
  key: string
  label: string
  amount_cents: number
  percent: number
  color: string
  icon: string
  category_ids: number[]
}
type BenefitSource = {
  label: string
  url: string
}
type BenefitItem = {
  label: string
  value: string
  detail: string
}
type BenefitProduct = {
  id: string
  name: string
  issuer: string
  type: string
  accent: string
  bestFor: string
  quickRule: string
  bestUses: string[]
  benefits: BenefitItem[]
  watchOut: string
  sources: BenefitSource[]
}
type BenefitRecommendation = {
  id: string
  spend: string
  product: string
  reason: string
  note: string
  accent: string
}

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
const cycleMenuOpen = ref(false)
const iconGalleryOpen = ref(false)
const iconGalleryDialog = ref<HTMLElement | null>(null)
const iconGalleryOpener = ref<HTMLElement | null>(null)
const iconSearch = ref('')
const selectedDate = ref(appToday.value)
const selectedScope = ref<Scope>('total')
const selectedCategoryId = ref<number | null>(null)
const expenseCategorySearch = ref('')
const expenseAccountSearch = ref('')
const expenseFeedCategoryId = ref('')
const expenseFeedPaymentMethod = ref('')
const expenseReviewMode = ref(false)
const reviewedExpenseIds = shallowRef(new Set<Transaction['id']>())
const commitmentCategorySearch = ref('')
const commitmentAccountSearch = ref('')
const merchantSuggestionsOpen = ref(false)
const merchantSuggestionTarget = ref<MerchantSuggestionTarget>('expense')
const inviteToken = ref(inviteTokenFromLocation())
const inviteLoading = ref(false)
const copiedInvitationId = ref<number | string | null>(null)
const createdInvitationLink = ref('')
const editingAccountId = ref<number | null>(null)
const editingMemberId = ref<number | null>(null)
const editingCategoryId = ref<number | null>(null)
const editingTransactionId = ref<number | null>(null)
const deleteConfirmTransactionId = ref<number | null>(null)
const accountFormOpen = ref(false)
const memberFormOpen = ref(false)
const categoryFormOpen = ref(false)
const editingCommitment = ref<{ type: CommitmentEditKind; id: number } | null>(null)
const deleteConfirmCommitment = ref<{ type: CommitmentEditKind; id: number } | null>(null)
const claimForm = reactive({ full_name: '', display_name: '', email: '', password: '', confirmPassword: '' })
const loginForm = reactive({ email: '', password: '' })
const acceptInviteForm = reactive({ full_name: '', display_name: '', password: '', confirmPassword: '' })
const invitationForm = reactive({
  email: '',
  is_admin: false,
})
const expenseForm = reactive({ merchant: '', amount: '', category: '', account: '', date: selectedDate.value, note: '' })
const transactionEditForm = reactive({ merchant: '', amount: '', category: '', account: '', date: selectedDate.value, note: '' })
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
  budget_treatment: 'budgeted' as 'budgeted' | 'tracking_only',
  member: '',
  monthly_budget: '',
  budget_behavior: 'monthly_reset' as 'monthly_reset' | 'carryover',
  carryover_initial_balance: '',
  carryover_start_date: selectedDate.value,
  budget_effective_date: selectedDate.value,
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
  auto_charge: false,
})
const installmentForm = reactive({
  name: '',
  merchant: '',
  total_amount: '',
  category: '',
  account: '',
  start_date: selectedDate.value,
  months_count: '12',
  round_up_monthly_payment: true,
})
const commitmentEditForm = reactive({
  name: '',
  merchant: '',
  category: '',
  account: '',
  charge_day: 1,
  auto_charge: false,
})
const settingsForm = reactive({ cutoff_day: 20, time_zone: settings.value.time_zone })
const notice = reactive<{ type: NoticeType; message: string }>({ type: 'info', message: '' })
const actionBusy = ref('')
let noticeTimer: ReturnType<typeof window.setTimeout> | undefined
let merchantSuggestionsTimer: ReturnType<typeof window.setTimeout> | undefined
let authRefreshTimer: ReturnType<typeof window.setInterval> | undefined
let lastActivityRefreshAttempt = 0
let copiedInvitationTimer: ReturnType<typeof window.setTimeout> | undefined
let systemThemeMediaQuery: MediaQueryList | undefined

const navItems = [
  { id: 'budget', label: 'Presupuesto', icon: 'M3.5 11.5 12 4l8.5 7.5M5.5 10.5V20h13v-9.5M9 20v-6h6v6M9.2 12.2l1.7 1.7 3.7-3.9' },
  { id: 'expenses', label: 'Gastos', icon: 'M4 7h16v10H4zM7 10h5M7 14h3M15 14a2 2 0 100-4 2 2 0 000 4z' },
  { id: 'commitments', label: 'Pagos', icon: 'M4 7a2 2 0 012-2h12a2 2 0 012 2v10a2 2 0 01-2 2H6a2 2 0 01-2-2zM4 9h16M7 15h4M15 15h2' },
  { id: 'benefits', label: 'Beneficios', icon: 'M12 3l2.6 5.3 5.9.9-4.2 4.1 1 5.8L12 16.3 6.7 19.1l1-5.8-4.2-4.1 5.9-.9L12 3z' },
  { id: 'settings', label: 'Ajustes', icon: 'M12 15a3 3 0 100-6 3 3 0 000 6ZM19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 0v-.09a1.65 1.65 0 00-1-1.51 1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06A1.65 1.65 0 004.6 15a1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09a1.65 1.65 0 001.51-1 1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 008.92 4.6a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06A1.65 1.65 0 0019.4 9c.24.54.78.9 1.37 1H21a2 2 0 110 4h-.23a1.65 1.65 0 00-1.37 1Z' },
] as const

const benefitsLastChecked = '31 mayo 2026'
const benefitRecommendations: BenefitRecommendation[] = [
  {
    id: 'costco-gas',
    spend: 'Costco y gasolina Costco',
    product: 'Banamex Costco',
    reason: 'Es la mejor señal directa: 5% en gasolina Costco, 3% en Costco y ahorro por precio de efectivo en sucursal.',
    note: 'El reembolso es anual; gasolina tiene tope mensual antes de bajar a 3%.',
    accent: '#9d5f16',
  },
  {
    id: 'education',
    spend: 'Escuela, libros y educación',
    product: 'Banamex Costco',
    reason: 'La categoría educación acumula 4% de reembolso anual hasta el tope mensual publicado por Banamex.',
    note: 'Después del tope acumula 1%, así que conviene separar compras grandes.',
    accent: '#9d5f16',
  },
  {
    id: 'pharmacy',
    spend: 'Farmacias',
    product: 'Santander LikeU crédito',
    reason: 'Es la mejor categoría directa: la Tarjeta de Crédito LikeU publica 6% de cashback en farmacias participantes.',
    note: 'Requiere inscripción, cuenta Santander participante y compra directa en el comercio.',
    accent: '#c43131',
  },
  {
    id: 'restaurants',
    spend: 'Restaurantes y antojos',
    product: 'Santander LikeU crédito',
    reason: 'LikeU crédito da 5% de cashback en restaurantes participantes; supera el 2% anual de Banamex Costco.',
    note: 'Paga directo en restaurante o app oficial; plataformas intermediarias no aplican.',
    accent: '#c43131',
  },
  {
    id: 'telecom',
    spend: 'Internet, celular y telecom',
    product: 'Santander LikeU crédito',
    reason: 'LikeU crédito da 4% de cashback en telecomunicaciones participantes.',
    note: 'Debe ser cargo directo del comercio o servicio participante.',
    accent: '#c43131',
  },
  {
    id: 'travel-large',
    spend: 'Viajes y compras grandes',
    product: 'Amex Platinum Credit Card',
    reason: 'Conviene por 3 MSI automáticos, Priority Pass, PriceTravel, protecciones y promociones activables.',
    note: 'Confirma aceptación Amex y activa beneficios antes de comprar.',
    accent: '#6f5db8',
  },
  {
    id: 'general',
    spend: 'Compras generales sin categoría',
    product: 'BBVA Dorada (Oro) o Banamex Costco',
    reason: 'BBVA acumula 11% en Puntos BBVA en compras a una exhibición; Banamex deja 1% anual en el resto.',
    note: 'Si es supermercado participante, LikeU crédito también puede dar 1% cashback.',
    accent: '#2f65d7',
  },
]
const benefitProducts: BenefitProduct[] = [
  {
    id: 'banamex-costco',
    name: 'Banamex Costco',
    issuer: 'Banamex + Costco',
    type: 'Tarjeta de crédito',
    accent: '#9d5f16',
    bestFor: 'Costco, gasolina Costco, educación, restaurantes, streaming, TV e internet.',
    quickRule: 'Úsala cuando el gasto cae en sus categorías de reembolso. Evita agregadores si quieres conservar la categoría.',
    bestUses: ['Costco', 'Gasolina Costco', 'Educación', 'Restaurantes', 'Streaming e internet'],
    benefits: [
      {
        label: 'Gasolina Costco',
        value: '5%',
        detail: 'Reembolso anual con tope de $10,000 MXN de facturación mensual; después acumula 3%.',
      },
      {
        label: 'Educación',
        value: '4%',
        detail: 'Aplica en escuelas, librerías y giros educativos hasta $20,000 MXN de facturación mensual.',
      },
      {
        label: 'Costco',
        value: '3%',
        detail: 'Tiendas Costco México, Costco Estados Unidos y costco.com.mx.',
      },
      {
        label: 'Casa digital',
        value: '2%',
        detail: 'Restaurantes, streaming, televisión de paga y servicios de internet.',
      },
      {
        label: 'Resto',
        value: '1%',
        detail: 'Compras fuera de las categorías anteriores y pagos por agregadores.',
      },
    ],
    watchOut: 'El reembolso es anual y las compras por agregadores generan 1% aunque el comercio original pertenezca a otra categoría.',
    sources: [
      {
        label: 'Folleto informativo Costco Banamex',
        url: 'https://www.banamex.com/resources/pdf/es/personas/creditos/tarjetas_credito/folleto-informativo-costco.pdf',
      },
    ],
  },
  {
    id: 'bbva-oro',
    name: 'BBVA Dorada (Oro)',
    issuer: 'BBVA México',
    type: 'Tarjeta de crédito',
    accent: '#2f65d7',
    bestFor: 'Compras a una exhibición cuando te sirven los Puntos BBVA.',
    quickRule: 'Es respaldo útil si redimes Puntos BBVA seguido; no la pongas por encima de cashback directo en categorías claras.',
    bestUses: ['Compras a una exhibición', 'Respaldo Visa', 'Seguridad en app', 'Viajes con equipaje'],
    benefits: [
      {
        label: 'Puntos BBVA',
        value: '11%',
        detail: 'Acumula 11% de tus compras en Puntos BBVA; las compras a meses sin intereses no acumulan.',
      },
      {
        label: 'Compras en línea',
        value: 'CVV',
        detail: 'CVV dinámico en app, tarjeta sin datos visibles, apagado desde la app y notificaciones.',
      },
      {
        label: 'Equipaje',
        value: '$1,000 / $3,000',
        detail: 'Cobertura BBVA por demora o pérdida de equipaje, con condiciones publicadas por el banco.',
      },
      {
        label: 'Compra protegida',
        value: 'Seguro',
        detail: 'Protección para ciertos bienes comprados totalmente con tarjetas BBVA.',
      },
    ],
    watchOut: 'Los Puntos BBVA dependen del canje y no son cashback en efectivo; revisa anualidad y si tu oferta personal la exenta.',
    sources: [
      {
        label: 'Tarjeta Oro BBVA',
        url: 'https://www.bbva.mx/personas/productos/tarjetas-de-credito/tarjeta-de-credito-oro.html',
      },
    ],
  },
  {
    id: 'santander-u',
    name: 'Santander LikeU crédito',
    issuer: 'Santander México',
    type: 'Tarjeta de crédito',
    accent: '#c43131',
    bestFor: 'Farmacias, restaurantes, telecomunicaciones y supermercados participantes.',
    quickRule: 'Úsala en giros participantes cuando puedas pagar directo con el comercio; para recibir cashback necesitas inscripción y cuenta Santander participante.',
    bestUses: ['Farmacias', 'Restaurantes', 'Telecom', 'Supermercados', 'MSI con cashback'],
    benefits: [
      {
        label: 'Farmacias',
        value: '6%',
        detail: 'Cashback en farmacias participantes. No aplica en farmacias dentro de supermercados o tiendas departamentales.',
      },
      {
        label: 'Restaurantes',
        value: '5%',
        detail: 'Cashback en restaurantes participantes cuando pagas directo con el establecimiento o su app oficial.',
      },
      {
        label: 'Telecom',
        value: '4%',
        detail: 'Cashback en servicios de cable, telefonía e internet participantes.',
      },
      {
        label: 'Supermercados',
        value: '1%',
        detail: 'Cashback en supermercados participantes, incluso en app del establecimiento cuando aplique.',
      },
      {
        label: 'Costos y seguridad',
        value: '$0 anual',
        detail: 'Sin anualidad; tarjeta sin números impresos, tarjeta digital inmediata y CVV dinámico.',
      },
    ],
    watchOut: 'Si no haces al menos $200 MXN de compras al mes, Santander publica una comisión mensual de mantenimiento. El cashback cae en una cuenta Santander y no aplica en compras por plataformas intermediarias.',
    sources: [
      {
        label: 'Tarjeta de Crédito LikeU',
        url: 'https://www.santander.com.mx/personas/credito-y-financiamiento/tarjetas-de-credito/likeu',
      },
      {
        label: 'Cashback Santander',
        url: 'https://www.santander.com.mx/cashback.html',
      },
      {
        label: 'Comercios participantes',
        url: 'https://www.santander.com.mx/cashback/comercios-participantes/',
      },
    ],
  },
  {
    id: 'amex-platinum-credit',
    name: 'Amex Platinum Credit Card',
    issuer: 'American Express México',
    type: 'Tarjeta de crédito',
    accent: '#6f5db8',
    bestFor: 'Viajes, compras grandes, promociones activables y meses automáticos.',
    quickRule: 'Úsala cuando el comercio acepte Amex y el beneficio activado supere una tarjeta de cashback simple.',
    bestUses: ['3 MSI automático', 'Viajes', 'Priority Pass', 'Starbucks', 'Promos activables'],
    benefits: [
      {
        label: 'Meses automáticos',
        value: '3 MSI',
        detail: 'Compras desde $6,000 MXN en moneda nacional y sin mínimo en moneda extranjera.',
      },
      {
        label: 'Salas VIP',
        value: '4 accesos',
        detail: 'Membresía Priority Pass con cuatro accesos anuales sin costo para titular.',
      },
      {
        label: 'Viajes',
        value: '10%',
        detail: 'Descuento PriceTravel en sitio exclusivo y beneficios de viaje publicados por Amex.',
      },
      {
        label: 'Promos vigentes',
        value: '$800 / $500',
        detail: 'Bonificaciones en Viva y Walmart.com.mx con inscripción y condiciones de vigencia.',
      },
      {
        label: 'Starbucks',
        value: '$120',
        detail: 'Bebida de cortesía diaria al hacer un consumo mínimo de $120.00 MXN con The Platinum Credit Card.',
      },
      {
        label: 'Recompensas y protección',
        value: 'MR',
        detail: 'Membership Rewards, Fiesta Rewards Platino y protecciones de viaje y compras.',
      },
    ],
    watchOut: 'Varias promociones requieren inscripción previa; la cuota anual a partir del segundo año y la aceptación Amex cambian la conveniencia.',
    sources: [
      {
        label: 'Beneficios The Platinum Credit Card',
        url: 'https://www.americanexpress.com/mx/beneficios/the-platinum-credit-card/index.html',
      },
    ],
  },
]

const setupPanelItems = [
  { id: 'accounts', label: 'Cuentas' },
  { id: 'people', label: 'Personas' },
  { id: 'categories', label: 'Categorías' },
  { id: 'invitations', label: 'Invitar' },
] as const

const themeOptions = [
  { id: 'auto', label: 'Sistema', icon: Laptop },
  { id: 'light', label: 'Claro', icon: Sun },
  { id: 'dark', label: 'Oscuro', icon: Moon },
] as const

const timeZoneOptions = [
  'America/Mexico_City',
  'America/Merida',
  'America/Monterrey',
  'America/Tijuana',
  'America/Cancun',
  'UTC',
  'America/New_York',
  'America/Los_Angeles',
  'Europe/Madrid',
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
  if (theme.value === 'auto') return `Sistema / ${activeTheme.value === 'dark' ? 'oscuro' : 'claro'}`
  return theme.value === 'dark' ? 'Oscuro' : 'Claro'
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
const trackingOnlyCategories = computed(() => categories.value.filter((category) => category.budget_treatment === 'tracking_only'))
const activeBudgetPeriod = computed(() => budgetPeriodForDate(selectedDate.value, settings.value.cutoff_day))
const currentBudgetPeriod = computed(() => budgetPeriodForDate(appToday.value, settings.value.cutoff_day))
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
const activeBudgetCycleOption = computed(() =>
  budgetCycleOptions.value.find((cycle) => cycle.value === activeBudgetPeriod.value.start) ??
  budgetCycleOptions.value[budgetCycleOptions.value.length - 1],
)
const budgetCycleMenuOptions = computed(() => [...budgetCycleOptions.value].reverse())
const periodRange = computed(() => `${activeBudgetPeriod.value.start} / ${activeBudgetPeriod.value.end}`)
const activePeriodLabel = computed(() => formatPeriodLabel(activeBudgetPeriod.value.start, activeBudgetPeriod.value.end))
const canShiftToPreviousCycle = computed(() => activeBudgetPeriod.value.start > (budgetCycleOptions.value[0]?.start ?? activeBudgetPeriod.value.start))
const canShiftToNextCycle = computed(() => activeBudgetPeriod.value.start < currentBudgetPeriod.value.start)
const overspent = computed(() => summary.value?.categories.filter((category) => category.is_overspent) ?? [])
const planSummaryCopy = computed(() => {
  if (!summary.value) return 'Carga tu presupuesto para ver cómo va la casa.'
  const available = summary.value.totals.available_cents
  if (available < 0) {
    return 'La casa ya rebasó el presupuesto de este periodo. Conviene revisar las categorías en rojo antes del siguiente gasto.'
  }
  if (overspent.value.length) {
    return 'Todavía hay margen, pero una categoría necesita atención antes de seguir gastando.'
  }
  return 'La casa va dentro del presupuesto. Registra los gastos cuando pasen para mantener este número confiable.'
})
const planAttentionItems = computed(() => {
  const items = overspent.value.slice(0, 2).map((category) => ({
    key: `overspent-${category.category_id}`,
    tone: 'danger',
    title: category.category_name,
      body: `Va ${money(Math.abs(category.available_cents), settings.value.currency)} arriba del presupuesto.`,
  }))
  const upcomingCharges = expectedCharges.value
    .filter((charge) => charge.source_type === 'recurring' && charge.category.budget_treatment !== 'tracking_only')
    .slice(0, 2)
    .map((charge) => ({
      key: `charge-${charge.key}`,
      tone: 'warm',
      title: charge.name,
      body: `${money(charge.amount_cents, settings.value.currency)} pendiente este periodo.`,
  }))
  return [...items, ...upcomingCharges].slice(0, 3)
})
const categoryLookup = computed(() => new Map(categories.value.map((category) => [category.id, category])))
const accountLookup = computed(() => new Map(accounts.value.map((account) => [account.id, account])))
const periodExpenses = computed(() => {
  const start = activeBudgetPeriod.value.start
  const end = activeBudgetPeriod.value.end
  return transactions.value.filter((transaction) => {
    return transaction.transaction_type === 'expense' && transaction.date >= start && transaction.date <= end
  })
})
const expenseFeedCategoryOptions = computed(() => {
  const options = new Map<number, { id: number; label: string }>()
  for (const transaction of periodExpenses.value) {
    if (!transaction.category || options.has(transaction.category)) continue
    const category = categoryLookup.value.get(transaction.category)
    const categoryName = transaction.category_name ?? category?.name ?? 'Sin categoría'
    const memberName = transaction.member_name ?? category?.member_name
    options.set(transaction.category, {
      id: transaction.category,
      label: memberName ? `${categoryName} · ${memberName}` : categoryName,
    })
  }
  return [...options.values()].sort((a, b) => a.label.localeCompare(b.label, 'es-MX'))
})
const expenseFeedAccountTypeOptions = computed(() => {
  const accountTypes = new Set<string>()
  for (const transaction of periodExpenses.value) {
    const account = accountForTransaction(transaction)
    if (account) accountTypes.add(account.account_type)
  }
  return ['cash', 'debit_card', 'credit_card', 'bank']
    .filter((accountType) => accountTypes.has(accountType))
    .map((accountType) => ({ value: `type:${accountType}`, label: accountTypeLabel(accountType) }))
})
const expenseFeedAccountOptions = computed(() => {
  const options = new Map<number, { value: string; label: string }>()
  for (const transaction of periodExpenses.value) {
    const account = accountForTransaction(transaction)
    if (!account || options.has(account.id)) continue
    options.set(account.id, {
      value: `account:${account.id}`,
      label: `${account.name} · ${accountTypeLabel(account.account_type)}`,
    })
  }
  return [...options.values()].sort((a, b) => a.label.localeCompare(b.label, 'es-MX'))
})
const hasUnaccountedPeriodExpenses = computed(() => periodExpenses.value.some((transaction) => !transaction.account))
const filteredPeriodExpenses = computed(() => {
  const categoryId = Number(expenseFeedCategoryId.value)
  return periodExpenses.value.filter((transaction) => {
    const matchesCategory =
      !expenseFeedCategoryId.value || !Number.isFinite(categoryId) || transaction.category === categoryId
    return matchesCategory && transactionMatchesExpensePaymentFilter(transaction)
  })
})
const expenseFeedHasActiveFilters = computed(() => Boolean(expenseFeedCategoryId.value || expenseFeedPaymentMethod.value))
const reviewedFilteredExpenseCount = computed(
  () => filteredPeriodExpenses.value.filter((transaction) => reviewedExpenseIds.value.has(transaction.id)).length,
)
const remainingReviewExpenseCount = computed(() =>
  Math.max(filteredPeriodExpenses.value.length - reviewedFilteredExpenseCount.value, 0),
)
const expenseReviewProgressLabel = computed(() => {
  if (!filteredPeriodExpenses.value.length) return 'Sin gastos'
  if (!remainingReviewExpenseCount.value) return 'Todo revisado'
  const noun = remainingReviewExpenseCount.value === 1 ? 'pendiente' : 'pendientes'
  return `${reviewedFilteredExpenseCount.value}/${filteredPeriodExpenses.value.length} revisados · ${remainingReviewExpenseCount.value} ${noun}`
})
const selectedExpenseFeedCategoryLabel = computed(() => {
  const categoryId = Number(expenseFeedCategoryId.value)
  return expenseFeedCategoryOptions.value.find((category) => category.id === categoryId)?.label ?? 'esta categoría'
})
const selectedExpenseFeedPaymentLabel = computed(() => {
  if (!expenseFeedPaymentMethod.value) return ''
  if (expenseFeedPaymentMethod.value === 'none') return 'sin cuenta'
  if (expenseFeedPaymentMethod.value.startsWith('type:')) {
    return accountTypeLabel(expenseFeedPaymentMethod.value.replace('type:', ''))
  }
  return (
    expenseFeedAccountOptions.value.find((option) => option.value === expenseFeedPaymentMethod.value)?.label ??
    'ese método de pago'
  )
})
const periodExpenseTotal = computed(() =>
  periodExpenses.value.reduce((total, transaction) => total + transaction.amount_cents, 0),
)
const filteredPeriodExpenseTotal = computed(() =>
  filteredPeriodExpenses.value.reduce((total, transaction) => total + transaction.amount_cents, 0),
)
const expenseFeedSummaryLabel = computed(() => {
  const total =
    expenseFeedCategoryId.value || expenseFeedPaymentMethod.value
      ? filteredPeriodExpenseTotal.value
      : periodExpenseTotal.value
  const count = filteredPeriodExpenses.value.length
  const noun = count === 1 ? 'gasto' : 'gastos'
  return `${count} ${noun} · ${money(total, settings.value.currency)}`
})
const expenseFeedEmptyMessage = computed(() => {
  if (!periodExpenses.value.length) return 'Sin gastos en este periodo.'
  const categoryText = expenseFeedCategoryId.value ? ` de ${selectedExpenseFeedCategoryLabel.value}` : ''
  const paymentText = expenseFeedPaymentMethod.value ? ` pagados con ${selectedExpenseFeedPaymentLabel.value}` : ''
  return `Sin gastos${categoryText}${paymentText} en este periodo.`
})
const recurringExpectedCharges = computed(() =>
  expectedCharges.value.filter((charge) => charge.source_type === 'recurring'),
)
const recurringExpectedTotal = computed(() =>
  recurringExpectedCharges.value.reduce((total, charge) => total + charge.amount_cents, 0),
)
const activeRecurringExpenses = computed(() => recurringExpenses.value.filter((expense) => expense.is_active))
const activeRecurringTotal = computed(() =>
  activeRecurringExpenses.value.reduce((total, expense) => total + expense.amount_cents, 0),
)
const recurringCommitmentRows = computed(() =>
  activeRecurringExpenses.value.map((expense) => ({
    expense,
    charge: recurringExpectedCharges.value.find((charge) => charge.source_id === expense.id),
  })),
)
const projectedInstallmentPeriods = computed(() => installmentProjection.value?.periods ?? [])
const projectedInstallmentPlans = computed(() =>
  (installmentProjection.value?.plans ?? []).filter((plan) => plan.projected_total_cents || plan.current_amount_cents),
)
const installmentPlanLookup = computed(() => new Map(installmentPlans.value.map((plan) => [plan.id, plan])))
const installmentCalculatedEndDate = computed(() => installmentEndDateFor(installmentForm.start_date, installmentForm.months_count))
const currentInstallmentTotal = computed(() => installmentProjection.value?.current_total_cents ?? 0)
const registeredInstallmentTotal = computed(() =>
  projectedInstallmentPlans.value.reduce((total, plan) => total + plan.total_amount_cents, 0),
)
const creditCardPaymentCards = computed(() => creditCardPaymentSummary.value?.cards ?? [])
const creditCardInterestFreeTotal = computed(() => creditCardPaymentSummary.value?.total_cents ?? 0)
const offBudgetTotal = computed(() => offBudgetSummary.value?.totals.total_cents ?? 0)
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
const filteredCommitmentCategories = computed(() => {
  const query = commitmentCategorySearch.value.trim().toLowerCase()
  if (!query) return visibleCategories.value
  return visibleCategories.value.filter((category) => {
    return `${category.name} ${category.member_name ?? ''}`.toLowerCase().includes(query)
  })
})
const filteredCommitmentAccounts = computed(() => {
  const query = commitmentAccountSearch.value.trim().toLowerCase()
  if (!query) return activeAccounts.value
  return activeAccounts.value.filter((account) => {
    return `${account.name} ${account.account_type}`.toLowerCase().includes(query)
  })
})
const selectedExpenseCategory = computed(() =>
  expenseForm.category ? categoryLookup.value.get(Number(expenseForm.category)) ?? null : null,
)
const selectedTransactionEditCategory = computed(() =>
  transactionEditForm.category ? categoryLookup.value.get(Number(transactionEditForm.category)) ?? null : null,
)
const selectedCommitmentCategory = computed(() => {
  const categoryId = commitmentCategoryValue()
  return categoryId ? categoryLookup.value.get(Number(categoryId)) ?? null : null
})
const expenseIsTrackingOnly = computed(() => selectedExpenseCategory.value?.budget_treatment === 'tracking_only')
const transactionEditIsTrackingOnly = computed(() => selectedTransactionEditCategory.value?.budget_treatment === 'tracking_only')
const commitmentIsTrackingOnly = computed(() => selectedCommitmentCategory.value?.budget_treatment === 'tracking_only')
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
const editingCategory = computed(() => categories.value.find((category) => category.id === editingCategoryId.value) ?? null)
const categoryBudgetChanged = computed(() => {
  if (!editingCategory.value) return false
  if (categoryForm.budget_treatment === 'tracking_only') return false
  return centsFromInput(categoryForm.monthly_budget) !== editingCategory.value.monthly_budget_cents
})
const categoryBehaviorLabel = computed(() => {
  if (categoryForm.budget_treatment === 'tracking_only') return 'Fuera de presupuesto'
  if (categoryForm.budget_behavior === 'carryover') return 'Acumula saldo'
  return 'Se reinicia cada mes'
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
const spendingChartTotal = computed(() =>
  (summary.value?.categories ?? []).reduce((total, category) => total + Math.max(category.spent_cents, 0), 0),
)
const spendingChartSegments = computed<SpendingChartSegment[]>(() => {
  const spentCategories = (summary.value?.categories ?? [])
    .filter((category) => category.spent_cents > 0)
    .sort((a, b) => b.spent_cents - a.spent_cents)

  if (!spentCategories.length || spendingChartTotal.value <= 0) return []

  return spentCategories.map((category) => ({
    key: `category-${category.category_id}`,
    label: category.member?.name ? `${category.category_name} · ${category.member.name}` : category.category_name,
    amount_cents: category.spent_cents,
    percent: (category.spent_cents / spendingChartTotal.value) * 100,
    color: category.color,
    icon: category.icon,
    category_ids: [category.category_id],
  }))
})
const spendingChartStyle = computed(() => {
  if (!spendingChartSegments.value.length) {
    return { '--spending-chart-fill': 'conic-gradient(var(--surface-tint), var(--surface-tint))' }
  }
  let cursor = 0
  const separator = spendingChartSegments.value.length > 1 ? 0.58 : 0
  const stops = spendingChartSegments.value.map((segment) => {
    const start = cursor
    cursor += segment.percent
    const colorEnd = Math.max(start, cursor - Math.min(separator, segment.percent * 0.42))
    return `${segment.color} ${start.toFixed(2)}% ${colorEnd.toFixed(2)}%, var(--surface) ${colorEnd.toFixed(2)}% ${cursor.toFixed(2)}%`
  })
  return { '--spending-chart-fill': `conic-gradient(${stops.join(', ')})` }
})
const spendingChartLeadSegment = computed(() => spendingChartSegments.value[0] ?? null)

onMounted(async () => {
  systemThemeMediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  updateSystemTheme(systemThemeMediaQuery)
  systemThemeMediaQuery.addEventListener('change', updateSystemTheme)
  await store.bootstrap()
  syncSettingsForm()
  if (inviteToken.value && !user.value && !firstRunClaimRequired.value) {
    await resolveCurrentInvitation()
  }
  document.addEventListener('visibilitychange', handleVisibilityChange)
  window.addEventListener('pointerdown', handleAuthActivity, { passive: true })
  window.addEventListener('keydown', handleAuthActivity)
})

watch(appToday, (nextDate, previousDate) => {
  if (selectedDate.value !== previousDate) return
  syncDefaultFormDates(nextDate, previousDate)
  selectedDate.value = nextDate
})

watch(selectedDate, async (nextDate, previousDate) => {
  selectedCategoryId.value = null
  expenseFeedCategoryId.value = ''
  expenseFeedPaymentMethod.value = ''
  syncDefaultFormDates(nextDate, previousDate)
  if (!user.value) return
  try {
    await refreshSelectedPeriod()
  } catch {
    showNotice('No pudimos actualizar el periodo. Intenta de nuevo.', 'error')
  }
})

watch([expenseFeedCategoryId, expenseFeedPaymentMethod], () => resetExpenseReview())

watch(filteredPeriodExpenses, (nextExpenses) => {
  if (!expenseFeedHasActiveFilters.value || !nextExpenses.length) {
    resetExpenseReview()
    return
  }
  const visibleIds = new Set(nextExpenses.map((transaction) => transaction.id))
  const nextReviewedIds = new Set(
    [...reviewedExpenseIds.value].filter((transactionId) => visibleIds.has(transactionId)),
  )
  if (nextReviewedIds.size !== reviewedExpenseIds.value.size) reviewedExpenseIds.value = nextReviewedIds
})

watch(
  () => [view.value, expensesTab.value] as const,
  ([nextView, nextExpensesTab]) => {
    if (nextView !== 'expenses' || nextExpensesTab !== 'feed') resetExpenseReview()
  },
)

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

function centsToInput(cents: number) {
  return (cents / 100).toFixed(2)
}

function lookupText(value: string) {
  return normalizeText(value).toLocaleLowerCase('es-MX')
}

function secondaryCommitmentLabel(name: string, merchant: string) {
  const cleanMerchant = normalizeText(merchant)
  if (!cleanMerchant || lookupText(cleanMerchant) === lookupText(name)) return ''
  return cleanMerchant
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

function addCalendarMonths(value: Date, months: number) {
  const monthIndex = value.getMonth() + months
  const year = value.getFullYear() + Math.floor(monthIndex / 12)
  const month = ((monthIndex % 12) + 12) % 12
  const lastDay = new Date(year, month + 1, 0).getDate()
  return new Date(year, month, Math.min(value.getDate(), lastDay))
}

function installmentEndDateFor(startDate: string, monthsCount: string) {
  const months = Number(monthsCount)
  if (!startDate || !Number.isInteger(months) || months < 1) return ''
  return formatIsoDate(addCalendarMonths(parseIsoDate(startDate), months - 1))
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

function syncSettingsForm() {
  settingsForm.cutoff_day = settings.value.cutoff_day
  settingsForm.time_zone = settings.value.time_zone
}

function syncDefaultFormDates(nextDate: string, previousDate: string) {
  if (expenseForm.date === previousDate) expenseForm.date = nextDate
  if (transactionEditForm.date === previousDate) transactionEditForm.date = nextDate
  if (categoryForm.carryover_start_date === previousDate) categoryForm.carryover_start_date = nextDate
  if (categoryForm.budget_effective_date === previousDate) categoryForm.budget_effective_date = nextDate
  if (recurringForm.start_date === previousDate) recurringForm.start_date = nextDate
  if (installmentForm.start_date === previousDate) installmentForm.start_date = nextDate
}

function isValidTimeZone(value: string) {
  try {
    new Intl.DateTimeFormat('en-US', { timeZone: value }).format(new Date())
    return true
  } catch {
    return false
  }
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
    showNotice(apiErrorMessage(err, 'No pudimos guardar. Revisa los datos e intenta de nuevo.'), 'error')
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
  if (!fullName) {
    showNotice('Falta nombre completo. Escríbelo para crear el primer acceso.', 'error')
    return
  }
  if (!displayName) {
    showNotice('Falta nombre visible. Escribe cómo quieres aparecer en la app.', 'error')
    return
  }
  if (!email) {
    showNotice('Falta correo. Escríbelo para crear el primer acceso.', 'error')
    return
  }
  if (!password) {
    showNotice('Falta contraseña. Escribe una para crear el primer acceso.', 'error')
    return
  }
  if (password !== claimForm.confirmPassword) {
    showNotice('Las contraseñas no coinciden. Revisa ambos campos e intenta de nuevo.', 'error')
    return
  }
  await runAction('claim', 'Burn Rate quedó listo para tu casa.', async () => {
    await store.claimFirstRun({ full_name: fullName, display_name: displayName, email, password })
    claimForm.password = ''
    claimForm.confirmPassword = ''
    syncSettingsForm()
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
    syncSettingsForm()
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
  if (!fullName) {
    showNotice('Falta tu nombre completo. Escríbelo para aceptar la invitación.', 'error')
    return
  }
  if (!displayName) {
    showNotice('Falta nombre visible. Escribe cómo quieres aparecer en la app.', 'error')
    return
  }
  if (!password) {
    showNotice('Falta contraseña. Escríbela para entrar a Burn Rate.', 'error')
    return
  }
  if (password !== acceptInviteForm.confirmPassword) {
    showNotice('Las contraseñas no coinciden. Revisa ambos campos e intenta de nuevo.', 'error')
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
    syncSettingsForm()
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
    showNotice('Falta correo. Escríbelo para crear la invitación.', 'error')
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
    showNotice('Falta comercio o concepto. Escríbelo antes de guardar el gasto.', 'error')
    return
  }
  if (amountCents <= 0) {
    showNotice('Falta monto válido. Escribe una cantidad mayor a cero.', 'error')
    return
  }
  if (!expenseForm.category) {
    showNotice('Falta categoría. Elige una para guardar el gasto.', 'error')
    return
  }
  if (!expenseIsTrackingOnly.value && !expenseForm.account) {
    showNotice('Falta cuenta. Elige desde dónde se pagó.', 'error')
    return
  }
  await runAction(
    'expense',
    expenseIsTrackingOnly.value ? 'Registro fuera de presupuesto guardado.' : 'Gasto guardado. El presupuesto ya está actualizado.',
    async () => {
    await store.createTransaction({
      transaction_type: 'expense',
      merchant,
      amount_cents: amountCents,
      date: expenseForm.date,
      account: expenseIsTrackingOnly.value ? null : Number(expenseForm.account),
      category: Number(expenseForm.category),
      note: expenseForm.note,
    })
    expenseForm.merchant = ''
    expenseForm.amount = ''
    expenseForm.note = ''
    merchantSuggestionsOpen.value = false
    expensesTab.value = 'feed'
    },
  )
}

function openTransactionEdit(transaction: Transaction) {
  editingTransactionId.value = transaction.id
  deleteConfirmTransactionId.value = null
  transactionEditForm.merchant = transaction.merchant
  transactionEditForm.amount = centsToInput(transaction.amount_cents)
  transactionEditForm.category = transaction.category ? String(transaction.category) : ''
  transactionEditForm.account = transaction.account ? String(transaction.account) : ''
  transactionEditForm.date = transaction.date
  transactionEditForm.note = transaction.note
}

function cancelTransactionEdit() {
  editingTransactionId.value = null
  deleteConfirmTransactionId.value = null
  transactionEditForm.merchant = ''
  transactionEditForm.amount = ''
  transactionEditForm.category = ''
  transactionEditForm.account = ''
  transactionEditForm.date = selectedDate.value
  transactionEditForm.note = ''
}

async function saveTransactionEdit(transaction: Transaction) {
  const merchant = normalizeText(transactionEditForm.merchant)
  const amountCents = centsFromInput(transactionEditForm.amount)
  if (!merchant) {
    showNotice('Falta comercio o concepto. Escríbelo antes de guardar el cambio.', 'error')
    return
  }
  if (amountCents <= 0) {
    showNotice('Falta monto válido. Escribe una cantidad mayor a cero.', 'error')
    return
  }
  if (!transactionEditForm.category) {
    showNotice('Falta categoría. Elige una para actualizar el gasto.', 'error')
    return
  }
  if (!transactionEditIsTrackingOnly.value && !transactionEditForm.account) {
    showNotice('Falta cuenta. Elige desde dónde se pagó.', 'error')
    return
  }
  await runAction(
    `edit-transaction-${transaction.id}`,
    transactionEditIsTrackingOnly.value ? 'Registro fuera de presupuesto actualizado.' : 'Gasto actualizado. El presupuesto ya está recalculado.',
    async () => {
    await store.updateTransaction(transaction.id, {
      merchant,
      amount_cents: amountCents,
      date: transactionEditForm.date,
      account: transactionEditIsTrackingOnly.value ? null : Number(transactionEditForm.account),
      category: Number(transactionEditForm.category),
      note: transactionEditForm.note,
    })
    cancelTransactionEdit()
    },
  )
}

function transactionLabel(transaction: Transaction) {
  return transaction.merchant || transaction.category_name || 'este gasto'
}

function isConfirmingTransactionDelete(transactionId: Transaction['id']) {
  return deleteConfirmTransactionId.value === transactionId
}

function startTransactionDelete(transaction: Transaction) {
  deleteConfirmTransactionId.value = transaction.id
}

function cancelTransactionDelete() {
  deleteConfirmTransactionId.value = null
}

async function deleteTransaction(transaction: Transaction) {
  const successMessage = transactionIsTrackingOnly(transaction)
    ? 'Registro fuera de presupuesto eliminado.'
    : 'Gasto eliminado. El presupuesto y la cuenta ya están recalculados.'
  await runAction(`delete-transaction-${transaction.id}`, successMessage, async () => {
    await store.deleteTransaction(transaction.id, transaction.date)
    deleteConfirmTransactionId.value = null
  })
}

async function submitAccount() {
  const name = normalizeText(accountForm.name)
  if (!name) {
    showNotice('Falta nombre de cuenta. Escríbelo para guardar.', 'error')
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
  accountFormOpen.value = true
  editingAccountId.value = account.id
  accountForm.name = account.name
  accountForm.account_type = account.account_type
  accountForm.initial_balance = String(account.initial_balance_cents / 100)
  accountForm.color = account.color || '#7c6250'
  accountForm.is_active = account.is_active
}

function resetAccountForm() {
  accountFormOpen.value = false
  editingAccountId.value = null
  accountForm.name = ''
  accountForm.account_type = 'cash'
  accountForm.initial_balance = ''
  accountForm.color = '#7c6250'
  accountForm.is_active = true
}

function startAccountForm() {
  resetAccountForm()
  accountFormOpen.value = true
}

function accountTypeLabel(accountType: string) {
  if (accountType === 'cash') return 'Efectivo'
  if (accountType === 'bank') return 'Banco'
  if (accountType === 'debit_card') return 'Tarjeta débito'
  if (accountType === 'credit_card') return 'Tarjeta crédito'
  return accountType
}

function accountForTransaction(transaction: Transaction) {
  return transaction.account ? accountLookup.value.get(transaction.account) ?? null : null
}

function transactionMatchesExpensePaymentFilter(transaction: Transaction) {
  const filter = expenseFeedPaymentMethod.value
  if (!filter) return true
  if (filter === 'none') return !transaction.account
  if (filter.startsWith('account:')) return String(transaction.account ?? '') === filter.replace('account:', '')
  if (filter.startsWith('type:')) return accountForTransaction(transaction)?.account_type === filter.replace('type:', '')
  return true
}

function resetExpenseReview() {
  expenseReviewMode.value = false
  reviewedExpenseIds.value = new Set<Transaction['id']>()
}

function toggleExpenseReviewMode() {
  if (!expenseFeedHasActiveFilters.value || !filteredPeriodExpenses.value.length) return
  expenseReviewMode.value = !expenseReviewMode.value
  reviewedExpenseIds.value = new Set<Transaction['id']>()
}

function transactionIsReviewed(transaction: Transaction) {
  return reviewedExpenseIds.value.has(transaction.id)
}

function toggleExpenseReviewed(transactionId: Transaction['id']) {
  if (!expenseReviewMode.value) return
  const nextReviewedIds = new Set(reviewedExpenseIds.value)
  if (nextReviewedIds.has(transactionId)) {
    nextReviewedIds.delete(transactionId)
  } else {
    nextReviewedIds.add(transactionId)
  }
  reviewedExpenseIds.value = nextReviewedIds
}

function clearReviewedExpenses() {
  reviewedExpenseIds.value = new Set<Transaction['id']>()
}

function clearExpenseFeedFilters() {
  resetExpenseReview()
  expenseFeedCategoryId.value = ''
  expenseFeedPaymentMethod.value = ''
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
    showNotice('Falta nombre de la persona. Escríbelo para guardar.', 'error')
    return
  }
  if (memberForm.is_admin) memberForm.has_access = true
  if (memberForm.has_access && !username) {
    showNotice('Falta usuario. Escríbelo para dar acceso a la app.', 'error')
    return
  }
  if (!editingMemberId.value && memberForm.has_access && !password) {
    showNotice('Falta clave temporal. Escríbela para dar acceso por primera vez.', 'error')
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
  memberFormOpen.value = true
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
  memberFormOpen.value = false
  editingMemberId.value = null
  memberForm.name = ''
  memberForm.color = '#b35320'
  memberForm.has_access = false
  memberForm.username = ''
  memberForm.email = ''
  memberForm.password = ''
  memberForm.is_admin = false
}

function startMemberForm() {
  resetMemberForm()
  memberFormOpen.value = true
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
  const isTrackingOnly = categoryForm.budget_treatment === 'tracking_only'
  const monthlyBudgetCents = isTrackingOnly ? 0 : centsFromInput(categoryForm.monthly_budget)
  const carryoverInitialBalanceCents = centsFromInput(categoryForm.carryover_initial_balance || '0')
  if (!name) {
    showNotice('Falta nombre de categoría. Escríbelo para guardar.', 'error')
    return
  }
  if (categoryForm.scope === 'personal' && !memberId) {
    showNotice('Falta persona. Elige a quién pertenece esta categoría.', 'error')
    return
  }
  if (!isTrackingOnly && monthlyBudgetCents <= 0) {
    showNotice('Falta presupuesto mensual válido. Escribe una cantidad mayor a cero.', 'error')
    return
  }
  if (!isTrackingOnly && !editingCategoryId.value && categoryForm.budget_behavior === 'carryover' && !categoryForm.carryover_start_date) {
    showNotice('Falta fecha de inicio. Indica desde cuándo acumula saldo.', 'error')
    return
  }
  if (editingCategoryId.value && categoryBudgetChanged.value && !categoryForm.budget_effective_date) {
    showNotice('Falta fecha del cambio. Indica desde cuándo aplica el nuevo presupuesto.', 'error')
    return
  }
  await runAction('category', editingCategoryId.value ? 'Categoría actualizada.' : 'Categoría guardada en el presupuesto.', async () => {
    const payload: Partial<Category> = {
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
      if (categoryBudgetChanged.value) {
        payload.budget_effective_date = categoryForm.budget_effective_date
      }
      await store.updateCategory(editingCategoryId.value, payload)
    } else {
      payload.budget_treatment = categoryForm.budget_treatment
      payload.budget_behavior = isTrackingOnly ? 'monthly_reset' : categoryForm.budget_behavior
      if (!isTrackingOnly && categoryForm.budget_behavior === 'carryover') {
        payload.carryover_initial_balance_cents = carryoverInitialBalanceCents
        payload.carryover_start_date = categoryForm.carryover_start_date
      }
      await store.createCategory(payload)
    }
    resetCategoryForm()
  })
}

function editCategory(category: Category) {
  categoryFormOpen.value = true
  editingCategoryId.value = category.id
  categoryForm.name = category.name
  categoryForm.scope = category.scope
  categoryForm.budget_treatment = category.budget_treatment
  categoryForm.member = category.member ? String(category.member) : ''
  categoryForm.monthly_budget = String(category.monthly_budget_cents / 100)
  categoryForm.budget_behavior = category.budget_behavior
  categoryForm.carryover_initial_balance = String(category.carryover_initial_balance_cents / 100)
  categoryForm.carryover_start_date = category.carryover_start_date || selectedDate.value
  categoryForm.budget_effective_date = selectedDate.value
  categoryForm.color = category.color
  categoryForm.icon = category.icon || 'tag'
  categoryForm.is_active = category.is_active
}

function resetCategoryForm() {
  categoryFormOpen.value = false
  editingCategoryId.value = null
  categoryForm.name = ''
  categoryForm.scope = 'global'
  categoryForm.budget_treatment = 'budgeted'
  categoryForm.member = ''
  categoryForm.monthly_budget = ''
  categoryForm.budget_behavior = 'monthly_reset'
  categoryForm.carryover_initial_balance = ''
  categoryForm.carryover_start_date = selectedDate.value
  categoryForm.budget_effective_date = selectedDate.value
  categoryForm.color = '#e11d48'
  categoryForm.icon = 'tag'
  categoryForm.is_active = true
}

function startCategoryForm() {
  resetCategoryForm()
  categoryFormOpen.value = true
}

async function submitRecurring() {
  const name = normalizeText(recurringForm.name)
  const merchant = normalizeText(recurringForm.merchant)
  const amountCents = centsFromInput(recurringForm.amount)
  const chargeDay = Math.min(28, Math.max(1, Number(recurringForm.charge_day) || 1))
  if (!name) {
    showNotice('Falta nombre del pago mensual. Escríbelo para guardar.', 'error')
    return
  }
  if (!merchant) {
    showNotice('Falta comercio del pago mensual. Escríbelo para guardar.', 'error')
    return
  }
  if (amountCents <= 0) {
    showNotice('Falta monto mensual válido. Escribe una cantidad mayor a cero.', 'error')
    return
  }
  if (!recurringForm.category) {
    showNotice('Falta categoría. Elige dónde cae este pago mensual.', 'error')
    return
  }
  if (recurringForm.auto_charge && !commitmentIsTrackingOnly.value && !recurringForm.account) {
    showNotice('El cargo automático necesita una cuenta configurada.', 'error')
    return
  }
  if (recurringForm.end_date && recurringForm.end_date < recurringForm.start_date) {
    showNotice('La fecha final queda antes del inicio. Corrige una de las dos fechas.', 'error')
    return
  }
  await runAction('recurring', 'Pago mensual guardado.', async () => {
    await store.createRecurring({
      name,
      merchant,
      amount_cents: amountCents,
      category: Number(recurringForm.category),
      account: commitmentIsTrackingOnly.value ? null : recurringForm.account ? Number(recurringForm.account) : null,
      start_date: recurringForm.start_date,
      end_date: recurringForm.end_date || null,
      charge_day: chargeDay,
      auto_charge: recurringForm.auto_charge,
      is_active: true,
    })
    recurringForm.name = ''
    recurringForm.merchant = ''
    recurringForm.amount = ''
    recurringForm.auto_charge = false
    showCommitmentForm.value = false
    commitmentTab.value = 'subscriptions'
  })
}

async function submitInstallment() {
  const name = normalizeText(installmentForm.name)
  const merchant = normalizeText(installmentForm.merchant)
  const totalAmountCents = centsFromInput(installmentForm.total_amount)
  const monthsCount = Number(installmentForm.months_count)
  if (!name) {
    showNotice('Falta nombre de la compra a meses. Escríbelo para guardar.', 'error')
    return
  }
  if (!merchant) {
    showNotice('Falta comercio de la compra a meses. Escríbelo para guardar.', 'error')
    return
  }
  if (totalAmountCents <= 0) {
    showNotice('Falta monto total válido. Escribe una cantidad mayor a cero.', 'error')
    return
  }
  if (!installmentForm.category) {
    showNotice('Falta categoría. Elige dónde cae esta compra a meses.', 'error')
    return
  }
  if (!Number.isInteger(monthsCount) || monthsCount < 1) {
    showNotice('Faltan meses válidos. Indica cuántos pagos tendrá la compra.', 'error')
    return
  }
  if (!installmentCalculatedEndDate.value) {
    showNotice('Falta fecha válida de primer pago. Revisa la fecha antes de guardar.', 'error')
    return
  }
  await runAction('installment', 'Compra a meses guardada.', async () => {
    await store.createInstallment({
      name,
      merchant,
      total_amount_cents: totalAmountCents,
      category: Number(installmentForm.category),
      account: commitmentIsTrackingOnly.value ? null : installmentForm.account ? Number(installmentForm.account) : null,
      start_date: installmentForm.start_date,
      months_count: monthsCount,
      round_up_monthly_payment: installmentForm.round_up_monthly_payment,
      is_active: true,
    })
    installmentForm.name = ''
    installmentForm.merchant = ''
    installmentForm.total_amount = ''
    installmentForm.months_count = '12'
    installmentForm.round_up_monthly_payment = true
    showCommitmentForm.value = false
    commitmentTab.value = 'msi'
  })
}

function isEditingCommitment(type: CommitmentEditKind, id: number) {
  return editingCommitment.value?.type === type && editingCommitment.value.id === id
}

function isConfirmingCommitmentDelete(type: CommitmentEditKind, id: number) {
  return deleteConfirmCommitment.value?.type === type && deleteConfirmCommitment.value.id === id
}

function openCommitmentEdit(
  type: CommitmentEditKind,
  item: {
    id: number
    name: string
    merchant: string
    category?: number | { id: number }
    account?: number | { id: number } | null
    charge_day?: number
    auto_charge?: boolean
  },
) {
  editingCommitment.value = { type, id: item.id }
  deleteConfirmCommitment.value = null
  commitmentEditForm.name = item.name
  commitmentEditForm.merchant = item.merchant
  if (type === 'installment') {
    commitmentEditForm.category = typeof item.category === 'object' ? String(item.category.id) : String(item.category ?? '')
    commitmentEditForm.account = ''
    commitmentEditForm.charge_day = 1
    commitmentEditForm.auto_charge = false
  } else {
    commitmentEditForm.category = ''
    commitmentEditForm.account =
      typeof item.account === 'object' && item.account !== null ? String(item.account.id) : String(item.account ?? '')
    commitmentEditForm.charge_day = item.charge_day ?? 1
    commitmentEditForm.auto_charge = Boolean(item.auto_charge)
  }
}

function closeCommitmentEdit() {
  editingCommitment.value = null
  deleteConfirmCommitment.value = null
  commitmentEditForm.name = ''
  commitmentEditForm.merchant = ''
  commitmentEditForm.category = ''
  commitmentEditForm.account = ''
  commitmentEditForm.charge_day = 1
  commitmentEditForm.auto_charge = false
}

function startCommitmentDelete(type: CommitmentEditKind, id: number) {
  if (!canManageSettings.value) {
    showNotice('Solo un administrador puede eliminar pagos planeados.', 'error')
    return
  }
  deleteConfirmCommitment.value = { type, id }
}

function cancelCommitmentDelete() {
  deleteConfirmCommitment.value = null
}

function installmentPlanDetail(id: number) {
  return installmentPlanLookup.value.get(id)
}

async function saveRecurringExpenseEdit(expense: { id: number }) {
  const name = normalizeText(commitmentEditForm.name)
  const merchant = normalizeText(commitmentEditForm.merchant)
  const chargeDay = Math.min(28, Math.max(1, Number(commitmentEditForm.charge_day) || 1))
  if (!name) {
    showNotice('Falta nombre del pago mensual. Escríbelo para guardar.', 'error')
    return
  }
  if (!merchant) {
    showNotice('Falta comercio del pago mensual. Escríbelo para guardar.', 'error')
    return
  }
  if (commitmentEditForm.auto_charge && !commitmentEditForm.account) {
    showNotice('El cargo automático necesita una cuenta configurada.', 'error')
    return
  }
  await runAction(`edit-recurring-${expense.id}`, 'Pago mensual actualizado.', async () => {
    await store.updateRecurring(expense.id, {
      name,
      merchant,
      account: commitmentEditForm.account ? Number(commitmentEditForm.account) : null,
      charge_day: chargeDay,
      auto_charge: commitmentEditForm.auto_charge,
    })
    closeCommitmentEdit()
  })
}

async function saveInstallmentPlanEdit(plan: { id: number }) {
  const name = normalizeText(commitmentEditForm.name)
  const merchant = normalizeText(commitmentEditForm.merchant)
  if (!name) {
    showNotice('Falta nombre de la compra a meses. Escríbelo para guardar.', 'error')
    return
  }
  if (!merchant) {
    showNotice('Falta comercio de la compra a meses. Escríbelo para guardar.', 'error')
    return
  }
  if (!commitmentEditForm.category) {
    showNotice('Falta categoría. Elige dónde cae esta compra a meses.', 'error')
    return
  }
  await runAction(`edit-installment-${plan.id}`, 'Compra a meses actualizada.', async () => {
    await store.updateInstallment(plan.id, { name, merchant, category: Number(commitmentEditForm.category) })
    closeCommitmentEdit()
  })
}

async function deleteRecurringExpense(expense: { id: number }) {
  if (!canManageSettings.value) {
    showNotice('Solo un administrador puede eliminar pagos planeados.', 'error')
    return
  }
  await runAction(`delete-recurring-${expense.id}`, 'Pago mensual eliminado.', async () => {
    await store.deleteRecurring(expense.id)
    closeCommitmentEdit()
  })
}

async function deleteInstallmentPlan(plan: { id: number }) {
  if (!canManageSettings.value) {
    showNotice('Solo un administrador puede eliminar pagos planeados.', 'error')
    return
  }
  await runAction(`delete-installment-${plan.id}`, 'Compra a meses eliminada.', async () => {
    await store.deleteInstallment(plan.id)
    closeCommitmentEdit()
  })
}

async function saveSettings() {
  const cutoffDay = Math.min(28, Math.max(1, Number(settingsForm.cutoff_day) || 1))
  const timeZone = normalizeText(settingsForm.time_zone) || settings.value.time_zone
  if (!isValidTimeZone(timeZone)) {
    showNotice('La zona horaria no es válida. Usa un identificador como America/Mexico_City.', 'error')
    return
  }
  await runAction('settings', 'Calendario actualizado.', async () => {
    await store.saveSettings({ ...settings.value, cutoff_day: cutoffDay, time_zone: timeZone })
    syncSettingsForm()
    await refreshSelectedPeriod()
  })
}

async function confirmCharge(charge: ExpectedCharge) {
  const isTrackingOnly = charge.category.budget_treatment === 'tracking_only'
  const fallback = isTrackingOnly ? null : (charge.account?.id ?? activeAccounts.value[0]?.id ?? null)
  if (!isTrackingOnly && !fallback) {
    showNotice('Falta cuenta activa. Crea o activa una cuenta antes de marcar este pago.', 'error')
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
  cycleMenuOpen.value = false
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

function cycleRelativeLabel(cycle: BudgetCycleOption) {
  if (cycle.offset === 0) return 'Ciclo actual'
  return cycle.offset === -1 ? 'Ciclo anterior' : `${Math.abs(cycle.offset)} ciclos antes`
}

function selectBudgetCycle(value: string) {
  selectedDate.value = value
  cycleMenuOpen.value = false
}

function closeCycleMenuOnBlur(event: FocusEvent) {
  const nextTarget = event.relatedTarget
  const currentTarget = event.currentTarget
  if (currentTarget instanceof HTMLElement && nextTarget instanceof Node && currentTarget.contains(nextTarget)) return
  cycleMenuOpen.value = false
}

function shiftBudgetCycle(offset: number) {
  if (offset < 0 && !canShiftToPreviousCycle.value) return
  if (offset > 0 && !canShiftToNextCycle.value) return
  const currentStart = parseIsoDate(activeBudgetPeriod.value.start)
  const nextStart = formatIsoDate(addMonths(currentStart, offset))
  selectedDate.value = nextStart > currentBudgetPeriod.value.start ? currentBudgetPeriod.value.start : nextStart
  cycleMenuOpen.value = false
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
  const category = categoryLookup.value.get(categoryId)
  if (category?.budget_treatment === 'tracking_only') expenseForm.account = ''
}

function chooseExpenseAccount(accountId: number) {
  expenseForm.account = String(accountId)
}

function commitmentCategoryValue() {
  return commitmentKind.value === 'subscription' ? recurringForm.category : installmentForm.category
}

function commitmentAccountValue() {
  return commitmentKind.value === 'subscription' ? recurringForm.account : installmentForm.account
}

function commitmentAccountStatusLabel() {
  if (commitmentKind.value === 'subscription' && recurringForm.auto_charge && !recurringForm.account) {
    return 'Necesaria'
  }
  return commitmentAccountValue() ? 'Lista' : 'Opcional'
}

function chooseCommitmentCategory(categoryId: number) {
  if (commitmentKind.value === 'subscription') {
    recurringForm.category = String(categoryId)
    const category = categoryLookup.value.get(categoryId)
    if (category?.budget_treatment === 'tracking_only') recurringForm.account = ''
    return
  }
  installmentForm.category = String(categoryId)
  const category = categoryLookup.value.get(categoryId)
  if (category?.budget_treatment === 'tracking_only') installmentForm.account = ''
}

function chooseCommitmentAccount(accountId: number | null) {
  const value = accountId ? String(accountId) : ''
  if (commitmentKind.value === 'subscription') {
    recurringForm.account = value
    return
  }
  installmentForm.account = value
}

function submitCurrentCommitment() {
  if (commitmentKind.value === 'subscription') {
    return submitRecurring()
  }
  return submitInstallment()
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

function percentOfBudget(amountCents: number, budgetCents: number) {
  if (budgetCents <= 0) return 0
  return Math.max(0, Math.min(100, (amountCents / budgetCents) * 100))
}

function categorySpentPercent(item: BudgetCategorySummary) {
  return percentOfBudget(Math.max(item.spent_cents, 0), item.budget_cents)
}

function categoryCommittedPercent(item: BudgetCategorySummary) {
  const spentWithinBudgetCents = Math.min(Math.max(item.spent_cents, 0), Math.max(item.budget_cents, 0))
  const remainingBudgetCents = Math.max(item.budget_cents - spentWithinBudgetCents, 0)
  const visibleCommittedCents = Math.min(Math.max(item.expected_cents, 0), remainingBudgetCents)
  return percentOfBudget(visibleCommittedCents, item.budget_cents)
}

function categoryRealOverspent(item: BudgetCategorySummary) {
  return item.real_available_cents < 0
}

function categoryProjectedOverspent(item: BudgetCategorySummary) {
  return item.real_available_cents >= 0 && item.available_cents < 0
}

function categoryStatusLabel(item: BudgetCategorySummary) {
  if (categoryProjectedOverspent(item)) return 'Compromiso'
  if (categoryRealOverspent(item)) return 'Revisar'
  return item.budget_behavior === 'carryover' ? 'Acumula' : 'Bien'
}

function transactionIsTrackingOnly(transaction: Transaction) {
  return Boolean(transaction.category && categoryLookup.value.get(transaction.category)?.budget_treatment === 'tracking_only')
}

function projectionPeriodLabel(index: number) {
  return index === 0 ? 'Act.' : `+${index}`
}

function projectionPaymentCountLabel(count: number) {
  if (count === 1) return '1 pago a meses'
  return `${count} pagos a meses`
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

function categoryStyle(color?: string | null) {
  return color ? ({ '--category-color': color } as Record<string, string>) : undefined
}

function recurringCommitmentCategory(row: { expense: RecurringExpense; charge?: ExpectedCharge }) {
  return row.charge?.category ?? categoryLookup.value.get(row.expense.category) ?? null
}

function recurringCommitmentCategoryLabel(row: { expense: RecurringExpense; charge?: ExpectedCharge }) {
  const suffix = recurringCommitmentCategory(row)?.budget_treatment === 'tracking_only' ? ' · fuera de presupuesto' : ''
  if (row.expense.member_name) return `${row.expense.category_name} · ${row.expense.member_name}${suffix}`
  return `${row.expense.category_name}${suffix}`
}

function installmentCommitmentCategoryLabel(plan: InstallmentProjectionPlan) {
  const suffix = plan.category.budget_treatment === 'tracking_only' ? ' · fuera de presupuesto' : ''
  if (plan.member) return `${plan.category.name} · ${plan.member.name}${suffix}`
  return `${plan.category.name}${suffix}`
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
          Correo
          <input v-model="claimForm.email" type="email" autocomplete="email" placeholder="papa@example.com" required />
        </label>
        <div class="field-row auth-password-row">
          <label>
            Contraseña
            <input v-model="claimForm.password" type="password" autocomplete="new-password" required />
          </label>
          <label>
            Confirmar contraseña
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
            Contraseña
            <input v-model="acceptInviteForm.password" type="password" autocomplete="new-password" required />
          </label>
          <label>
            Confirmar contraseña
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
          Correo
          <input v-model="loginForm.email" type="email" autocomplete="email" placeholder="papa@example.com" required />
        </label>
        <label>
          Contraseña
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
          <span>{{ selectedCategory.budget_behavior === 'carryover' ? 'Disponible libre' : 'Disponible' }}</span>
          <strong>{{ money(selectedCategory.available_cents, settings.currency) }}</strong>
        </div>
        <div class="hero-metrics">
          <article v-if="selectedCategory.budget_behavior === 'carryover'">
            <span>Saldo real</span>
            <b>{{ money(selectedCategory.real_available_cents, settings.currency) }}</b>
          </article>
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
          <article v-if="selectedCategory.budget_behavior === 'monthly_reset'">
            <span>Excedentes</span>
            <b>{{ selectedCategory.overspend_count }}</b>
          </article>
        </div>
        <div
          class="meter hero-meter category-meter"
          :class="{
            'is-over-budget': categoryRealOverspent(selectedCategory),
            'projected-over-budget': categoryProjectedOverspent(selectedCategory),
          }"
          :style="{ '--category-fill-color': categoryRealOverspent(selectedCategory) ? '#d64309' : selectedCategory.color }"
        >
          <span class="meter-segment spent" :style="{ width: `${categorySpentPercent(selectedCategory)}%` }"></span>
          <span
            v-if="selectedCategory.expected_cents"
            class="meter-segment committed"
            :style="{ left: `${categorySpentPercent(selectedCategory)}%`, width: `${categoryCommittedPercent(selectedCategory)}%` }"
          ></span>
          <span v-if="selectedCategory.is_overspent" class="meter-overflow"></span>
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
      <section class="plan-top-section" aria-label="Presupuesto de casa">
        <header class="plan-top-header">
          <h1>Presupuesto de casa</h1>
          <p>{{ activePeriodLabel }}</p>
        </header>

        <div
          class="plan-cycle-controls"
          aria-label="Seleccionar ciclo del presupuesto"
          @focusout="closeCycleMenuOnBlur"
          @keydown.esc="cycleMenuOpen = false"
        >
          <button
            class="cycle-step-button"
            type="button"
            aria-label="Ciclo anterior"
            :disabled="!canShiftToPreviousCycle"
            @click="shiftBudgetCycle(-1)"
          >
            <svg viewBox="0 0 24 24"><path d="M15 6l-6 6 6 6" /></svg>
          </button>
          <div class="cycle-picker">
            <button
              class="cycle-picker-trigger"
              type="button"
              aria-haspopup="listbox"
              aria-controls="budget-cycle-list"
              :aria-expanded="cycleMenuOpen"
              @click="cycleMenuOpen = !cycleMenuOpen"
            >
              <span>
                <small>{{ activeBudgetCycleOption ? cycleRelativeLabel(activeBudgetCycleOption) : 'Ciclo actual' }}</small>
                <strong>{{ activePeriodLabel }}</strong>
              </span>
              <svg class="cycle-trigger-chevron" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>
            <div v-if="cycleMenuOpen" id="budget-cycle-list" class="cycle-picker-menu" role="listbox" aria-label="Ciclos disponibles">
              <button
                v-for="cycle in budgetCycleMenuOptions"
                :key="cycle.value"
                class="cycle-option"
                :class="{ active: cycle.value === activeBudgetPeriod.start }"
                type="button"
                role="option"
                :aria-selected="cycle.value === activeBudgetPeriod.start"
                @click="selectBudgetCycle(cycle.value)"
              >
                <span>
                  <small>{{ cycleRelativeLabel(cycle) }}</small>
                  <strong>{{ formatPeriodLabel(cycle.start, cycle.end) }}</strong>
                </span>
                <b v-if="cycle.value === activeBudgetPeriod.start">Activo</b>
              </button>
            </div>
          </div>
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
            :class="{
              danger: categoryRealOverspent(item),
              'projected-danger': categoryProjectedOverspent(item),
            }"
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
                  <p v-if="item.budget_behavior === 'carryover'">
                    Saldo {{ money(item.real_available_cents, settings.currency) }} · libre {{ money(item.available_cents, settings.currency) }}
                  </p>
                  <p v-else>
                    {{ item.spent_cents ? money(item.spent_cents, settings.currency) : '$0.00' }} de {{ money(item.budget_cents, settings.currency) }}
                  </p>
                  <small v-if="item.expected_cents" class="category-commitment-line">
                    Comprometido {{ money(item.expected_cents, settings.currency) }}
                  </small>
                  <small v-if="item.budget_behavior === 'monthly_reset' && item.overspend_count">
                    {{ item.overspend_count }} excedentes · {{ money(item.overspend_total_cents, settings.currency) }}
                  </small>
                </div>
                <span
                  class="status-pill"
                  :class="{ warning: categoryRealOverspent(item), projected: categoryProjectedOverspent(item) }"
                >
                  {{ categoryStatusLabel(item) }}
                </span>
              </div>
              <div
                class="meter category-meter"
                :class="{
                  'is-over-budget': categoryRealOverspent(item),
                  'projected-over-budget': categoryProjectedOverspent(item),
                }"
                :style="{ '--category-fill-color': categoryRealOverspent(item) ? '#d64309' : item.color }"
                aria-hidden="true"
              >
                <span class="meter-segment spent" :style="{ width: `${categorySpentPercent(item)}%` }"></span>
                <span
                  v-if="item.expected_cents"
                  class="meter-segment committed"
                  :style="{ left: `${categorySpentPercent(item)}%`, width: `${categoryCommittedPercent(item)}%` }"
                ></span>
                <span v-if="item.is_overspent" class="meter-overflow"></span>
              </div>
              <footer>
                <span>{{ item.member?.name ?? 'Casa' }}</span>
                <strong>{{ money(item.available_cents, settings.currency) }}</strong>
              </footer>
            </button>
          </article>
        </div>
      </section>

      <section v-if="summary" class="plan-overview" aria-label="Resumen de casa">
        <div class="plan-balance">
          <span>Presupuesto de casa</span>
          <strong :class="{ negative: summary.totals.available_cents < 0 }">
            {{ money(summary.totals.available_cents, settings.currency) }}
          </strong>
          <p>{{ planSummaryCopy }}</p>
        </div>
        <dl class="home-totals">
          <div>
            <dt>Presupuesto del periodo</dt>
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

      <section v-if="offBudgetSummary && (offBudgetTotal > 0 || trackingOnlyCategories.length)" class="off-budget-panel" aria-label="Registros fuera de presupuesto">
        <div class="section-title-row">
          <div>
            <h2>Fuera de presupuesto</h2>
          </div>
          <span>{{ money(offBudgetTotal, settings.currency) }}</span>
        </div>
        <div v-if="offBudgetSummary.categories.length" class="off-budget-list">
          <article
            v-for="item in offBudgetSummary.categories"
            :key="item.category_id"
            class="off-budget-row"
            :style="{ '--category-color': item.color }"
          >
            <span class="category-icon" :style="{ '--category-color': item.color }">
              <component :is="categoryIconComponent(item.icon)" aria-hidden="true" />
            </span>
            <div>
              <b>{{ item.category_name }}</b>
              <small>
                Registrado {{ money(item.spent_cents, settings.currency) }} · por venir {{ money(item.expected_cents, settings.currency) }}
              </small>
            </div>
            <strong>{{ money(item.total_cents, settings.currency) }}</strong>
          </article>
        </div>
        <p v-else class="empty-line">Sin registros fuera de presupuesto en este periodo.</p>
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
        <p v-else>No hay categorías rebasadas ni pagos urgentes en este ciclo.</p>
      </section>

      <section v-if="summary" class="spending-chart-panel" aria-labelledby="spending-chart-title">
        <div class="spending-chart-copy">
          <span>Distribución del gasto</span>
          <h2 id="spending-chart-title">Cómo se está yendo el dinero</h2>
          <p v-if="spendingChartTotal">
            {{ spendingChartLeadSegment?.label }} concentra {{ spendingChartLeadSegment?.percent.toFixed(0) }}% del gasto del periodo.
          </p>
          <p v-else>Registra gastos para ver la proporción real por categoría en este ciclo.</p>
        </div>

        <div class="spending-chart-layout">
          <figure class="spending-donut" :style="spendingChartStyle" role="img" :aria-label="`Gasto total ${money(spendingChartTotal, settings.currency)}`">
            <span>
              <small>Gastado</small>
              <strong>{{ money(spendingChartTotal, settings.currency) }}</strong>
            </span>
          </figure>

          <ol v-if="spendingChartSegments.length" class="spending-legend" aria-label="Gasto por categoría">
            <li
              v-for="segment in spendingChartSegments"
              :key="segment.key"
              :style="{ '--category-color': segment.color }"
            >
              <button type="button" @click="selectedCategoryId = segment.category_ids[0]; scrollToTop()">
                <span class="legend-icon" aria-hidden="true">
                  <component :is="categoryIconComponent(segment.icon)" />
                </span>
                <span class="legend-swatch" aria-hidden="true"></span>
                <b>{{ segment.label }}</b>
                <span class="legend-percent">
                  <em>{{ segment.percent.toFixed(0) }}%</em>
                  <i :style="{ '--legend-percent': `${Math.max(6, segment.percent)}%` }" aria-hidden="true"></i>
                </span>
                <strong>{{ money(segment.amount_cents, settings.currency) }}</strong>
                <ChevronRight class="legend-chevron" aria-hidden="true" />
              </button>
            </li>
          </ol>
          <p v-else class="spending-empty">Todavía no hay gastos en este periodo.</p>
        </div>
      </section>
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
          <p>{{ expensesTab === 'capture' ? 'Guarda el gasto en pocos pasos. Usa los accesos rápidos si coincide con lo de siempre.' : 'Revisa los gastos del periodo y confirma que quedaron en la cuenta correcta.' }}</p>
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
              <span>{{ category.name }}</span>
              <small v-if="category.budget_treatment === 'tracking_only'" class="choice-note">Fuera de presupuesto</small>
            </button>
            <p v-if="!filteredExpenseCategories.length" class="empty-line">No encontramos esa categoría.</p>
          </div>
        </section>

        <section class="choice-block">
          <div class="section-title-row">
            <h2>Cuenta</h2>
            <span>{{ expenseIsTrackingOnly ? 'No aplica' : expenseForm.account ? 'Lista' : 'Desde dónde se pagó' }}</span>
          </div>

          <p v-if="expenseIsTrackingOnly" class="tracking-only-note">
            Este registro no afecta presupuesto ni saldos de cuentas.
          </p>

          <label v-if="!expenseIsTrackingOnly" class="search-field account-search-field">
            Buscar cuenta
            <input v-model="expenseAccountSearch" type="search" placeholder="BBVA, caja, tarjeta" autocomplete="off" />
          </label>

          <div v-if="!expenseIsTrackingOnly" class="choice-chips account-card-list" role="list">
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
          <div class="field-row expense-meta-row">
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
          <div>
            <h2>Gastos del periodo</h2>
            <small>{{ activePeriodLabel }}</small>
          </div>
          <span>{{ expenseFeedSummaryLabel }}</span>
        </div>
        <div class="feed-filter-row">
          <label>
            Categoría
            <select v-model="expenseFeedCategoryId" :disabled="!expenseFeedCategoryOptions.length">
              <option value="">Todas las categorías</option>
              <option v-for="category in expenseFeedCategoryOptions" :key="category.id" :value="String(category.id)">
                {{ category.label }}
              </option>
            </select>
          </label>
          <label>
            Método de pago
            <select v-model="expenseFeedPaymentMethod" :disabled="!expenseFeedAccountTypeOptions.length && !expenseFeedAccountOptions.length && !hasUnaccountedPeriodExpenses">
              <option value="">Todos los métodos</option>
              <optgroup v-if="expenseFeedAccountTypeOptions.length" label="Tipo de pago">
                <option v-for="option in expenseFeedAccountTypeOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </optgroup>
              <optgroup v-if="expenseFeedAccountOptions.length || hasUnaccountedPeriodExpenses" label="Cuenta o tarjeta">
                <option v-if="hasUnaccountedPeriodExpenses" value="none">Sin cuenta</option>
                <option v-for="option in expenseFeedAccountOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </optgroup>
            </select>
          </label>
          <button
            v-if="expenseFeedCategoryId || expenseFeedPaymentMethod"
            class="square-action feed-filter-clear"
            type="button"
            aria-label="Limpiar filtros de movimientos"
            title="Limpiar filtros"
            @click="clearExpenseFeedFilters"
          >
            <X :size="16" :stroke-width="2.4" />
          </button>
        </div>
        <div
          v-if="expenseFeedHasActiveFilters && filteredPeriodExpenses.length"
          class="expense-review-toolbar"
          :class="{ active: expenseReviewMode }"
        >
          <button
            class="secondary expense-review-toggle"
            type="button"
            :aria-pressed="expenseReviewMode"
            @click="toggleExpenseReviewMode"
          >
            <ListChecks :size="17" :stroke-width="2.4" />
            {{ expenseReviewMode ? 'Cerrar revisión' : 'Revisión' }}
          </button>
          <span v-if="expenseReviewMode" class="expense-review-count">{{ expenseReviewProgressLabel }}</span>
          <button
            v-if="expenseReviewMode && reviewedFilteredExpenseCount"
            class="square-action expense-review-reset"
            type="button"
            aria-label="Limpiar checks de revisión"
            title="Limpiar checks"
            @click="clearReviewedExpenses"
          >
            <X :size="16" :stroke-width="2.4" />
          </button>
        </div>
        <article
          v-for="transaction in filteredPeriodExpenses"
          :key="transaction.id"
          class="feed-row accent-left"
          :class="{ editing: editingTransactionId === transaction.id, reviewed: transactionIsReviewed(transaction) }"
        >
          <template v-if="editingTransactionId !== transaction.id">
            <div>
              <b>{{ transaction.merchant || transaction.category_name || transaction.transaction_type }}</b>
              <span>
                {{ transaction.category_name ?? transaction.transaction_type }} ·
                {{ transaction.account_name ?? 'sin cuenta' }} ·
                {{ transaction.created_by_username ?? 'sin usuario' }} · {{ transaction.date }}
              </span>
              <small v-if="transactionIsTrackingOnly(transaction)" class="tracking-inline">Fuera de presupuesto</small>
            </div>
            <div class="feed-row-actions">
              <button
                v-if="expenseReviewMode"
                class="square-action expense-review-check"
                :class="{ checked: transactionIsReviewed(transaction) }"
                type="button"
                :aria-pressed="transactionIsReviewed(transaction)"
                :aria-label="transactionIsReviewed(transaction) ? `Marcar ${transactionLabel(transaction)} como pendiente` : `Marcar ${transactionLabel(transaction)} como revisado`"
                :title="transactionIsReviewed(transaction) ? 'Marcar como pendiente' : 'Marcar como revisado'"
                @click="toggleExpenseReviewed(transaction.id)"
              >
                <Check :size="16" :stroke-width="2.6" />
              </button>
              <strong>-{{ money(transaction.amount_cents, settings.currency) }}</strong>
              <button
                class="square-action edit-action"
                type="button"
                :aria-label="`Editar ${transaction.merchant || transaction.category_name || 'gasto'}`"
                :title="`Editar ${transaction.merchant || transaction.category_name || 'gasto'}`"
                @click="openTransactionEdit(transaction)"
              >
                <Pencil :size="16" :stroke-width="2.4" />
              </button>
            </div>
          </template>
          <form
            v-else
            class="transaction-edit-form form-stack inline-edit-form"
            @submit.prevent="saveTransactionEdit(transaction)"
          >
            <div class="field-row featured-fields">
              <label>Comercio o concepto<input v-model="transactionEditForm.merchant" required /></label>
              <label>Monto<input v-model="transactionEditForm.amount" inputmode="decimal" required /></label>
            </div>
            <div class="field-row expense-meta-row">
              <label>Fecha<input v-model="transactionEditForm.date" type="date" required /></label>
              <label>
                Categoría
                <select v-model="transactionEditForm.category" required>
                  <option value="" disabled>Elige una categoría</option>
                  <option v-for="category in categories" :key="category.id" :value="String(category.id)">
                    {{ category.name }}{{ category.budget_treatment === 'tracking_only' ? ' · fuera de presupuesto' : '' }}
                  </option>
                </select>
              </label>
            </div>
            <div class="field-row expense-meta-row">
              <label v-if="!transactionEditIsTrackingOnly">
                Cuenta
                <select v-model="transactionEditForm.account" required>
                  <option value="" disabled>Elige una cuenta</option>
                  <option v-for="account in accounts" :key="account.id" :value="String(account.id)">
                    {{ account.name }}
                  </option>
                </select>
              </label>
              <p v-else class="tracking-only-note">No afecta saldos de cuentas.</p>
              <label>Nota opcional<textarea v-model="transactionEditForm.note" rows="2"></textarea></label>
            </div>
            <div class="action-row">
              <button
                class="primary expense-primary"
                type="submit"
                :disabled="actionBusy === `edit-transaction-${transaction.id}`"
              >
                {{ actionBusy === `edit-transaction-${transaction.id}` ? 'Guardando...' : 'Guardar cambios' }}
              </button>
              <button class="secondary" type="button" @click="cancelTransactionEdit">
                Cancelar
              </button>
            </div>
            <div class="transaction-danger-zone">
              <button
                v-if="!isConfirmingTransactionDelete(transaction.id)"
                class="danger-action"
                type="button"
                @click="startTransactionDelete(transaction)"
              >
                <Trash2 :size="15" :stroke-width="2.4" />
                Eliminar gasto registrado
              </button>
              <div
                v-else
                class="transaction-delete-confirm inline-confirm"
                role="group"
                :aria-label="`Confirmar eliminación de ${transactionLabel(transaction)}`"
              >
                <span>
                  Eliminar {{ transactionLabel(transaction) }} de {{ transaction.date }} por
                  {{ money(transaction.amount_cents, settings.currency) }}. Se recalcula el presupuesto y la cuenta.
                </span>
                <button
                  class="danger-action"
                  type="button"
                  :disabled="actionBusy === `delete-transaction-${transaction.id}`"
                  @click="deleteTransaction(transaction)"
                >
                  {{ actionBusy === `delete-transaction-${transaction.id}` ? 'Eliminando...' : 'Sí, eliminar' }}
                </button>
                <button class="secondary" type="button" @click="cancelTransactionDelete">Cancelar</button>
              </div>
            </div>
          </form>
        </article>
        <p v-if="!filteredPeriodExpenses.length" class="empty-line">{{ expenseFeedEmptyMessage }}</p>
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
            <span>Pagos</span>
          <h1>Nuevo pago planeado</h1>
          </div>
        </header>

        <div class="segmented purple">
          <button :class="{ active: commitmentKind === 'subscription' }" type="button" @click="commitmentKind = 'subscription'">Pago mensual</button>
          <button :class="{ active: commitmentKind === 'msi' }" type="button" @click="commitmentKind = 'msi'">Compra a meses</button>
        </div>

        <form class="commitment-form form-stack" @submit.prevent="submitCurrentCommitment">
          <section class="choice-block commitment-choice-block">
            <div class="section-title-row">
              <h2>Categoría</h2>
              <span>{{ commitmentCategoryValue() ? 'Lista' : 'Elige una' }}</span>
            </div>

            <label class="search-field category-search-field">
              Buscar categoría
              <input v-model="commitmentCategorySearch" type="search" placeholder="Comida, gas, internet" autocomplete="off" />
            </label>

            <div class="choice-chips category-card-list" role="list">
              <button
                v-for="category in filteredCommitmentCategories"
                :key="category.id"
                type="button"
                :class="{ active: String(category.id) === commitmentCategoryValue() }"
                :style="{ '--category-color': category.color }"
                @click="chooseCommitmentCategory(category.id)"
              >
                <span class="category-icon" :style="{ '--category-color': category.color }">
                  <component :is="categoryIconComponent(category.icon)" aria-hidden="true" />
                </span>
                <span>{{ category.name }}</span>
                <small v-if="category.budget_treatment === 'tracking_only'" class="choice-note">Fuera de presupuesto</small>
              </button>
              <p v-if="!filteredCommitmentCategories.length" class="empty-line">No encontramos esa categoría.</p>
            </div>
          </section>

          <section class="choice-block commitment-choice-block">
            <div class="section-title-row">
              <h2>Cuenta</h2>
              <span>{{ commitmentIsTrackingOnly ? 'No aplica' : commitmentAccountStatusLabel() }}</span>
            </div>

            <p v-if="commitmentIsTrackingOnly" class="tracking-only-note">
              Este compromiso queda aparte y no afecta la distribución del gasto.
            </p>

            <label v-if="!commitmentIsTrackingOnly" class="search-field account-search-field">
              Buscar cuenta
              <input v-model="commitmentAccountSearch" type="search" placeholder="BBVA, caja, tarjeta" autocomplete="off" />
            </label>

            <div v-if="!commitmentIsTrackingOnly" class="choice-chips account-card-list" role="list">
              <button
                class="account-choice-card no-account-choice"
                type="button"
                :class="{ active: !commitmentAccountValue() }"
                :style="{ '--account-color': 'var(--commitments-accent)' }"
                @click="chooseCommitmentAccount(null)"
              >
                <span class="account-color-dot" aria-hidden="true"></span>
                Sin cuenta
              </button>
              <button
                v-for="account in filteredCommitmentAccounts"
                :key="account.id"
                class="account-choice-card"
                type="button"
                :class="{ active: String(account.id) === commitmentAccountValue() }"
                :style="{ '--account-color': account.color }"
                @click="chooseCommitmentAccount(account.id)"
              >
                <span class="account-color-dot" aria-hidden="true"></span>
                {{ account.name }}
              </button>
              <p v-if="!filteredCommitmentAccounts.length" class="empty-line">No encontramos esa cuenta.</p>
            </div>
          </section>

          <section v-if="commitmentKind === 'subscription'" class="purple-panel commitment-entry-panel">
            <div class="section-title-row">
              <h2>Pago mensual</h2>
              <span>Indefinida</span>
            </div>
            <p>Solo indica el día de pago. Se repite cada mes hasta que lo omitas o lo desactives.</p>
            <div class="field-row commitment-input-row">
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
            <div class="field-row commitment-date-row">
              <label>Día de pago<input v-model.number="recurringForm.charge_day" type="number" min="1" max="28" /></label>
              <label>Inicio<input v-model="recurringForm.start_date" type="date" required /></label>
              <label>Fin opcional<input v-model="recurringForm.end_date" type="date" /></label>
            </div>
            <label class="switch-row auto-charge-switch">
              <input v-model="recurringForm.auto_charge" type="checkbox" role="switch" />
              <span class="switch-track" aria-hidden="true"></span>
              <span>
                <b>Cargar automáticamente</b>
                <small>{{ commitmentIsTrackingOnly ? 'Cuando llegue el día, se registra sin afectar cuentas.' : 'Cuando llegue el día de pago, se registra el gasto con la cuenta configurada.' }}</small>
              </span>
            </label>
            <div class="preview-box">
              <b>Cómo se verá</b>
              <span>Primer pago {{ recurringForm.start_date }}</span>
              <span>{{ recurringForm.auto_charge ? 'Se registrará automáticamente' : 'Quedará como pago pendiente' }}</span>
              <span>Duración indefinida</span>
            </div>
          </section>

          <section v-else class="purple-panel commitment-entry-panel">
            <div class="section-title-row">
              <h2>Compra a meses</h2>
              <span>Plazo definido</span>
            </div>
            <p>Indica la fecha del primer pago y cuántos meses dura la compra. Burn Rate calcula el último pago.</p>
            <div class="field-row commitment-input-row">
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
            <div class="field-row commitment-date-row">
              <label>Primer pago<input v-model="installmentForm.start_date" type="date" required /></label>
              <label>Meses<input v-model="installmentForm.months_count" type="number" inputmode="numeric" min="1" step="1" required /></label>
            </div>
            <label class="switch-row rounding-switch">
              <input v-model="installmentForm.round_up_monthly_payment" type="checkbox" role="switch" />
              <span class="switch-track" aria-hidden="true"></span>
              <span>
                <b>Redondear pago requerido</b>
                <small>Usa el siguiente peso completo en cada mensualidad y ajusta el último pago al remanente real.</small>
              </span>
            </label>
            <div class="preview-box">
              <b>Cómo se verá</b>
              <span>Primer pago {{ installmentForm.start_date }}</span>
              <span>Último pago {{ installmentCalculatedEndDate || 'por calcular' }}</span>
              <span>{{ installmentForm.months_count || 0 }} mensualidades</span>
              <span v-if="installmentForm.round_up_monthly_payment">Pago requerido redondeado al siguiente peso</span>
            </div>
          </section>

          <div class="action-row">
            <button class="secondary purple-secondary" type="button" @click="closeCommitmentForm">Cancelar</button>
            <button
              class="primary purple-primary"
              type="submit"
              :disabled="actionBusy === (commitmentKind === 'subscription' ? 'recurring' : 'installment')"
            >
              {{
                actionBusy === (commitmentKind === 'subscription' ? 'recurring' : 'installment')
                  ? 'Guardando...'
                  : commitmentKind === 'subscription'
                    ? 'Guardar pago'
                    : 'Guardar compra'
              }}
            </button>
          </div>
        </form>
      </template>

      <template v-else>
        <header class="mobile-header commitments-header">
          <div>
            <span>Burn Rate</span>
            <h1>Pagos del mes</h1>
            <small class="commitment-inline-summary">
              <b>{{ money(currentCommitmentTotal, settings.currency) }}</b>
              <em>{{ activeRecurringExpenses.length }} mensuales · {{ projectedInstallmentPlans.length }} a meses</em>
            </small>
          </div>
        </header>

        <div class="commitment-total-grid">
          <article class="commitment-total-card">
            <span>Suscripciones activas</span>
            <strong>{{ money(activeRecurringTotal, settings.currency) }}</strong>
            <small>{{ activeRecurringExpenses.length }} mensuales registrados</small>
          </article>
          <article class="commitment-total-card">
            <span>A meses este periodo</span>
            <strong>{{ money(currentInstallmentTotal, settings.currency) }}</strong>
            <small>{{ projectedInstallmentPlans.length }} compras a meses activas</small>
          </article>
        </div>

        <section v-if="creditCardPaymentSummary" class="credit-card-payment-panel" aria-label="Pago para no generar intereses">
          <div class="credit-card-payment-header">
            <div>
              <span>Pago para no generar intereses</span>
              <small>Compras registradas + compras a meses del ciclo</small>
            </div>
            <strong>{{ money(creditCardInterestFreeTotal, settings.currency) }}</strong>
          </div>
          <div v-if="creditCardPaymentCards.length" class="credit-card-payment-list">
            <article
              v-for="card in creditCardPaymentCards"
              :key="card.account_id"
              class="credit-card-payment-row"
              :style="{ '--account-color': card.account_color }"
            >
              <div>
                <b>{{ card.account_name }}</b>
                <span>{{ money(card.interest_free_payment_cents, settings.currency) }}</span>
              </div>
              <dl>
                <div>
                  <dt>Compras del ciclo</dt>
                  <dd>{{ money(card.cycle_purchase_cents, settings.currency) }}</dd>
                </div>
                <div>
                  <dt>A meses del ciclo</dt>
                  <dd>{{ money(card.installment_cents, settings.currency) }}</dd>
                </div>
              </dl>
            </article>
          </div>
          <p v-else class="empty-line">No hay tarjetas de crédito activas.</p>
        </section>

        <div class="segmented">
          <button :class="{ active: commitmentTab === 'subscriptions' }" type="button" @click="commitmentTab = 'subscriptions'">Mensuales</button>
          <button :class="{ active: commitmentTab === 'msi' }" type="button" @click="commitmentTab = 'msi'">A meses</button>
        </div>

        <section v-if="commitmentTab === 'subscriptions'" class="commitment-section">
          <div class="section-title-row">
            <h2>Pagos mensuales</h2>
            <button class="secondary purple-secondary section-title-action" type="button" @click="openCommitmentForm('subscription')">
              Nuevo pago mensual
            </button>
          </div>
          <article
            v-for="row in recurringCommitmentRows"
            :key="row.expense.id"
            class="expected-row"
            :class="{ editing: isEditingCommitment('recurring', row.expense.id) }"
            :style="categoryStyle(recurringCommitmentCategory(row)?.color)"
          >
            <div>
              <b>{{ row.expense.name }}</b>
              <span v-if="secondaryCommitmentLabel(row.expense.name, row.expense.merchant)">
                {{ secondaryCommitmentLabel(row.expense.name, row.expense.merchant) }}
              </span>
              <span class="commitment-category-pill">
                <span class="category-icon" :style="categoryStyle(recurringCommitmentCategory(row)?.color)">
                  <component :is="categoryIconComponent(recurringCommitmentCategory(row)?.icon)" aria-hidden="true" />
                </span>
                <span class="category-pill-copy">
                  <em>Categoría</em>
                  <b>{{ recurringCommitmentCategoryLabel(row) }}</b>
                </span>
              </span>
              <small>
                {{ row.expense.auto_charge ? `Cargo automático día ${row.expense.charge_day}` : `Recordatorio día ${row.expense.charge_day}` }}
              </small>
              <small v-if="!row.charge">Sin pago pendiente en este periodo</small>
            </div>
            <strong>{{ money(row.expense.amount_cents, settings.currency) }}</strong>
            <template v-if="!isEditingCommitment('recurring', row.expense.id)">
              <button
                v-if="row.charge"
                class="primary purple-primary"
                type="button"
                :disabled="actionBusy === `charge-${row.charge.key}`"
                @click="confirmCharge(row.charge)"
              >
                Pagado
              </button>
              <button
                v-if="row.charge"
                class="secondary"
                type="button"
                :disabled="actionBusy === `dismiss-${row.charge.key}`"
                @click="dismissCharge(row.charge)"
              >
                Omitir
              </button>
            </template>
            <button
              class="square-action compact-icon-action"
              type="button"
              :aria-label="`Editar ${row.expense.name}`"
              :title="`Editar ${row.expense.name}`"
              @click="openCommitmentEdit('recurring', row.expense)"
            >
              <Pencil :size="16" :stroke-width="2.4" />
            </button>
            <form
              v-if="isEditingCommitment('recurring', row.expense.id)"
              class="commitment-edit-panel form-stack"
              @submit.prevent="saveRecurringExpenseEdit(row.expense)"
            >
              <div class="field-row">
                <label>Nombre<input v-model="commitmentEditForm.name" required /></label>
                <label>Comercio<input v-model="commitmentEditForm.merchant" required /></label>
              </div>
              <div class="field-row commitment-date-row">
                <label>Día de pago<input v-model.number="commitmentEditForm.charge_day" type="number" min="1" max="28" /></label>
                <label>
                  Cuenta
                  <select v-model="commitmentEditForm.account">
                    <option value="">Sin cuenta</option>
                    <option v-for="account in activeAccounts" :key="account.id" :value="String(account.id)">
                      {{ account.name }}
                    </option>
                  </select>
                </label>
              </div>
              <label class="switch-row auto-charge-switch">
                <input v-model="commitmentEditForm.auto_charge" type="checkbox" role="switch" />
                <span class="switch-track" aria-hidden="true"></span>
                <span>
                  <b>Cargar automáticamente</b>
                  <small>Registra el gasto real al llegar el día configurado.</small>
                </span>
              </label>
              <div class="commitment-readonly">
                <span>Monto {{ money(row.expense.amount_cents, settings.currency) }}</span>
                <span>Inicio {{ row.expense.start_date }}</span>
              </div>
              <div class="commitment-edit-actions">
                <button class="primary purple-primary" type="submit" :disabled="actionBusy === `edit-recurring-${row.expense.id}`">
                  {{ actionBusy === `edit-recurring-${row.expense.id}` ? 'Guardando...' : 'Guardar' }}
                </button>
                <button class="secondary" type="button" @click="closeCommitmentEdit">Cancelar</button>
              </div>
              <div v-if="canManageSettings" class="commitment-danger-zone">
                <button
                  v-if="!isConfirmingCommitmentDelete('recurring', row.expense.id)"
                  class="danger-action"
                  type="button"
                  @click="startCommitmentDelete('recurring', row.expense.id)"
                >
                  Eliminar pago mensual
                </button>
                <div v-else class="inline-confirm">
                  <span>Confirmar eliminación definitiva</span>
                  <button
                    class="danger-action"
                    type="button"
                    :disabled="actionBusy === `delete-recurring-${row.expense.id}`"
                    @click="deleteRecurringExpense(row.expense)"
                  >
                    {{ actionBusy === `delete-recurring-${row.expense.id}` ? 'Eliminando...' : 'Sí, eliminar' }}
                  </button>
                  <button class="secondary" type="button" @click="cancelCommitmentDelete">Cancelar</button>
                </div>
              </div>
            </form>
          </article>
          <p v-if="!recurringCommitmentRows.length" class="empty-line">No hay pagos mensuales activos.</p>
        </section>

        <section v-else class="commitment-section">
          <div class="section-title-row">
            <h2>Compras a meses</h2>
            <span>{{ money(currentInstallmentTotal, settings.currency) }}</span>
          </div>
          <article
            v-for="plan in projectedInstallmentPlans"
            :key="plan.id"
            class="installment-row"
            :class="{ editing: isEditingCommitment('installment', plan.id) }"
            :style="categoryStyle(plan.category.color)"
          >
            <div class="installment-main">
              <div>
                <b>{{ plan.name }}</b>
                <span v-if="secondaryCommitmentLabel(plan.name, plan.merchant)">
                  {{ secondaryCommitmentLabel(plan.name, plan.merchant) }}
                </span>
                <span class="commitment-category-pill">
                  <span class="category-icon" :style="categoryStyle(plan.category.color)">
                    <component :is="categoryIconComponent(plan.category.icon)" aria-hidden="true" />
                  </span>
                  <span class="category-pill-copy">
                    <em>Categoría</em>
                    <b>{{ installmentCommitmentCategoryLabel(plan) }}</b>
                  </span>
                </span>
              </div>
              <strong>{{ money(plan.current_amount_cents ?? 0, settings.currency) }}</strong>
              <button
                class="square-action compact-icon-action"
                type="button"
                :aria-label="`Editar ${plan.name}`"
                :title="`Editar ${plan.name}`"
                @click="openCommitmentEdit('installment', plan)"
              >
                <Pencil :size="16" :stroke-width="2.4" />
              </button>
            </div>
            <form
              v-if="isEditingCommitment('installment', plan.id)"
              class="commitment-edit-panel form-stack"
              @submit.prevent="saveInstallmentPlanEdit(plan)"
            >
              <div class="field-row">
                <label>Nombre<input v-model="commitmentEditForm.name" required /></label>
                <label>Comercio<input v-model="commitmentEditForm.merchant" required /></label>
              </div>
              <label>
                Categoría
                <select v-model="commitmentEditForm.category" required>
                  <option value="">Categoría</option>
                  <option v-for="category in activeCategories" :key="category.id" :value="category.id">
                    {{ category.name }}{{ category.member_name ? ` - ${category.member_name}` : '' }}{{ category.budget_treatment === 'tracking_only' ? ' · fuera de presupuesto' : '' }}
                  </option>
                </select>
              </label>
              <div class="commitment-readonly">
                <span>Total {{ money(plan.total_amount_cents, settings.currency) }}</span>
                <span>Inicio {{ installmentPlanDetail(plan.id)?.start_date ?? 'No disponible' }}</span>
              </div>
              <div class="commitment-edit-actions">
                <button class="primary purple-primary" type="submit" :disabled="actionBusy === `edit-installment-${plan.id}`">
                  {{ actionBusy === `edit-installment-${plan.id}` ? 'Guardando...' : 'Guardar' }}
                </button>
                <button class="secondary" type="button" @click="closeCommitmentEdit">Cancelar</button>
              </div>
              <div v-if="canManageSettings" class="commitment-danger-zone">
                <button
                  v-if="!isConfirmingCommitmentDelete('installment', plan.id)"
                  class="danger-action"
                  type="button"
                  @click="startCommitmentDelete('installment', plan.id)"
                >
                  Eliminar compra a meses
                </button>
                <div v-else class="inline-confirm">
                  <span>Confirmar eliminación definitiva</span>
                  <button
                    class="danger-action"
                    type="button"
                    :disabled="actionBusy === `delete-installment-${plan.id}`"
                    @click="deleteInstallmentPlan(plan)"
                  >
                    {{ actionBusy === `delete-installment-${plan.id}` ? 'Eliminando...' : 'Sí, eliminar' }}
                  </button>
                  <button class="secondary" type="button" @click="cancelCommitmentDelete">Cancelar</button>
                </div>
              </div>
            </form>
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

        <section v-if="commitmentTab === 'msi'" class="projection-card">
          <div class="projection-header">
            <div>
              <h2>Pagos a meses registrados</h2>
              <span>Total de compras a meses activas en esta proyección</span>
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
                <span>{{ period.plans.length ? projectionPaymentCountLabel(period.plans.length) : 'Sin pagos a meses' }}</span>
                <b v-if="projectionSettledPlans(period).length">{{ projectionSettledLabel(period) }}</b>
              </div>
            </article>
          </div>
        </section>
      </template>
    </section>

    <section
      v-if="view === 'benefits'"
      class="screen benefits-screen"
      :inert="iconGalleryOpen || undefined"
      :aria-hidden="iconGalleryOpen ? 'true' : undefined"
    >
      <header class="mobile-header benefits-header">
        <div>
          <span>Burn Rate</span>
          <h1>Beneficios</h1>
          <p>Qué tarjeta o cuenta conviene usar según el tipo de gasto.</p>
        </div>
      </header>

      <section class="benefits-intro" aria-label="Resumen de beneficios">
        <div>
          <span>Revisado: {{ benefitsLastChecked }}</span>
          <h2>Elige por gasto, no por banco</h2>
          <p>
            Esta primera versión compara los beneficios publicados para tus tarjetas y cuenta. Úsalo como guía rápida antes de capturar un gasto.
          </p>
        </div>
        <div class="benefit-mini-rules" aria-label="Reglas rápidas">
          <span>Cashback claro primero</span>
          <span>Promos Amex solo activadas</span>
          <span>Puntos BBVA solo si los redimes</span>
        </div>
      </section>

      <section class="benefit-recommendation-panel" aria-labelledby="benefit-recommendation-title">
        <div class="section-title-row">
          <div>
            <h2 id="benefit-recommendation-title">Para qué usar cada una</h2>
            <p>Orden práctico para compras comunes de la casa.</p>
          </div>
          <span>{{ benefitRecommendations.length }} casos</span>
        </div>

        <div class="benefit-recommendation-list">
          <article
            v-for="(recommendation, index) in benefitRecommendations"
            :key="recommendation.id"
            class="benefit-recommendation-row"
            :style="{ '--benefit-color': recommendation.accent }"
          >
            <span class="benefit-rank">{{ index + 1 }}</span>
            <div>
              <b>{{ recommendation.spend }}</b>
              <strong>{{ recommendation.product }}</strong>
              <p>{{ recommendation.reason }}</p>
              <small>{{ recommendation.note }}</small>
            </div>
          </article>
        </div>
      </section>

      <section class="benefit-product-section" aria-labelledby="benefit-product-title">
        <div class="section-title-row">
          <div>
            <h2 id="benefit-product-title">Beneficios por tarjeta o cuenta</h2>
            <p>Resumen por producto con fuente oficial.</p>
          </div>
          <span>{{ benefitsLastChecked }}</span>
        </div>

        <div class="benefit-product-list">
          <article
            v-for="product in benefitProducts"
            :key="product.id"
            class="benefit-product-card"
            :style="{ '--benefit-color': product.accent }"
          >
            <header class="benefit-product-header">
              <span>{{ product.type }}</span>
              <h2>{{ product.name }}</h2>
              <p>{{ product.issuer }} · {{ product.bestFor }}</p>
            </header>

            <div class="benefit-rule">
              <b>Regla rápida</b>
              <span>{{ product.quickRule }}</span>
            </div>

            <div class="benefit-chip-list" aria-label="Mejor para">
              <span v-for="use in product.bestUses" :key="use">{{ use }}</span>
            </div>

            <ul class="benefit-detail-list">
              <li v-for="benefit in product.benefits" :key="`${product.id}-${benefit.label}`">
                <strong>{{ benefit.value }}</strong>
                <span>
                  <b>{{ benefit.label }}</b>
                  <small>{{ benefit.detail }}</small>
                </span>
              </li>
            </ul>

            <p class="benefit-watchout">
              <b>Ojo:</b>
              {{ product.watchOut }}
            </p>

            <div class="benefit-source-list" aria-label="Fuentes">
              <a
                v-for="source in product.sources"
                :key="source.url"
                :href="source.url"
                target="_blank"
                rel="noreferrer"
              >
                {{ source.label }}
              </a>
            </div>
          </article>
        </div>
      </section>
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
            <p>Configura solo lo que necesitas para que el presupuesto familiar calcule bien.</p>
          </div>
          <div class="cutoff-row">
            <label>Día de corte<input v-model.number="settingsForm.cutoff_day" type="number" min="1" max="28" /></label>
            <label>
              Zona horaria
              <input v-model="settingsForm.time_zone" list="time-zone-options" autocomplete="off" required />
            </label>
            <datalist id="time-zone-options">
              <option v-for="timeZone in timeZoneOptions" :key="timeZone" :value="timeZone" />
            </datalist>
            <button class="primary blue-primary" type="submit" :disabled="actionBusy === 'settings'">
              {{ actionBusy === 'settings' ? 'Guardando...' : 'Guardar calendario' }}
            </button>
          </div>
          <small>Hoy en la app: {{ appToday }} · el periodo usa días del 1 al 28 para evitar meses raros.</small>
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
                <p>Administra desde dónde se pagan los gastos de la casa.</p>
              </div>
              <span>Saldo: {{ money(totalAccountBalance, settings.currency) }}</span>
            </div>
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
            <button v-if="!accountFormOpen" class="primary account-primary setup-add-button" type="button" @click="startAccountForm">
              Nueva cuenta
            </button>
            <form v-if="accountFormOpen" class="form-stack account-edit-form inline-edit-form" @submit.prevent="submitAccount">
              <div class="section-title-row compact-title-row">
                <h3>{{ accountFormTitle }}</h3>
                <button class="secondary" type="button" @click="resetAccountForm">Cerrar</button>
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
              <details class="advanced-disclosure">
                <summary>Color y estado</summary>
                <div class="advanced-body">
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
                </div>
              </details>
              <button class="primary account-primary" type="submit" :disabled="actionBusy === 'account'">
                {{ accountSubmitLabel }}
              </button>
            </form>
          </section>

          <section v-if="settingsPanel === 'people'" class="panel form-stack compact-panel people-panel">
            <div class="section-title-row">
              <div>
                <h2>Personas de casa</h2>
                <p>Separa gastos personales dentro del mismo presupuesto familiar.</p>
              </div>
              <span>{{ members.length }} totales</span>
            </div>
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
            <p v-if="!members.length" class="empty-line">Sin personas creadas.</p>
            <button v-if="!memberFormOpen" class="primary blue-primary setup-add-button" type="button" @click="startMemberForm">
              Nueva persona
            </button>
            <form v-if="memberFormOpen" class="form-stack inline-edit-form" @submit.prevent="submitMember">
              <div class="section-title-row compact-title-row">
                <h3>{{ memberFormTitle }}</h3>
                <button class="secondary" type="button" @click="resetMemberForm">Cerrar</button>
              </div>
              <label>Nombre de la persona<input v-model="memberForm.name" required /></label>
              <details class="advanced-disclosure">
                <summary>Acceso, permisos y color</summary>
                <div class="advanced-body">
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
                      <label>Correo<input v-model="memberForm.email" type="email" autocomplete="email" /></label>
                    </div>
                    <label>Clave temporal<input v-model="memberForm.password" type="password" autocomplete="new-password" :required="!editingMemberId" /></label>
                  </template>
                  <label>Color<input v-model="memberForm.color" type="color" /></label>
                </div>
              </details>
              <button class="primary blue-primary" type="submit" :disabled="actionBusy === 'member'">
                {{ memberSubmitLabel }}
              </button>
            </form>
          </section>

          <section v-if="settingsPanel === 'categories'" class="panel form-stack compact-panel categories-panel">
            <div class="section-title-row">
              <div>
                <h2>Categorías del presupuesto</h2>
                <p>Revisa presupuestos y ajusta solo lo que cambió.</p>
              </div>
              <span>{{ categories.length }} totales</span>
            </div>
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
                    {{
                      category.budget_treatment === 'tracking_only'
                        ? 'fuera de presupuesto'
                        : `${money(category.monthly_budget_cents, settings.currency)} · ${category.budget_behavior === 'carryover' ? 'acumulable' : 'mensual'}`
                    }} ·
                    {{ category.is_active ? 'activa' : 'inactiva' }}
                  </span>
                </div>
                <button class="secondary" type="button" @click="editCategory(category)">Editar</button>
              </article>
              <p v-if="!categories.length" class="empty-line">Sin categorías creadas.</p>
            </section>
            <button v-if="!categoryFormOpen" class="primary blue-primary setup-add-button" type="button" @click="startCategoryForm">
              Nueva categoría
            </button>
            <form v-if="categoryFormOpen" class="form-stack category-edit-form inline-edit-form" @submit.prevent="submitCategory">
              <div class="section-title-row compact-title-row">
                <h3>{{ categoryFormTitle }}</h3>
                <button class="secondary" type="button" @click="resetCategoryForm">Cerrar</button>
              </div>
              <div class="segmented blue-segmented">
                <button type="button" :class="{ active: categoryForm.scope === 'global' }" @click="categoryForm.scope = 'global'">Familia</button>
                <button type="button" :class="{ active: categoryForm.scope === 'personal' }" @click="categoryForm.scope = 'personal'">Personal</button>
              </div>
              <div v-if="!editingCategoryId" class="segmented blue-segmented">
                <button
                  type="button"
                  :class="{ active: categoryForm.budget_treatment === 'budgeted' }"
                  @click="categoryForm.budget_treatment = 'budgeted'"
                >
                  Presupuestada
                </button>
                <button
                  type="button"
                  :class="{ active: categoryForm.budget_treatment === 'tracking_only' }"
                  @click="categoryForm.budget_treatment = 'tracking_only'; categoryForm.budget_behavior = 'monthly_reset'"
                >
                  Fuera de presupuesto
                </button>
              </div>
              <div v-else class="commitment-readonly">
                <span>{{ categoryForm.budget_treatment === 'tracking_only' ? 'Fuera de presupuesto' : 'Presupuestada' }}</span>
              </div>
              <div v-if="!editingCategoryId" class="segmented blue-segmented">
                <button
                  type="button"
                  :class="{ active: categoryForm.budget_behavior === 'monthly_reset' }"
                  :disabled="categoryForm.budget_treatment === 'tracking_only'"
                  @click="categoryForm.budget_behavior = 'monthly_reset'"
                >
                  Mensual
                </button>
                <button
                  type="button"
                  :class="{ active: categoryForm.budget_behavior === 'carryover' }"
                  :disabled="categoryForm.budget_treatment === 'tracking_only'"
                  @click="categoryForm.budget_behavior = 'carryover'"
                >
                  Acumulable
                </button>
              </div>
              <div v-else class="commitment-readonly">
                <span>Tipo {{ categoryBehaviorLabel }}</span>
              </div>
              <label>Nombre<input v-model="categoryForm.name" required /></label>
              <label v-if="categoryForm.scope === 'personal'">
                Persona
                <select v-model="categoryForm.member" required>
                  <option value="">Elige persona</option>
                  <option v-for="member in members" :key="member.id" :value="member.id">{{ member.name }}</option>
                </select>
              </label>
              <p v-if="categoryForm.budget_treatment === 'tracking_only'" class="tracking-only-note">
                Esta categoría solo registra historial aparte; no consume presupuesto ni modifica saldos.
              </p>
              <label v-else>Presupuesto mensual<input v-model="categoryForm.monthly_budget" inputmode="decimal" required /></label>
              <div v-if="!editingCategoryId && categoryForm.budget_treatment === 'budgeted' && categoryForm.budget_behavior === 'carryover'" class="field-row">
                <label>Saldo inicial<input v-model="categoryForm.carryover_initial_balance" inputmode="decimal" required /></label>
                <label>Inicio<input v-model="categoryForm.carryover_start_date" type="date" required /></label>
              </div>
              <label v-if="editingCategoryId && categoryBudgetChanged">
                Fecha del cambio
                <input v-model="categoryForm.budget_effective_date" type="date" required />
              </label>
              <details class="advanced-disclosure">
                <summary>Icono, color y estado</summary>
                <div class="advanced-body">
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
                    Activa: aparece en presupuesto y captura de gastos
                  </label>
                </div>
              </details>
              <button class="primary blue-primary" type="submit" :disabled="actionBusy === 'category'">
                {{ categorySubmitLabel }}
              </button>
            </form>
          </section>

          <form v-if="settingsPanel === 'invitations'" class="panel form-stack compact-panel invitations-panel" @submit.prevent="submitInvitation">
            <div class="section-title-row">
              <div>
                <h2>Invitaciones</h2>
                <p>Genera un link para que otra persona entre a Burn Rate sin compartir tu contraseña.</p>
              </div>
              <span>{{ invitations.length }} activas</span>
            </div>
            <label>
              Correo
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
