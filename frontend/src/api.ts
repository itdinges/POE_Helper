export type ApiHealth = {
  ok: boolean
  service: string
  layer: string
}

export type MarketTypeResponse = {
  ok: boolean
  market_types: string[]
}

export type TopEntry = {
  name: string
  chaos_value: number
}

export type TrendSignal = {
  market_type: string
  target_currency: string
  target_name: string
  short_term_reversal: string
  trend_1h_percent: number | null
  trend_2h_percent: number | null
  trend_12h_percent: number | null
  trend_24h_percent: number | null
  latest_chaos_value: number | null
}

export type MarketRow = {
  league: string
  market_type: string
  item_id: string
  item_name: string
  icon_url: string | null
  chaos_value: number
  primary_value: number
  fetched_at: string
  vendor_value: number | null
}

export type MarketSnapshot = {
  ok: boolean
  league: string
  market_type: string
  latest_fetched_at: string | null
  item_count: number
  top_entries: TopEntry[]
  rows: MarketRow[]
  trend_highlights: TrendSignal[]
  error?: string | null
}

export type MarketHistoryPoint = {
  fetched_at: string
  chaos_value: number
  primary_value: number
  vendor_value: number | null
}

export type MarketHistory = {
  ok: boolean
  league: string
  market_type: string
  item_id: string
  item_name: string | null
  icon_url: string | null
  points: MarketHistoryPoint[]
  error?: string | null
}

const apiBase = ''

async function readJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed with status ${response.status}`)
  }

  return response.json() as Promise<T>
}

export function getHealth(): Promise<ApiHealth> {
  return readJson<ApiHealth>('/api/health')
}

export function getMarketTypes(): Promise<MarketTypeResponse> {
  return readJson<MarketTypeResponse>('/api/market/types')
}

export function getLatestMarket(league: string, marketType: string, limit: number): Promise<MarketSnapshot> {
  const params = new URLSearchParams({ league, market_type: marketType, limit: String(limit) })
  return readJson<MarketSnapshot>(`/api/market/latest?${params.toString()}`)
}

export function refreshMarket(league: string, marketType: string, limit: number): Promise<MarketSnapshot> {
  const params = new URLSearchParams({ league, market_type: marketType, market_limit: String(limit) })
  return readJson<MarketSnapshot>(`/api/market/refresh?${params.toString()}`, {
    method: 'POST',
  })
}

export function getItemHistory(league: string, marketType: string, itemId: string): Promise<MarketHistory> {
  const params = new URLSearchParams({ league, market_type: marketType })
  return readJson<MarketHistory>(`/api/market/history/${encodeURIComponent(itemId)}?${params.toString()}`)
}