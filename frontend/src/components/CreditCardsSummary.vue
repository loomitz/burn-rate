<script setup lang="ts">
import { computed } from 'vue'
import type { CreditCardPaymentSummary, CreditCardPaymentSummaryCard } from '../stores/budget'
import { money } from '../stores/api'
import {
  cardPaymentDistributionFrom,
  cardPaymentOwnerGroupsFrom,
  cardPortfolioStatsFrom,
  type CardPaymentOwnerGroup,
} from '../creditCardViews'

const props = defineProps<{
  summary: CreditCardPaymentSummary | null
  currency: string
}>()

const emit = defineEmits<{
  openBenefits: []
  openSettings: []
}>()

const stats = computed(() => cardPortfolioStatsFrom(props.summary))
const distribution = computed(() => cardPaymentDistributionFrom(props.summary))
const cardsByDue = computed(() =>
  [...(props.summary?.cards ?? [])].sort(
    (left, right) =>
      right.closed_cycle.total_cents - left.closed_cycle.total_cents ||
      left.account_name.localeCompare(right.account_name, 'es-MX'),
  ),
)
const ownerGroups = computed<CardPaymentOwnerGroup[]>(() => {
  const groups = cardPaymentOwnerGroupsFrom(props.summary)
  if (groups.length || !props.summary?.cards.length) return groups
  return [
    {
      owner: {
        member: null,
        total_cents: props.summary.total_cents,
        account_ids: props.summary.cards.map((card) => card.account_id),
      },
      cards: props.summary.cards,
    },
  ]
})

const donutStyle = computed(() => {
  if (!distribution.value.length) return { background: 'conic-gradient(var(--line) 0 100%)' }
  let cursor = 0
  const segments = distribution.value.map((item) => {
    const start = cursor
    cursor += item.percent
    return `${item.account_color} ${start.toFixed(2)}% ${cursor.toFixed(2)}%`
  })
  return { background: `conic-gradient(${segments.join(', ')})` }
})

const chartScaleLabel = computed(() => money(stats.value.max_cycle_total_cents, props.currency))

function parseIsoDate(value: string) {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function formatDate(value: string | null | undefined, options: Intl.DateTimeFormatOptions = {}) {
  if (!value) return 'Por configurar'
  return new Intl.DateTimeFormat('es-MX', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    ...options,
  }).format(parseIsoDate(value))
}

function formatShortDate(value: string | null | undefined) {
  return formatDate(value, { day: 'numeric', month: 'short' })
}

function daysBetween(from: string, to: string) {
  const dayMs = 24 * 60 * 60 * 1000
  const fromDate = parseIsoDate(from)
  const toDate = parseIsoDate(to)
  return Math.round((toDate.getTime() - fromDate.getTime()) / dayMs)
}

function paymentTimingLabel(paymentDate: string) {
  if (!props.summary?.as_of) return 'Pago preventivo'
  const days = daysBetween(props.summary.as_of, paymentDate)
  if (days < 0) return 'Fecha preventiva pasada'
  if (days === 0) return 'Pagar hoy'
  if (days === 1) return 'Pagar mañana'
  return `En ${days} días`
}

function paymentTimingTone(paymentDate: string) {
  if (!props.summary?.as_of) return 'neutral'
  const days = daysBetween(props.summary.as_of, paymentDate)
  if (days < 0) return 'late'
  if (days <= 3) return 'soon'
  return 'neutral'
}

function cycleBarWidth(amountCents: number) {
  if (!stats.value.max_cycle_total_cents) return '0%'
  return `${Math.max(0, Math.min(100, (amountCents / stats.value.max_cycle_total_cents) * 100))}%`
}

function compositionWidth(amountCents: number, totalCents: number) {
  if (!totalCents) return '0%'
  return `${Math.max(0, Math.min(100, (amountCents / totalCents) * 100))}%`
}

function cardPaymentCycle(card: CreditCardPaymentSummaryCard) {
  if (card.closed_cycle.total_cents > 0) return card.closed_cycle
  if (card.open_cycle.total_cents > 0) return card.open_cycle
  return null
}

function cardPaymentDate(card: CreditCardPaymentSummaryCard) {
  return cardPaymentCycle(card)?.safe_payment_date ?? null
}

function cardBankDueDate(card: CreditCardPaymentSummaryCard) {
  return cardPaymentCycle(card)?.payment_due_date ?? null
}

