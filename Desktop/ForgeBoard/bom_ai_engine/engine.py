from __future__ import annotations

import math
from collections import defaultdict
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from .models import (
    AggregateShortage,
    ComponentShortage,
    DemandLine,
    FGAnalysis,
    MaterialUsage,
    ProductionAllocation,
    ScenarioResult,
    WorkbookData,
)
from .xlsx_reader import read_xlsx


class WorkbookFormatError(ValueError):
    pass


def load_workbook_data(workbook_path: str | Path) -> WorkbookData:
    sheets = read_xlsx(workbook_path)

    demand_table = _extract_table(
        sheets.get("Demand", []),
        required_headers={"Assembly (FG)", "Demand Qty", "On-hand Qty"},
    )
    bom_table = _extract_table(
        sheets.get("BOM Explode", []),
        required_headers={"TOP_ITEM", "COMPONENT_ITEM", "PLAN_LEVEL"},
    )
    inventory_table = _extract_table(
        sheets.get("On-hand Qty", []),
        required_headers={"Item Code", "On-hand Qty"},
    )

    demands: list[DemandLine] = []
    for row in demand_table:
        fg = _clean(row.get("Assembly (FG)"))
        if not fg:
            continue

        demand_qty = _to_float(row.get("Demand Qty"))
        fg_on_hand_qty = _to_float(row.get("On-hand Qty"))
        demands.append(
            DemandLine(
                organization_id=_clean(row.get("Org")),
                fg=fg,
                demand_qty=demand_qty,
                fg_on_hand_qty=fg_on_hand_qty,
                net_demand_qty=max(demand_qty - fg_on_hand_qty, 0.0),
            )
        )

    bom: dict[str, dict[str, float]] = defaultdict(dict)
    for row in bom_table:
        fg = _clean(row.get("TOP_ITEM"))
        component = _clean(row.get("COMPONENT_ITEM"))
        plan_level = int(_to_float(row.get("PLAN_LEVEL")))
        qty_per_fg = _to_float(row.get("EXTENDED_QUANTITY")) or _to_float(
            row.get("COMPONENT_QUANTITY")
        )

        if not fg or not component or plan_level <= 0 or qty_per_fg <= 0:
            continue

        current = bom[fg].get(component, 0.0)
        bom[fg][component] = current + qty_per_fg

    inventory: dict[str, float] = defaultdict(float)
    for row in inventory_table:
        item_code = _clean(row.get("Item Code"))
        if not item_code:
            continue
        inventory[item_code] += _to_float(row.get("On-hand Qty"))

    return WorkbookData(demands=demands, bom=dict(bom), inventory=dict(inventory))


def apply_scenario(
    data: WorkbookData,
    demand_multiplier: float = 1.0,
    procurement: dict[str, float] | None = None,
) -> WorkbookData:
    adjusted_demands = [
        replace(
            demand,
            demand_qty=demand.demand_qty * demand_multiplier,
            net_demand_qty=max((demand.demand_qty * demand_multiplier) - demand.fg_on_hand_qty, 0.0),
        )
        for demand in data.demands
    ]

    adjusted_inventory = deepcopy(data.inventory)
    for item, qty in (procurement or {}).items():
        adjusted_inventory[item] = adjusted_inventory.get(item, 0.0) + float(qty)

    return WorkbookData(demands=adjusted_demands, bom=deepcopy(data.bom), inventory=adjusted_inventory)


