<script setup lang="ts">
const league = defineModel<string>('league', { required: true })
const marketType = defineModel<string>('marketType', { required: true })
const marketLimit = defineModel<number>('marketLimit', { required: true })

defineProps<{
  marketTypes: string[]
  loading: boolean
  refreshing: boolean
}>()

defineEmits<{
  reload: []
  refreshMarket: []
}>()
</script>

<template>
  <header class="hero">
    <div>
      <p class="eyebrow">POE Helper</p>
      <h1>Market dashboard</h1>
      <p class="lede">
        View fresh market data, trend reversals, and item history without jumping back into the CLI.
      </p>
    </div>

    <div class="hero-panel">
      <label>
        League
        <input v-model="league" type="text" />
      </label>

      <label>
        Market type
        <select v-model="marketType">
          <option v-for="type in marketTypes" :key="type" :value="type">{{ type }}</option>
        </select>
      </label>

      <label>
        Rows
        <input v-model.number="marketLimit" type="number" min="1" max="100" />
      </label>

      <div class="actions">
        <button :disabled="loading || refreshing" @click="$emit('reload')">Reload</button>
        <button class="secondary" :disabled="refreshing" @click="$emit('refreshMarket')">
          {{ refreshing ? 'Refreshing...' : 'Refresh market' }}
        </button>
      </div>
    </div>
  </header>
</template>