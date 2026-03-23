from __future__ import annotations

from typing import Any


def build_phase1_report(result: dict[str, Any]) -> str:
    metadata = result.get("metadata", {})
    analyses = result.get("analyses", [])
    shortages = result.get("aggregate_shortages", [])
    production_plan = result.get("production_plan", [])

    lines: list[str] = []
    lines.append("# Phase 1 Production Feasibility Report")
    lines.append("")
    workbook = metadata.get("workbook", "Unknown workbook")
    lines.append(f"- Workbook: `{workbook}`")
    lines.append(f"- Demand multiplier: `{metadata.get('demand_multiplier', 1.0)}`")
    lines.append(f"- Generated at UTC: `{metadata.get('generated_at_utc', 'unknown')}`")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("Phase 1 is deterministic planning logic, not predictive AI.")
    lines.append("")
    lines.append("- Demand to BOM requirement explosion")
    lines.append("- Inventory matching and shortage detection")
    lines.append("- Max producible quantity per FG")
    lines.append("- Priority-based production allocation")
    lines.append("- Scenario simulation using demand and procurement overrides")
    lines.append("")
    lines.append("## Finished Goods Summary")
    lines.append("")
    lines.append("| FG | Net Demand | Max Producible | Recommended Build | Coverage | Limiting Components |")
    lines.append("| --- | ---: | ---: | ---: | ---: | --- |")
    for analysis in analyses:
        lines.append(
            "| "
            f"{analysis['fg']} | "
            f"{int(round(analysis['net_demand_qty']))} | "
            f"{analysis['max_producible_qty']} | "
            f"{analysis['recommended_build_qty']} | "
            f"{analysis['coverage_ratio']:.0%} | "
            f"{', '.join(analysis['limiting_components']) or 'None'} |"
        )
    lines.append("")
    lines.append("## Production Plan")
    lines.append("")
    lines.append("| FG | Planned Qty | Unmet Qty | Priority Score |")
    lines.append("| --- | ---: | ---: | ---: |")
    for row in production_plan:
        lines.append(
            f"| {row['fg']} | {row['planned_qty']} | {row['unmet_qty']} | {row['priority_score']:.2f} |"
        )
    lines.append("")
    lines.append("## Top Material Shortages")
    lines.append("")
    lines.append("| Component | Required Qty | Available Qty | Shortage Qty |")
    lines.append("| --- | ---: | ---: | ---: |")
    for shortage in shortages[:10]:
        lines.append(
            "| "
            f"{shortage['component']} | "
            f"{shortage['required_qty']:.2f} | "
            f"{shortage['available_qty']:.2f} | "
            f"{shortage['shortage_qty']:.2f} |"
        )
    lines.append("")
    lines.append("## What Phase 1 Does Not Include")
    lines.append("")
    lines.append("- demand forecasting")
    lines.append("- lead-time prediction")
    lines.append("- supplier risk scoring")
    lines.append("- conversational AI")
    lines.append("- machine-learned prioritization")
    lines.append("")
    lines.append("These become Phase 2 and later layers on top of the current engine.")
    lines.append("")
    return "\n".join(lines)

