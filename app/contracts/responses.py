from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FilterInitResponse:
    ok: bool
    error: str | None = None
    filter_directory: str | None = None


@dataclass
class FilterListResponse:
    ok: bool
    error: str | None = None
    filter_directory: str | None = None
    filters: list[str] = field(default_factory=list)


@dataclass
class FilterBuildResponse:
    ok: bool
    error: str | None = None
    output_path: str | None = None


@dataclass
class TopEntry:
    name: str
    chaos_value: float


@dataclass
class VendorOpportunityView:
    name: str
    market_chaos_value: float
    vendor_chaos_cost: float
    margin_chaos: float


@dataclass
class ConversionView:
    from_currency: str
    to_currency: str
    amount: float
    converted_amount: float


@dataclass
class CurrencyRecommendationView:
    market_type: str
    source_currency: str
    target_currency: str
    target_name: str
    amount: float
    converted_amount: float
    value_chaos: float
    value_divine: float
    spent_source_units: float = 0.0
    leftover_source_units: float = 0.0
    action: str = "hold"
    current_ratio: float | None = None
    previous_ratio: float | None = None
    ratio_change_percent: float | None = None
    affordable_units: float = 0.0
    whole_units_affordable: int = 0
    is_affordable: bool = False
    owned_target_units: float = 0.0
    whole_units_owned: int = 0
    can_sell: bool = False
    actionable_action: str = "hold"
    trend_1h_percent: float | None = None
    trend_2h_percent: float | None = None
    trend_12h_percent: float | None = None
    trend_24h_percent: float | None = None
    short_term_reversal: str | None = None
    trend_alignment: str | None = None
    value_exalt: float | None = None


@dataclass
class TrendSignalView:
    market_type: str
    target_currency: str
    target_name: str
    short_term_reversal: str
    trend_1h_percent: float | None = None
    trend_2h_percent: float | None = None
    trend_12h_percent: float | None = None
    trend_24h_percent: float | None = None
    latest_chaos_value: float | None = None


@dataclass
class MarketRowView:
    league: str
    market_type: str
    item_id: str
    item_name: str
    chaos_value: float
    primary_value: float
    fetched_at: str
    vendor_value: float | None = None
    icon_url: str | None = None


@dataclass
class MarketSnapshotView:
    ok: bool
    league: str
    market_type: str
    latest_fetched_at: str | None = None
    item_count: int = 0
    top_entries: list[TopEntry] = field(default_factory=list)
    rows: list[MarketRowView] = field(default_factory=list)
    trend_highlights: list[TrendSignalView] = field(default_factory=list)
    error: str | None = None


@dataclass
class MarketItemHistoryPointView:
    fetched_at: str
    chaos_value: float
    primary_value: float
    vendor_value: float | None = None


@dataclass
class MarketItemHistoryView:
    ok: bool
    league: str
    market_type: str
    item_id: str
    item_name: str | None = None
    icon_url: str | None = None
    points: list[MarketItemHistoryPointView] = field(default_factory=list)
    error: str | None = None


@dataclass
class FlipSimulationView:
    route_name: str
    start_currency: str
    start_amount: float
    end_currency: str
    end_amount: float
    cost_chaos: float
    revenue_chaos: float
    profit_chaos: float
    roi_percent: float
    step_notes: list[str] = field(default_factory=list)


@dataclass
class MarketWorkflowResponse:
    ok: bool
    error: str | None = None
    error_stage: str | None = None
    snapshot_path: str | None = None
    market_data_fetched_at: str | None = None
    market_data_source: str | None = None
    top_entries: list[TopEntry] = field(default_factory=list)
    vendor_opportunities: list[VendorOpportunityView] = field(default_factory=list)
    vendor_no_opportunities: bool = False
    conversion: ConversionView | None = None
    recommendations: list[CurrencyRecommendationView] = field(default_factory=list)
    trend_highlights: list[TrendSignalView] = field(default_factory=list)
    flip_simulation: FlipSimulationView | None = None
    available_routes: list[str] = field(default_factory=list)