function cardHasConfiguredDeadline(card: CreditCardPaymentSummaryCard) {
  return Boolean(
    card.closed_cycle.safe_payment_date ||
      card.closed_cycle.payment_due_date ||
      card.open_cycle.safe_payment_date ||
      card.open_cycle.payment_due_date,
  )
}

function cardCountLabel(count: number) {
  return `${count} ${count === 1 ? 'tarjeta activa' : 'tarjetas activas'}`
}
</script>

<template>
  <section class="screen cards-screen">
    <div class="cards-view-tabs" role="tablist" aria-label="Secciones de tarjetas">
      <button class="active" type="button" role="tab" aria-selected="true">Resumen</button>
      <button type="button" role="tab" aria-selected="false" @click="emit('openBenefits')">Beneficios</button>
    </div>

    <header class="cards-page-header">
      <div>
        <span>Burn Rate</span>
        <h1>Tarjetas</h1>
        <p>Qué ya cortó, qué sigue creciendo y cuándo conviene pagar.</p>
      </div>
      <button class="cards-settings-action" type="button" @click="emit('openSettings')">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 7h16M7 12h10M9 17h6M7 5v4M15 10v4M11 15v4" />
        </svg>
        Ajustar tarjetas
      </button>
    </header>

    <template v-if="summary?.cards.length">
      <section class="cards-overview" aria-labelledby="cards-overview-title">
        <div class="cards-overview-copy">
          <span class="cards-kicker" id="cards-overview-title">Ciclos cerrados por pagar</span>
          <strong class="cards-due-total">{{ money(stats.due_total_cents, currency) }}</strong>
          <p>
            {{ cardCountLabel(stats.card_count) }} · corte consultado al
            {{ formatDate(summary.as_of, { day: 'numeric', month: 'long' }) }}
          </p>

          <dl class="cards-overview-metrics">
            <div>
              <dt>Acumulando</dt>
              <dd>{{ money(stats.accumulating_total_cents, currency) }}</dd>
              <small>En ciclos todavía abiertos</small>
            </div>
            <div v-if="stats.next_payment" class="next-payment-metric">
              <dt>{{ paymentTimingLabel(stats.next_payment.safe_payment_date) }}</dt>
              <dd>{{ formatShortDate(stats.next_payment.safe_payment_date) }}</dd>
              <small>
                {{ stats.next_payment.account_name }} · límite
                {{ formatShortDate(stats.next_payment.payment_due_date) }}
              </small>
            </div>
            <div v-else class="next-payment-metric">
              <dt>Siguiente pago</dt>
              <dd>Por configurar</dd>
              <small>Agrega la fecha límite de cada tarjeta.</small>
            </div>
          </dl>
        </div>

        <div class="cards-donut-panel">
          <div
            class="cards-donut"
            :style="donutStyle"
            role="img"
            :aria-label="`Distribución de ${money(stats.due_total_cents, currency)} por pagar entre ${stats.card_count} tarjetas`"
          >
            <div>
              <span>Distribución</span>
              <strong>{{ stats.card_count }}</strong>
              <small>tarjetas</small>
            </div>
          </div>
          <div class="cards-donut-legend" aria-label="Distribución por tarjeta">
            <div v-for="item in distribution" :key="item.account_id">
              <i :style="{ '--card-color': item.account_color }" aria-hidden="true"></i>
              <span>{{ item.account_name }}</span>
              <b>{{ item.percent.toFixed(0) }}%</b>
              <strong>{{ money(item.total_cents, currency) }}</strong>
            </div>
            <p v-if="!distribution.length">Aún no hay saldo en ciclos cerrados.</p>
          </div>
        </div>
      </section>

      <div class="cards-chart-grid">
        <section class="cycle-comparison-chart" aria-labelledby="cycle-comparison-title">
          <header class="cards-section-header">
            <div>
              <span>Saldo por tarjeta</span>
              <h2 id="cycle-comparison-title">Cortado vs. acumulando</h2>
            </div>
            <small>Escala máxima {{ chartScaleLabel }}</small>
          </header>

          <div class="cycle-chart-legend" aria-hidden="true">
            <span><i class="closed"></i>Por pagar</span>
            <span><i class="open"></i>Acumulando</span>
          </div>

          <div class="cycle-comparison-rows">
            <article v-for="card in cardsByDue" :key="card.account_id" :style="{ '--card-color': card.account_color }">
              <header>
                <span><i aria-hidden="true"></i>{{ card.account_name }}</span>
                <small>{{ card.owner?.name ?? 'Sin titular' }}</small>
              </header>
              <div
                class="cycle-bar-row"
                role="img"
                :aria-label="`${card.account_name}: ${money(card.closed_cycle.total_cents, currency)} por pagar`"
              >
                <span>Por pagar</span>
                <div class="cycle-track"><i class="closed" :style="{ width: cycleBarWidth(card.closed_cycle.total_cents) }"></i></div>
                <b>{{ money(card.closed_cycle.total_cents, currency) }}</b>
              </div>
              <div
                class="cycle-bar-row"
                role="img"
                :aria-label="`${card.account_name}: ${money(card.open_cycle.total_cents, currency)} acumulando`"
              >
                <span>Acumulando</span>
                <div class="cycle-track"><i class="open" :style="{ width: cycleBarWidth(card.open_cycle.total_cents) }"></i></div>
                <b>{{ money(card.open_cycle.total_cents, currency) }}</b>
              </div>
            </article>
          </div>
        </section>

        <section class="cycle-composition-chart" aria-labelledby="cycle-composition-title">
          <header class="cards-section-header">
            <div>
              <span>Composición</span>
              <h2 id="cycle-composition-title">De qué viene el saldo</h2>
            </div>
          </header>

          <div class="composition-period">
            <div class="composition-heading">
              <div>
                <span>Ciclos cerrados</span>
                <small>Listos para pagar</small>
              </div>
              <strong>{{ money(stats.due_total_cents, currency) }}</strong>
            </div>
            <div
              class="composition-track"
              role="img"
              :aria-label="`${money(stats.due_purchase_cents, currency)} en compras y ${money(stats.due_installment_cents, currency)} en mensualidades a meses`"
            >
              <i class="purchases" :style="{ width: compositionWidth(stats.due_purchase_cents, stats.due_total_cents) }"></i>
              <i class="installments" :style="{ width: compositionWidth(stats.due_installment_cents, stats.due_total_cents) }"></i>
            </div>
            <dl>
              <div>
                <dt><i class="purchases"></i>Compras</dt>
                <dd>{{ money(stats.due_purchase_cents, currency) }}</dd>
              </div>
              <div>
                <dt><i class="installments"></i>Mensualidades</dt>
                <dd>{{ money(stats.due_installment_cents, currency) }}</dd>
              </div>
            </dl>
          </div>

          <div class="composition-period open">
            <div class="composition-heading">
              <div>
                <span>Ciclos abiertos</span>
                <small>Todavía acumulando</small>
              </div>
              <strong>{{ money(stats.accumulating_total_cents, currency) }}</strong>
            </div>
            <div
              class="composition-track"
              role="img"
              :aria-label="`${money(stats.accumulating_purchase_cents, currency)} en compras y ${money(stats.accumulating_installment_cents, currency)} en mensualidades a meses abiertas`"
            >
              <i
                class="purchases"
                :style="{ width: compositionWidth(stats.accumulating_purchase_cents, stats.accumulating_total_cents) }"
              ></i>
              <i
                class="installments"
                :style="{ width: compositionWidth(stats.accumulating_installment_cents, stats.accumulating_total_cents) }"
              ></i>
            </div>
            <dl>
              <div>
                <dt><i class="purchases"></i>Compras</dt>
                <dd>{{ money(stats.accumulating_purchase_cents, currency) }}</dd>
              </div>
              <div>
                <dt><i class="installments"></i>Mensualidades</dt>
                <dd>{{ money(stats.accumulating_installment_cents, currency) }}</dd>
              </div>
            </dl>
          </div>
        </section>
      </div>

      <section class="card-schedule" aria-labelledby="card-schedule-title">
        <header class="cards-section-header">
          <div>
            <span>Próximas fechas</span>
            <h2 id="card-schedule-title">Estado de cada tarjeta</h2>
          </div>
          <small>El pago preventivo conserva 3 días de margen.</small>
        </header>

        <div class="card-owner-groups-summary">
          <section
            v-for="(group, ownerIndex) in ownerGroups"
            :key="group.owner.member?.id ?? `sin-titular-${ownerIndex}`"
            class="card-owner-summary"
          >
            <header>
              <div>
                <i :style="{ '--owner-color': group.owner.member?.color ?? 'var(--muted)' }" aria-hidden="true"></i>
                <span>{{ group.owner.member?.name ?? 'Sin titular' }}</span>
              </div>
              <strong>{{ money(group.owner.total_cents, currency) }}</strong>
            </header>

            <article
              v-for="card in group.cards"
              :key="card.account_id"
              class="card-statement-row"
              :style="{ '--card-color': card.account_color }"
            >
              <div class="card-identity">
                <span class="mini-card-mark" aria-hidden="true">
                  <i></i>
                  <i></i>
                </span>
                <div>
                  <b>{{ card.account_name }}</b>
                  <small>{{ card.closed_cycle.start }} → {{ card.closed_cycle.end }}</small>
                </div>
              </div>

              <div v-if="cardPaymentDate(card)" class="card-date-block">
                <span :class="paymentTimingTone(cardPaymentDate(card)!)">
                  {{ paymentTimingLabel(cardPaymentDate(card)!) }}
                </span>
                <strong>{{ formatShortDate(cardPaymentDate(card)) }}</strong>
                <small>Límite bancario {{ formatShortDate(cardBankDueDate(card)) }}</small>
              </div>
              <div v-else-if="cardHasConfiguredDeadline(card)" class="card-date-block current">
                <span>Sin saldo pendiente</span>
                <strong>Al día</strong>
                <small>No hay pago programado para esta tarjeta.</small>
              </div>
              <div v-else class="card-date-block pending">
                <span>Fecha pendiente</span>
                <strong>Por configurar</strong>
                <button type="button" @click="emit('openSettings')">Agregar límite</button>
              </div>

              <dl class="card-balance-block">
                <div>
                  <dt>Por pagar</dt>
                  <dd>{{ money(card.closed_cycle.total_cents, currency) }}</dd>
                </div>
                <div>
                  <dt>Acumulando</dt>
                  <dd>{{ money(card.open_cycle.total_cents, currency) }}</dd>
                </div>
              </dl>
            </article>
          </section>
        </div>
      </section>
    </template>

    <section v-else class="cards-empty-state">
      <span class="empty-card-illustration" aria-hidden="true"><i></i></span>
      <div>
        <h2>Tu resumen aparecerá aquí</h2>
        <p>Agrega una tarjeta de crédito para ver sus cortes, fechas de pago y composición.</p>
      </div>
      <button type="button" @click="emit('openSettings')">Agregar tarjeta</button>
    </section>
  </section>