class ProductionPlanner:
    def run(
        self,
        data: WorkbookData,
        priority_hints: dict[str, dict[str, float]] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ScenarioResult:
        analyses = [self._analyse_fg(demand, data.bom.get(demand.fg, {}), data.inventory) for demand in data.demands]
        scored_analyses = self._score_analyses(analyses, data.bom, priority_hints or {})
        production_plan, remaining_inventory = self._allocate(scored_analyses, data.bom, data.inventory)
        aggregate_shortages = self._aggregate_shortages(data)
        material_usage_ranking = self._build_material_usage_ranking(data, production_plan)

        return ScenarioResult(
            analyses=scored_analyses,
            production_plan=production_plan,
            aggregate_shortages=aggregate_shortages,
            remaining_inventory=remaining_inventory,
            metadata=metadata or {},
            material_usage_ranking=material_usage_ranking,
        )

    def _analyse_fg(
        self,
        demand: DemandLine,
        requirements: dict[str, float],
        inventory: dict[str, float],
    ) -> FGAnalysis:
        if not requirements:
            return FGAnalysis(
                fg=demand.fg,
                demand_qty=demand.demand_qty,
                fg_on_hand_qty=demand.fg_on_hand_qty,
                net_demand_qty=demand.net_demand_qty,
                max_producible_qty=0,
                recommended_build_qty=0,
                coverage_ratio=0.0,
                can_fulfill_demand=False,
                limiting_components=[],
                blocking_components=["NO_BOM_FOUND"],
                shortages=[],
            )

        component_limits: list[tuple[str, float]] = []
        shortages: list[ComponentShortage] = []

        for component, qty_per_fg in requirements.items():
            available_qty = inventory.get(component, 0.0)
            possible_units = math.inf if qty_per_fg <= 0 else available_qty / qty_per_fg
            component_limits.append((component, possible_units))

            required_qty = demand.net_demand_qty * qty_per_fg
            shortage_qty = max(required_qty - available_qty, 0.0)
            if shortage_qty > 1e-9:
                shortages.append(
                    ComponentShortage(
                        component=component,
                        qty_per_fg=qty_per_fg,
                        required_qty=required_qty,
                        available_qty=available_qty,
                        shortage_qty=shortage_qty,
                    )
                )

        min_possible_units = min(limit for _, limit in component_limits)
        max_producible_qty = _whole_units(min_possible_units)
        net_demand_units = _whole_units(demand.net_demand_qty)
        recommended_build_qty = min(max_producible_qty, net_demand_units)
        coverage_ratio = (
            1.0 if net_demand_units == 0 else round(recommended_build_qty / net_demand_units, 4)
        )
        limiting_value = min_possible_units
        limiting_components = sorted(
            component for component, limit in component_limits if abs(limit - limiting_value) < 1e-9
        )
        blocking_components: list[str] = list(limiting_components)
        for shortage in sorted(shortages, key=lambda item: item.shortage_qty, reverse=True):
            if shortage.component not in blocking_components:
                blocking_components.append(shortage.component)
            if len(blocking_components) >= 5:
                break

        return FGAnalysis(
            fg=demand.fg,
            demand_qty=demand.demand_qty,
            fg_on_hand_qty=demand.fg_on_hand_qty,
            net_demand_qty=demand.net_demand_qty,
            max_producible_qty=max_producible_qty,
            recommended_build_qty=recommended_build_qty,
            coverage_ratio=coverage_ratio,
            can_fulfill_demand=recommended_build_qty >= net_demand_units,
            limiting_components=limiting_components,
            blocking_components=blocking_components,
            shortages=sorted(shortages, key=lambda item: item.shortage_qty, reverse=True),
        )

    def _score_analyses(
        self,
        analyses: list[FGAnalysis],
        bom: dict[str, dict[str, float]],
        priority_hints: dict[str, dict[str, float]],
    ) -> list[FGAnalysis]:
        demand_values = [analysis.net_demand_qty for analysis in analyses]
        efficiency_values = [
            0.0 if not bom.get(analysis.fg) else 1.0 / sum(bom[analysis.fg].values())
            for analysis in analyses
        ]
        scarcity_values = [
            0.0
            if not bom.get(analysis.fg)
            else len(analysis.shortages) / max(len(bom[analysis.fg]), 1)
            for analysis in analyses
        ]

        demand_scale = _build_scale(demand_values)
        efficiency_scale = _build_scale(efficiency_values)
        scarcity_scale = _build_scale(scarcity_values, invert=True)

        scored: list[FGAnalysis] = []
        for analysis in analyses:
            hints = priority_hints.get(analysis.fg, {})
            demand_signal = demand_scale(analysis.net_demand_qty)
            efficiency_signal = efficiency_scale(
                0.0 if not bom.get(analysis.fg) else 1.0 / sum(bom[analysis.fg].values())
            )
            scarcity_signal = scarcity_scale(
                0.0
                if not bom.get(analysis.fg)
                else len(analysis.shortages) / max(len(bom[analysis.fg]), 1)
            )
            coverage_signal = analysis.coverage_ratio
            business_signal = _clip(hints.get("business_priority", 0.0))
            margin_signal = _clip(hints.get("margin_score", 0.0))
            service_signal = _clip(hints.get("service_level_weight", 0.0))

            score = (
                (coverage_signal * 0.40)
                + (demand_signal * 0.15)
                + (efficiency_signal * 0.10)
                + (scarcity_signal * 0.10)
                + (business_signal * 0.15)
                + (margin_signal * 0.05)
                + (service_signal * 0.05)
            ) * 100.0
            score = round(score, 2)

            reason = (
                f"coverage={coverage_signal:.0%}, "
                f"demand={demand_signal:.0%}, "
                f"efficiency={efficiency_signal:.0%}, "
                f"scarcity={scarcity_signal:.0%}"
            )
            if hints:
                reason += (
                    f", business={business_signal:.0%}, "
                    f"margin={margin_signal:.0%}, "
                    f"service={service_signal:.0%}"
                )

            scored.append(replace(analysis, priority_score=score, priority_reason=reason))

        return sorted(
            scored,
            key=lambda item: (
                item.priority_score,
                item.coverage_ratio,
                item.max_producible_qty,
                item.net_demand_qty,
            ),
            reverse=True,
        )

    def _allocate(
        self,
        analyses: list[FGAnalysis],
        bom: dict[str, dict[str, float]],
        inventory: dict[str, float],
    ) -> tuple[list[ProductionAllocation], dict[str, float]]:
        remaining_inventory = deepcopy(inventory)
        allocations: list[ProductionAllocation] = []

        for analysis in analyses:
            requirements = bom.get(analysis.fg, {})
            if not requirements:
                allocations.append(
                    ProductionAllocation(
                        fg=analysis.fg,
                        planned_qty=0,
                        unmet_qty=_whole_units(analysis.net_demand_qty),
                        priority_score=analysis.priority_score,
                        rationale="No BOM found for this FG.",
                        consumed_components={},
                    )
                )
                continue

            possible_units = min(
                (remaining_inventory.get(component, 0.0) / qty_per_fg)
                for component, qty_per_fg in requirements.items()
                if qty_per_fg > 0
            )
            plan_qty = min(_whole_units(possible_units), _whole_units(analysis.net_demand_qty))
            consumed_components: dict[str, float] = {}
            for component, qty_per_fg in requirements.items():
                consumed_qty = plan_qty * qty_per_fg
                consumed_components[component] = consumed_qty
                remaining_inventory[component] = remaining_inventory.get(component, 0.0) - consumed_qty

            unmet_qty = max(_whole_units(analysis.net_demand_qty) - plan_qty, 0)
            allocations.append(
                ProductionAllocation(
                    fg=analysis.fg,
                    planned_qty=plan_qty,
                    unmet_qty=unmet_qty,
                    priority_score=analysis.priority_score,
                    rationale=analysis.priority_reason,
                    consumed_components=consumed_components,
                )
            )

        return allocations, remaining_inventory

    def _aggregate_shortages(self, data: WorkbookData) -> list[AggregateShortage]:
        total_requirements: dict[str, float] = defaultdict(float)
        for demand in data.demands:
            for component, qty_per_fg in data.bom.get(demand.fg, {}).items():
                total_requirements[component] += qty_per_fg * demand.net_demand_qty

        shortages: list[AggregateShortage] = []
        for component, required_qty in total_requirements.items():
            available_qty = data.inventory.get(component, 0.0)
            shortage_qty = max(required_qty - available_qty, 0.0)
            if shortage_qty > 1e-9:
                shortages.append(
                    AggregateShortage(
                        component=component,
                        required_qty=required_qty,
                        available_qty=available_qty,
                        shortage_qty=shortage_qty,
                    )
                )

        return sorted(shortages, key=lambda item: item.shortage_qty, reverse=True)

    def _build_material_usage_ranking(
        self,
        data: WorkbookData,
        production_plan: list[ProductionAllocation],
    ) -> list[MaterialUsage]:
        total_requirements: dict[str, float] = defaultdict(float)
        used_in_fgs: dict[str, set[str]] = defaultdict(set)
        planned_consumption: dict[str, float] = defaultdict(float)

        for demand in data.demands:
            for component, qty_per_fg in data.bom.get(demand.fg, {}).items():
                required_qty = qty_per_fg * demand.net_demand_qty
                if required_qty <= 0:
                    continue
                total_requirements[component] += required_qty
                used_in_fgs[component].add(demand.fg)

        for allocation in production_plan:
            for component, consumed_qty in allocation.consumed_components.items():
                planned_consumption[component] += consumed_qty

        if not total_requirements:
            return []

        fg_count_values = [len(used_in_fgs[component]) for component in total_requirements]
        required_values = [total_requirements[component] for component in total_requirements]
        planned_values = [planned_consumption.get(component, 0.0) for component in total_requirements]

        fg_count_scale = _build_scale(fg_count_values)
        required_scale = _build_scale(required_values)
        planned_scale = _build_scale(planned_values)

        ranking: list[MaterialUsage] = []
        for component, total_required_qty in total_requirements.items():
            used_count = len(used_in_fgs[component])
            available_qty = data.inventory.get(component, 0.0)
            planned_qty = planned_consumption.get(component, 0.0)
            shortage_qty = max(total_required_qty - available_qty, 0.0)
            usage_importance_score = round(
                (
                    (fg_count_scale(used_count) * 0.45)
                    + (required_scale(total_required_qty) * 0.40)
                    + (planned_scale(planned_qty) * 0.15)
                )
                * 100.0,
                2,
            )

            ranking.append(
                MaterialUsage(
                    component=component,
                    used_in_fg_count=used_count,
                    used_in_fgs=sorted(used_in_fgs[component]),
                    total_required_qty=total_required_qty,
                    planned_consumption_qty=planned_qty,
                    available_qty=available_qty,
                    shortage_qty=shortage_qty,
                    usage_importance_score=usage_importance_score,
                )
            )

        return sorted(
            ranking,
            key=lambda item: (
                -item.usage_importance_score,
                -item.used_in_fg_count,
                -item.total_required_qty,
                -item.planned_consumption_qty,
                -item.shortage_qty,
                item.component,
            ),
        )


def _extract_table(
    rows: list[list[str | None]],
    required_headers: set[str],
) -> list[dict[str, str | None]]:
    header_index = None
    headers: list[str | None] | None = None

    for index, row in enumerate(rows):
        row_headers = {_clean(cell) for cell in row if _clean(cell)}
        if required_headers.issubset(row_headers):
            header_index = index
            headers = row
            break

    if header_index is None or headers is None:
        missing = ", ".join(sorted(required_headers))
        raise WorkbookFormatError(f"Could not find a table header with columns: {missing}")

    records: list[dict[str, str | None]] = []
    for row in rows[header_index + 1 :]:
        if not any(_clean(cell) for cell in row):
            continue
        record: dict[str, str | None] = {}
        for position, header in enumerate(headers):
            header_name = _clean(header)
            if not header_name:
                continue
            record[header_name] = row[position] if position < len(row) else None
        records.append(record)

    return records


def _to_float(value: str | None) -> float:
    if value is None:
        return 0.0
    text = str(value).strip()
    if not text:
        return 0.0
    return float(text)


def _clean(value: str | None) -> str:
    return "" if value is None else str(value).strip()


def _whole_units(value: float) -> int:
    if math.isinf(value):
        return 0
    return max(int(math.floor(value + 1e-9)), 0)


def _clip(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


def _build_scale(values: list[float], invert: bool = False):
    if not values:
        return lambda _: 0.0
    minimum = min(values)
    maximum = max(values)

    if math.isclose(minimum, maximum):
        if invert:
            return lambda _: 1.0
        return lambda _: 1.0

    def scale(value: float) -> float:
        normalized = (value - minimum) / (maximum - minimum)
        return 1.0 - normalized if invert else normalized

    return scale
