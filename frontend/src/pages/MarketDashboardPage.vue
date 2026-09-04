<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  getHoldings,
  getHealth,
  getItemHistory,
  getLatestMarket,
  getMarketTypes,
  refreshMarket,
  saveHoldings,
  type ApiHealth,
  type HoldingItem,
  type HoldingsResponse,
  type MarketHistory,
  type MarketSnapshot,
  type MarketTypeResponse,
} from '../api'
import DashboardHero from '../components/dashboard/DashboardHero.vue'
import DashboardSummary from '../components/dashboard/DashboardSummary.vue'
import HoldingsEditor from '../components/dashboard/HoldingsEditor.vue'
import MarketSnapshotTable from '../components/dashboard/MarketSnapshotTable.vue'
import TrendHighlights from '../components/dashboard/TrendHighlights.vue'

const league = ref('Forbidden Rites')
const marketTypes = ref<string[]>(['Currency'])
const selectedMarketType = ref('Currency')
const marketLimit = ref(12)
const health = ref<ApiHealth | null>(null)
const snapshot = ref<MarketSnapshot | null>(null)
const history = ref<MarketHistory | null>(null)
const holdings = ref<HoldingItem[]>([])
const loading = ref(false)
const refreshing = ref(false)
const holdingsLoading = ref(false)
const holdingsSaving = ref(false)
const error = ref<string | null>(null)
const holdingsError = ref<string | null>(null)
const backendUnavailable = ref(false)

const selectedRowCount = computed(() => snapshot.value?.item_count ?? 0)
const latestFetchedAt = computed(() => snapshot.value?.latest_fetched_at ?? 'unknown')

function formatTrend(value: number | null): string {
  if (value === null || Number.isNaN(value)) {
    return 'n/a'
  }

  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}%`
}

function trendIcon(reversal: string): string {
  if (reversal === 'bullish_reversal') {
    return '↗'
  }
  if (reversal === 'bearish_reversal') {
    return '↘'
  }
  return '•'
}

function trendTone(value: number | null): string {
  if (value === null || Number.isNaN(value) || value === 0) {
    return 'neutral'
  }
  return value > 0 ? 'positive' : 'negative'
}

function showIcon(url: string | null | undefined): boolean {
  return typeof url === 'string' && url.length > 0
}

async function loadHealth() {
  try {
    health.value = await getHealth()
    backendUnavailable.value = false
  } catch {
    backendUnavailable.value = true
    health.value = null
  }
}

async function loadMarketTypes() {
  const response: MarketTypeResponse = await getMarketTypes()
  if (response.market_types.length > 0) {
    marketTypes.value = response.market_types
    selectedMarketType.value = response.market_types[0]
  }
}

async function loadSnapshot() {
  loading.value = true
  error.value = null
  history.value = null
  try {
    snapshot.value = await getLatestMarket(league.value, selectedMarketType.value, marketLimit.value)
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : 'Failed to load market snapshot.'
    snapshot.value = null
  } finally {
    loading.value = false
  }
}

async function loadHoldings() {
  holdingsLoading.value = true
  holdingsError.value = null
  try {
    const response: HoldingsResponse = await getHoldings(league.value, selectedMarketType.value)
    holdings.value = response.items
  } catch (caught) {
    holdings.value = []
    holdingsError.value = caught instanceof Error ? caught.message : 'Failed to load holdings.'
  } finally {
    holdingsLoading.value = false
  }
}

async function submitHoldings(items: Array<{ item_id: string; item_name: string; amount: number }>) {
  holdingsSaving.value = true
  holdingsError.value = null
  try {
    const response = await saveHoldings(league.value, selectedMarketType.value, items)
    holdings.value = response.items
  } catch (caught) {
    holdingsError.value = caught instanceof Error ? caught.message : 'Failed to save holdings.'
  } finally {
    holdingsSaving.value = false
  }
}

async function loadHistory(itemId: string) {
  try {
    history.value = await getItemHistory(league.value, selectedMarketType.value, itemId)
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : 'Failed to load item history.'
  }
}

async function reloadAfterRefresh() {
  refreshing.value = true
  error.value = null
  try {
    await refreshMarket(league.value, 'all', marketLimit.value, false)
    await Promise.all([loadSnapshot(), loadHoldings()])
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : 'Market refresh failed.'
  } finally {
    refreshing.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadHealth(), loadMarketTypes()])
  await Promise.all([loadSnapshot(), loadHoldings()])
})

watch(selectedMarketType, async () => {
  await Promise.all([loadSnapshot(), loadHoldings()])
})
</script>

<template>
  <div class="shell">
    <div class="top-grid">
      <DashboardHero
        v-model:league="league"
        v-model:market-type="selectedMarketType"
        v-model:market-limit="marketLimit"
        :market-types="marketTypes"
        :loading="loading"
        :refreshing="refreshing"
        @reload="loadSnapshot"
        @refresh-market="reloadAfterRefresh"
      />

      <DashboardSummary
        :backend-unavailable="backendUnavailable"
        :health="health"
        :selected-row-count="selectedRowCount"
        :latest-fetched-at="latestFetchedAt"
        :league="snapshot?.league ?? league"
        :market-type="snapshot?.market_type ?? selectedMarketType"
      />
    </div>

    <main class="bottom-grid">
      <MarketSnapshotTable
        class="snapshot-panel"
        :rows="snapshot?.rows ?? []"
        :loading="loading"
        :error="error"
        @select-row="loadHistory"
      />

      <TrendHighlights
        class="trend-panel"
        :trend-highlights="snapshot?.trend_highlights ?? []"
        :format-trend="formatTrend"
        :trend-icon="trendIcon"
        :trend-tone="trendTone"
        :show-icon="showIcon"
        :history="history"
      />

      <HoldingsEditor
        class="holdings-slot"
        :items="holdings"
        :loading="holdingsLoading"
        :saving="holdingsSaving"
        :error="holdingsError"
        @reload="loadHoldings"
        @save="submitHoldings"
      />
    </main>
  </div>
</template>