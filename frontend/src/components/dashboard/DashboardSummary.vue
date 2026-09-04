<script setup lang="ts">
import type { ApiHealth } from '../../api'

defineProps<{
  backendUnavailable: boolean
  health: ApiHealth | null
  selectedRowCount: number
  latestFetchedAt: string
  league: string
  marketType: string
}>()
</script>

<template>
  <section class="card summary">
    <div>
      <p class="label">API health</p>
      <strong>{{ backendUnavailable ? 'Backend offline' : health?.ok ? 'Online' : 'Unknown' }}</strong>
      <p class="muted">
        {{ backendUnavailable ? 'Start scripts/start_web_poc.ps1 or python main.py --api' : health?.service ?? 'Waiting for backend...' }}
      </p>
    </div>
    <div>
      <p class="label">Latest fetch</p>
      <strong>{{ latestFetchedAt }}</strong>
      <p class="muted">{{ marketType }} · {{ league }}</p>
    </div>
    <div>
      <p class="label">Rows</p>
      <strong>{{ selectedRowCount }}</strong>
      <p class="muted">Current snapshot items</p>
    </div>
  </section>
</template>