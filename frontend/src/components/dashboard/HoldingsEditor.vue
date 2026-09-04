<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { HoldingItem } from '../../api'

const props = defineProps<{
  items: HoldingItem[]
  loading: boolean
  saving: boolean
  error: string | null
}>()

const emit = defineEmits<{
  save: [items: Array<{ item_id: string; item_name: string; amount: number }>]
  reload: []
}>()

const query = ref('')
const draftAmounts = ref<Record<string, string>>({})

watch(
  () => props.items,
  (rows) => {
    const next: Record<string, string> = {}
    for (const row of rows) {
      next[row.item_id] = Number.isFinite(row.amount) ? String(row.amount) : '0'
    }
    draftAmounts.value = next
  },
  { immediate: true }
)

const filteredItems = computed(() => {
  const term = query.value.trim().toLowerCase()
  if (!term) {
    return props.items
  }
  return props.items.filter((row) => {
    return row.item_name.toLowerCase().includes(term) || row.item_id.toLowerCase().includes(term)
  })
})

function toNonNegativeNumber(value: string): number {
  const parsed = Number.parseFloat(value)
  if (!Number.isFinite(parsed) || parsed < 0) {
    return 0
  }
  return parsed
}

function submitSave() {
  const payload = props.items.map((row) => ({
    item_id: row.item_id,
    item_name: row.item_name,
    amount: toNonNegativeNumber(draftAmounts.value[row.item_id] ?? '0'),
  }))
  emit('save', payload)
}

function showIcon(url: string | null | undefined): boolean {
  return typeof url === 'string' && url.length > 0
}
</script>

<template>
  <section class="card holdings-panel">
    <div class="section-head">
      <div>
        <p class="label">Holdings</p>
        <h2>Inventory amounts</h2>
      </div>
      <div class="actions">
        <button class="secondary" :disabled="loading || saving" @click="$emit('reload')">Reload</button>
        <button :disabled="loading || saving || items.length === 0" @click="submitSave">
          {{ saving ? 'Saving...' : 'Save holdings' }}
        </button>
      </div>
    </div>

    <label>
      Search item
      <input v-model="query" type="text" placeholder="Type item name or id" />
    </label>

    <p v-if="loading" class="muted">Loading holdings...</p>
    <p v-else-if="error" class="error">{{ error }}</p>
    <p v-else-if="items.length === 0" class="muted">No rows yet. Fetch market data first for this market type.</p>

    <table v-else class="table holdings-table">
      <thead>
        <tr>
          <th>Item</th>
          <th class="num">Amount</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in filteredItems" :key="row.item_id">
          <td>
            <div class="item-cell">
              <img v-if="showIcon(row.icon_url)" class="item-icon" :src="row.icon_url" :alt="row.item_name" loading="lazy" />
              <div>
                <div class="item-name">{{ row.item_name }}</div>
                <div class="muted tiny">{{ row.item_id }}</div>
              </div>
            </div>
          </td>
          <td class="num amount-input-cell">
            <input
              v-model="draftAmounts[row.item_id]"
              class="amount-input"
              type="number"
              min="0"
              step="0.01"
              inputmode="decimal"
            />
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
