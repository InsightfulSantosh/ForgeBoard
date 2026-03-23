from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class DemandLine:
    organization_id: str
    fg: str
    demand_qty: float
    fg_on_hand_qty: float
    net_demand_qty: float


@dataclass(frozen=True)
class ComponentShortage:
    component: str
    qty_per_fg: float
    required_qty: float
    available_qty: float
    shortage_qty: float


@dataclass(frozen=True)
class FGAnalysis:
    fg: str
    demand_qty: float
    fg_on_hand_qty: float
    net_demand_qty: float
    max_producible_qty: int
    recommended_build_qty: int
    coverage_ratio: float
    can_fulfill_demand: bool
    limiting_components: list[str]
    blocking_components: list[str]
    shortages: list[ComponentShortage] = field(default_factory=list)
    priority_score: float = 0.0
    priority_reason: str = ""


@dataclass(frozen=True)
class ProductionAllocation:
    fg: str
    planned_qty: int
    unmet_qty: int
    priority_score: float
    rationale: str
    consumed_components: dict[str, float]


@dataclass(frozen=True)
class AggregateShortage:
    component: str
    required_qty: float
    available_qty: float
    shortage_qty: float


@dataclass(frozen=True)
class MaterialUsage:
    component: str
    used_in_fg_count: int
    used_in_fgs: list[str]
    total_required_qty: float
    planned_consumption_qty: float
    available_qty: float
    shortage_qty: float
    usage_importance_score: float


@dataclass(frozen=True)
class WorkbookData:
    demands: list[DemandLine]
    bom: dict[str, dict[str, float]]
    inventory: dict[str, float]


@dataclass(frozen=True)
class ScenarioResult:
    analyses: list[FGAnalysis]
    production_plan: list[ProductionAllocation]
    aggregate_shortages: list[AggregateShortage]
    remaining_inventory: dict[str, float]
    metadata: dict[str, Any]
    material_usage_ranking: list[MaterialUsage] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
