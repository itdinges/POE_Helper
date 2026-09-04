<script setup lang="ts">
import type { MarketRow } from '../../api'

defineProps<{
  rows: MarketRow[]
  loading: boolean
  error: string | null
}>()

defineEmits<{
  selectRow: [itemId: string]
}>()

function showIcon(url: string | null | undefined): boolean {
  return typeof url === 'string' && url.length > 0
}
</script>

<template>
  <section class="card table-card">
    <div class="section-head">
      <div>
        <p class="label">Top entries</p>
        <h2>Current snapshot</h2>
      </div>
      <p class="muted">Click a row to inspect item history.</p>
    </div>

    <p v-if="loading" class="muted">Loading snapshot...</p>
    <p v-else-if="error" class="error">{{ error }}</p>

    <table v-else class="table">
      <thead>
        <tr>
          <th>Item</th>
          <th class="num">Chaos</th>
          <th class="num">Primary</th>
          <th>Updated</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.item_id" class="clickable" @click="$emit('selectRow', row.item_id)">
          <td>
            <div class="item-cell">
              <img v-if="showIcon(row.icon_url)" class="item-icon" :src="row.icon_url" :alt="row.item_name" loading="lazy" />
              <div>
                <div class="item-name">{{ row.item_name }}</div>
                <div class="muted tiny">{{ row.item_id }}</div>
              </div>
            </div>
          </td>
          <td class="num">{{ row.chaos_value.toFixed(3) }}</td>
          <td class="num">{{ row.primary_value.toFixed(3) }}</td>
          <td>{{ row.fetched_at }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>