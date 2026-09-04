<script setup lang="ts">
import type { MarketHistory, TrendSignal } from '../../api'

defineProps<{
  trendHighlights: TrendSignal[]
  history: MarketHistory | null
  formatTrend: (value: number | null) => string
  trendIcon: (reversal: string) => string
  trendTone: (value: number | null) => string
  showIcon: (url: string | null | undefined) => boolean
}>()
</script>

<template>
  <section class="card side-panel">
    <div class="section-head">
      <div>
        <p class="label">Trend highlights</p>
        <h2>Short-term reversals</h2>
      </div>
    </div>

    <div v-if="trendHighlights.length" class="stack">
      <article v-for="entry in trendHighlights" :key="entry.target_currency" class="mini-card">
        <div class="mini-head">
          <div class="mini-title">
            <span class="mini-icon" :class="entry.short_term_reversal">{{ trendIcon(entry.short_term_reversal) }}</span>
            <strong>{{ entry.target_name }}</strong>
          </div>
          <span :class="['badge', entry.short_term_reversal]">{{ entry.short_term_reversal }}</span>
        </div>
        <div class="trend-grid">
          <span class="trend-chip" :class="trendTone(entry.trend_1h_percent)">
            <span class="trend-label">1h</span>
            <strong>{{ formatTrend(entry.trend_1h_percent) }}</strong>
          </span>
          <span class="trend-chip" :class="trendTone(entry.trend_2h_percent)">
            <span class="trend-label">2h</span>
            <strong>{{ formatTrend(entry.trend_2h_percent) }}</strong>
          </span>
          <span class="trend-chip" :class="trendTone(entry.trend_12h_percent)">
            <span class="trend-label">12h</span>
            <strong>{{ formatTrend(entry.trend_12h_percent) }}</strong>
          </span>
          <span class="trend-chip" :class="trendTone(entry.trend_24h_percent)">
            <span class="trend-label">24h</span>
            <strong>{{ formatTrend(entry.trend_24h_percent) }}</strong>
          </span>
        </div>
      </article>
    </div>
    <p v-else class="muted">No reversal signals in the current snapshot.</p>

    <div class="history-panel">
      <div class="section-head compact">
        <div>
          <p class="label">Item history</p>
          <div class="history-title">
            <img
              v-if="showIcon(history?.icon_url)"
              class="history-icon"
              :src="history?.icon_url || undefined"
              :alt="history?.item_name ?? 'Selected item'"
              loading="lazy"
            />
            <h3>{{ history?.item_name ?? 'Select an item' }}</h3>
          </div>
        </div>
      </div>

      <p v-if="!history" class="muted">Pick a row to show its price path.</p>

      <div v-else class="history-list">
        <div v-for="point in history.points" :key="point.fetched_at" class="history-point">
          <div class="history-label">
            <span>{{ point.fetched_at }}</span>
            <strong>{{ point.chaos_value.toFixed(3) }} chaos</strong>
          </div>
          <div class="bar-track">
            <span class="bar" :style="{ width: Math.min(point.chaos_value, 100) + '%' }"></span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>