</template>

<style scoped>
.cards-screen {
  --cards-accent: var(--commitments-accent);
  --cards-soft: var(--commitments-soft);
  display: grid;
  gap: var(--space-lg);
  width: min(100%, 980px);
  max-width: 980px;
}

.cards-view-tabs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
  min-height: 52px;
  border: 1px solid color-mix(in srgb, var(--cards-accent) 18%, var(--line));
  border-radius: var(--radius-sm);
  padding: 6px;
  background: var(--cards-soft);
}

.cards-view-tabs button {
  min-height: 44px;
  border-radius: var(--radius-control);
  color: var(--muted);
  background: transparent;
  font-size: var(--font-size-label);
  font-weight: 750;
}

.cards-view-tabs button.active {
  color: var(--cards-accent);
  background: var(--surface);
  box-shadow: 0 1px 2px rgba(44, 28, 20, 0.06);
}

.cards-page-header,
.cards-section-header,
.composition-heading,
.card-owner-summary > header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-md);
}

.cards-page-header > div,
.cards-section-header > div {
  min-width: 0;
}

.cards-page-header > div > span,
.cards-section-header span,
.cards-kicker {
  display: block;
  color: var(--cards-accent);
  font-size: var(--font-size-xs);
  font-weight: 850;
  letter-spacing: 0.035em;
  text-transform: uppercase;
}

