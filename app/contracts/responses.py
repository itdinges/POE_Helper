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
    top_entries: list[TopEntry] = field(default_factory=list)
    vendor_opportunities: list[VendorOpportunityView] = field(default_factory=list)
    vendor_no_opportunities: bool = False
    conversion: ConversionView | None = None
    flip_simulation: FlipSimulationView | None = None
    available_routes: list[str] = field(default_factory=list)