.cards-page-header h1 {
  margin: 2px 0 0;
  color: var(--ink);
  font-family: var(--font-display);
  font-size: var(--font-size-title);
  font-weight: 850;
  line-height: var(--line-height-tight);
}

.cards-page-header p,
.cards-section-header small {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: var(--font-size-sm);
  font-weight: 650;
}

.cards-settings-action {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  border: 1px solid color-mix(in srgb, var(--cards-accent) 24%, var(--line));
  border-radius: var(--radius-control);
  padding: 8px 12px;
  color: var(--cards-accent);
  background: color-mix(in srgb, var(--cards-soft) 58%, var(--surface));
  font-size: var(--font-size-xs);
  font-weight: 850;
}

.cards-settings-action svg {
  width: 17px;
  height: 17px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.cards-overview {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(320px, 0.95fr);
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--cards-accent) 22%, var(--line));
  border-radius: calc(var(--radius-sm) + 4px);
  background: var(--surface);
  box-shadow: var(--shadow-soft);
  animation: cards-enter 420ms cubic-bezier(0.2, 0.75, 0.3, 1) both;
}

.cards-overview-copy {
  display: grid;
  align-content: start;
  min-width: 0;
  padding: clamp(20px, 4vw, 36px);
}

.cards-due-total {
  margin-top: 8px;
  color: var(--ink);
  font-family: var(--font-display);
  font-size: clamp(2.5rem, 7vw, 4.4rem);
  font-weight: 850;
  font-variant-numeric: tabular-nums;
  line-height: 0.98;
  letter-spacing: -0.035em;
}

.cards-overview-copy > p {
  margin: 12px 0 0;
  color: var(--muted);
  font-size: var(--font-size-sm);
  font-weight: 700;
}

.cards-overview-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-md);
  margin: clamp(24px, 5vw, 42px) 0 0;
}

.cards-overview-metrics > div {
  min-width: 0;
  padding-top: var(--space-sm);
  border-top: 1px solid color-mix(in srgb, var(--cards-accent) 20%, var(--line));
}

.cards-overview-metrics dt,
.cards-overview-metrics dd,
.cards-overview-metrics small {
  margin: 0;
}

.cards-overview-metrics dt {
  color: var(--muted);
  font-size: var(--font-size-xs);
  font-weight: 800;
}

.cards-overview-metrics dd {
  margin-top: 3px;
  overflow-wrap: anywhere;
  color: var(--cards-accent);
  font-size: clamp(1.1rem, 3vw, 1.45rem);
  font-weight: 900;
  font-variant-numeric: tabular-nums;
}

.cards-overview-metrics small {
  display: block;
  margin-top: 3px;
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  line-height: 1.35;
}

.cards-donut-panel {
  display: grid;
  grid-template-columns: minmax(156px, 0.85fr) minmax(160px, 1fr);
  align-items: center;
  gap: var(--space-lg);
  min-width: 0;
  border-left: 1px solid color-mix(in srgb, var(--cards-accent) 16%, var(--line));
  padding: clamp(20px, 4vw, 32px);
  background: color-mix(in srgb, var(--cards-soft) 38%, var(--surface));
}

.cards-donut {
  display: grid;
  place-items: center;
  width: min(100%, 210px);
  aspect-ratio: 1;
  justify-self: center;
  border-radius: 50%;
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--line) 72%, transparent);
  animation: donut-arrive 620ms cubic-bezier(0.2, 0.8, 0.25, 1) 100ms both;
}

.cards-donut > div {
  display: grid;
  place-items: center;
  width: 64%;
  aspect-ratio: 1;
  border: 1px solid color-mix(in srgb, var(--cards-accent) 12%, var(--line));
  border-radius: 50%;
  padding: 10px;
  background: var(--surface);
  box-shadow: 0 8px 24px color-mix(in srgb, var(--cards-accent) 10%, transparent);
  text-align: center;
}

.cards-donut span,
.cards-donut small {
  color: var(--muted);
  font-size: 10px;
  font-weight: 800;
}

.cards-donut strong {
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 1.65rem;
  line-height: 0.8;
}

.cards-donut-legend {
  display: grid;
  align-content: center;
  min-width: 0;
}

.cards-donut-legend > div {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 2px 8px;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid color-mix(in srgb, var(--cards-accent) 12%, var(--line));
}

.cards-donut-legend > div:last-child {
  border-bottom: 0;
}

.cards-donut-legend i {
  grid-row: 1 / span 2;
  width: 9px;
  height: 28px;
  border-radius: 999px;
  background: var(--card-color);
}

.cards-donut-legend span {
  overflow: hidden;
  color: var(--ink);
  font-size: var(--font-size-sm);
  font-weight: 850;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cards-donut-legend b {
  color: var(--cards-accent);
  font-size: 11px;
  font-weight: 900;
}

.cards-donut-legend strong {
  grid-column: 2 / -1;
  color: var(--muted);
  font-size: 11px;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
}

.cards-donut-legend p {
  margin: 0;
  color: var(--muted);
  font-size: var(--font-size-sm);
  font-weight: 700;
}

.cards-chart-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(300px, 0.8fr);
  gap: var(--space-lg);
}

.cycle-comparison-chart,
.cycle-composition-chart,
.card-schedule,
.cards-empty-state {
  min-width: 0;
  border: 1px solid color-mix(in srgb, var(--cards-accent) 16%, var(--line));
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--surface) 94%, var(--cards-soft));
}

.cycle-comparison-chart,
.cycle-composition-chart {
  display: grid;
  align-content: start;
  gap: var(--space-md);
  padding: clamp(16px, 3vw, 24px);
  animation: cards-enter 460ms cubic-bezier(0.2, 0.75, 0.3, 1) 80ms both;
}

.cards-section-header h2 {
  margin: 2px 0 0;
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 850;
  line-height: 1.15;
}

.cards-section-header > small {
  max-width: 220px;
  text-align: right;
}

.cycle-chart-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: var(--muted);
  font-size: 11px;
  font-weight: 750;
}

.cycle-chart-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.cycle-chart-legend i,
.composition-period dt i {
  width: 8px;
  height: 8px;
  border-radius: 999px;
}

.cycle-chart-legend i.closed {
  background: var(--cards-accent);
}

.cycle-chart-legend i.open {
  border: 1px solid color-mix(in srgb, var(--cards-accent) 52%, var(--line));
  background: color-mix(in srgb, var(--cards-accent) 24%, var(--surface));
}

.cycle-comparison-rows {
  display: grid;
}

.cycle-comparison-rows > article {
  display: grid;
  gap: 8px;
  padding: 14px 0;
  border-top: 1px solid color-mix(in srgb, var(--cards-accent) 12%, var(--line));
}

.cycle-comparison-rows > article > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
}

.cycle-comparison-rows > article > header span {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  gap: 7px;
  color: var(--ink);
  font-size: var(--font-size-sm);
  font-weight: 900;
}

.cycle-comparison-rows > article > header span i {
  width: 8px;
  height: 18px;
  border-radius: 999px;
  background: var(--card-color);
}

.cycle-comparison-rows > article > header small {
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
}

.cycle-bar-row {
  display: grid;
  grid-template-columns: 74px minmax(80px, 1fr) minmax(88px, auto);
  gap: 10px;
  align-items: center;
}

.cycle-bar-row > span {
  color: var(--muted);
  font-size: 10px;
  font-weight: 750;
}

.cycle-bar-row > b {
  color: var(--ink-soft);
  font-size: 11px;
  font-weight: 850;
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.cycle-track {
  overflow: hidden;
  height: 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--cards-accent) 8%, var(--paper-muted));
}

.cycle-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  transform-origin: left center;
  animation: chart-grow 680ms cubic-bezier(0.2, 0.8, 0.25, 1) 160ms both;
}

.cycle-track i.closed {
  background: var(--card-color);
}

.cycle-track i.open {
  border: 1px solid color-mix(in srgb, var(--card-color) 62%, transparent);
  background: color-mix(in srgb, var(--card-color) 28%, var(--surface));
}

.cycle-composition-chart {
  gap: 0;
}

.composition-period {
  display: grid;
  gap: 12px;
  padding: 20px 0;
  border-top: 1px solid color-mix(in srgb, var(--cards-accent) 12%, var(--line));
}

.composition-period:first-of-type {
  margin-top: var(--space-md);
}

.composition-period:last-child {
  padding-bottom: 0;
}

.composition-heading span {
  color: var(--ink);
  font-size: var(--font-size-sm);
  font-weight: 900;
}

.composition-heading small {
  display: block;
  color: var(--muted);
  font-size: 10px;
  font-weight: 700;
}

.composition-heading strong {
  color: var(--cards-accent);
  font-size: var(--font-size-sm);
  font-weight: 900;
  font-variant-numeric: tabular-nums;
}

.composition-track {
  display: flex;
  overflow: hidden;
  height: 18px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--cards-accent) 8%, var(--paper-muted));
}

.composition-track i {
  display: block;
  min-width: 0;
  height: 100%;
  transform-origin: left center;
  animation: chart-grow 720ms cubic-bezier(0.2, 0.8, 0.25, 1) 220ms both;
}

.composition-track i.purchases,
.composition-period dt i.purchases {
  background: var(--cards-accent);
}

.composition-track i.installments,
.composition-period dt i.installments {
  background: color-mix(in srgb, var(--cards-accent) 30%, var(--surface));
}

.composition-period.open .composition-track i.purchases {
  background: color-mix(in srgb, var(--cards-accent) 65%, var(--surface));
}

.composition-period dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-sm);
  margin: 0;
}

.composition-period dl > div {
  min-width: 0;
}

.composition-period dt,
.composition-period dd {
  margin: 0;
}

.composition-period dt {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--muted);
  font-size: 10px;
  font-weight: 750;
}

.composition-period dd {
  margin-top: 2px;
  color: var(--ink);
  font-size: 11px;
  font-weight: 850;
  font-variant-numeric: tabular-nums;
}

.card-schedule {
  display: grid;
  gap: var(--space-md);
  padding: clamp(16px, 3vw, 24px);
  animation: cards-enter 480ms cubic-bezier(0.2, 0.75, 0.3, 1) 140ms both;
}

.card-owner-groups-summary,
.card-owner-summary {
  display: grid;
  gap: var(--space-sm);
}

.card-owner-summary + .card-owner-summary {
  margin-top: var(--space-sm);
}

.card-owner-summary > header {
  align-items: center;
  padding-bottom: 4px;
}

.card-owner-summary > header > div {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--ink);
  font-size: var(--font-size-sm);
  font-weight: 900;
}

.card-owner-summary > header i {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: var(--owner-color);
}

.card-owner-summary > header strong {
  color: var(--cards-accent);
  font-size: var(--font-size-sm);
  font-weight: 900;
  font-variant-numeric: tabular-nums;
}

.card-statement-row {
  display: grid;
  grid-template-columns: minmax(190px, 1fr) minmax(180px, 0.8fr) minmax(210px, 0.9fr);
  gap: var(--space-lg);
  align-items: center;
  min-width: 0;
  border: 1px solid color-mix(in srgb, var(--card-color) 18%, var(--line));
  border-radius: var(--radius-control);
  padding: 14px 16px;
  background: color-mix(in srgb, var(--card-color) 4%, var(--surface));
  transition: transform 160ms ease, border-color 160ms ease, background-color 160ms ease;
}

.card-statement-row:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--card-color) 38%, var(--line));
  background: color-mix(in srgb, var(--card-color) 7%, var(--surface));
}

.card-identity {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 12px;
}

.mini-card-mark {
  position: relative;
  display: block;
  flex: 0 0 auto;
  width: 52px;
  height: 34px;
  overflow: hidden;
  border-radius: 9px;
  background: var(--card-color);
  box-shadow: inset 0 -10px 18px rgba(0, 0, 0, 0.1);
}

.mini-card-mark::before {
  content: '';
  position: absolute;
  top: 8px;
  left: 8px;
  width: 10px;
  height: 7px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.7);
}

.mini-card-mark i {
  position: absolute;
  right: 8px;
  bottom: 8px;
  width: 8px;
  height: 8px;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 50%;
}

.mini-card-mark i:last-child {
  right: 13px;
}

.card-identity > div {
  min-width: 0;
}

.card-identity b,
.card-identity small {
  display: block;
}

.card-identity b {
  overflow: hidden;
  color: var(--ink);
  font-size: var(--font-size-sm);
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-identity small,
.card-date-block small {
  color: var(--muted);
  font-size: 10px;
  font-weight: 700;
}

.card-date-block {
  display: grid;
  gap: 1px;
  min-width: 0;
  padding-left: var(--space-md);
  border-left: 1px solid color-mix(in srgb, var(--card-color) 14%, var(--line));
}

.card-date-block > span {
  color: var(--muted);
  font-size: 10px;
  font-weight: 850;
}

.card-date-block > span.soon {
  color: var(--ember);
}

.card-date-block > span.late {
  color: var(--danger-dark);
}

.card-date-block > strong {
  color: var(--ink);
  font-size: 1rem;
  font-weight: 900;
  font-variant-numeric: tabular-nums;
}

.card-date-block.pending button {
  justify-self: start;
  min-height: 30px;
  margin-top: 4px;
  padding: 4px 9px;
  border: 1px solid color-mix(in srgb, var(--cards-accent) 24%, var(--line));
  border-radius: 999px;
  color: var(--cards-accent);
  background: var(--cards-soft);
  font-size: 10px;
  font-weight: 850;
}

.card-balance-block {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-md);
  margin: 0;
}

.card-balance-block div {
  min-width: 0;
}

.card-balance-block dt,
.card-balance-block dd {
  margin: 0;
}

.card-balance-block dt {
  color: var(--muted);
  font-size: 10px;
  font-weight: 750;
}

.card-balance-block dd {
  margin-top: 2px;
  overflow-wrap: anywhere;
  color: var(--ink);
  font-size: var(--font-size-sm);
  font-weight: 900;
  font-variant-numeric: tabular-nums;
}

.card-balance-block div:first-child dd {
  color: var(--cards-accent);
}

.cards-empty-state {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: var(--space-lg);
  align-items: center;
  padding: clamp(22px, 5vw, 40px);
}

.empty-card-illustration {
  position: relative;
  width: 76px;
  height: 50px;
  border: 2px solid color-mix(in srgb, var(--cards-accent) 55%, var(--line));
  border-radius: 14px;
  background: var(--cards-soft);
  transform: rotate(-4deg);
}

.empty-card-illustration::before {
  content: '';
  position: absolute;
  top: 12px;
  right: -12px;
  width: 66px;
  height: 44px;
  border: 2px solid color-mix(in srgb, var(--cards-accent) 32%, var(--line));
  border-radius: 12px;
  background: var(--surface);
  transform: rotate(8deg);
}

.cards-empty-state h2 {
  margin: 0;
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 1.35rem;
}

.cards-empty-state p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: var(--font-size-sm);
  font-weight: 650;
}

.cards-empty-state button {
  min-height: 44px;
  border-radius: var(--radius-control);
  padding: 8px 14px;
  color: var(--surface);
  background: var(--cards-accent);
  font-size: var(--font-size-sm);
  font-weight: 850;
}

@keyframes cards-enter {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes donut-arrive {
  from {
    opacity: 0;
    transform: rotate(-12deg) scale(0.9);
  }
  to {
    opacity: 1;
    transform: rotate(0) scale(1);
  }
}

@keyframes chart-grow {
  from {
    transform: scaleX(0);
  }
  to {
    transform: scaleX(1);
  }
}

@media (max-width: 820px) {
  .cards-overview,
  .cards-chart-grid {
    grid-template-columns: 1fr;
  }

  .cards-donut-panel {
    border-top: 1px solid color-mix(in srgb, var(--cards-accent) 16%, var(--line));
    border-left: 0;
  }

  .card-statement-row {
    grid-template-columns: minmax(180px, 1fr) minmax(170px, 0.8fr);
  }

  .card-balance-block {
    grid-column: 1 / -1;
    padding-top: var(--space-sm);
    border-top: 1px solid color-mix(in srgb, var(--card-color) 14%, var(--line));
  }
}

@media (max-width: 560px) {
  .cards-screen {
    gap: var(--space-md);
  }

  .cards-page-header {
    display: grid;
  }

  .cards-settings-action {
    justify-self: start;
  }

  .cards-overview-copy,
  .cards-donut-panel,
  .cycle-comparison-chart,
  .cycle-composition-chart,
  .card-schedule {
    padding: var(--space-md);
  }

  .cards-due-total {
    font-size: clamp(2.25rem, 13vw, 3.2rem);
  }

  .cards-overview-metrics,
  .composition-period dl {
    grid-template-columns: 1fr;
  }

  .cards-donut-panel {
    grid-template-columns: 1fr;
  }

  .cards-donut {
    width: min(66vw, 210px);
  }

  .cards-section-header {
    display: grid;
  }

  .cards-section-header > small {
    max-width: none;
    margin-top: 0;
    text-align: left;
  }

  .cycle-bar-row {
    grid-template-columns: 68px minmax(60px, 1fr);
    gap: 8px;
  }

  .cycle-bar-row > b {
    grid-column: 2;
    text-align: left;
  }

  .card-statement-row {
    grid-template-columns: 1fr;
    gap: var(--space-sm);
  }

  .card-date-block,
  .card-balance-block {
    padding-top: var(--space-sm);
    padding-left: 0;
    border-top: 1px solid color-mix(in srgb, var(--card-color) 14%, var(--line));
    border-left: 0;
  }

  .cards-empty-state {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .cards-overview,
  .cycle-comparison-chart,
  .cycle-composition-chart,
  .card-schedule,
  .cards-donut,
  .cycle-track i,
  .composition-track i {
    animation: none;
  }

  .card-statement-row {
    transition: none;
  }
}
</style>
