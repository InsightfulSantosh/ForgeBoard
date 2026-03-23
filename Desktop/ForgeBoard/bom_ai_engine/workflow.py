from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

from .assistant import PlanningAssistant, build_chat_markdown
from .engine import ProductionPlanner, apply_scenario, load_workbook_data
from .reporting import build_phase1_report


@dataclass(frozen=True)
class ScenarioExecution:
    result: dict[str, Any]
    artifacts: dict[str, str]
    assistant_answers: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_scenario(
    workbook_path: str | Path,
    demand_multiplier: float = 1.0,
    procurement: dict[str, float] | None = None,
    priority_hints: dict[str, dict[str, float]] | None = None,
    questions: list[str] | None = None,
    use_llm: bool = False,
    llm_model: str = "gemini-2.5-flash",
) -> ScenarioExecution:
    workbook = Path(workbook_path).expanduser().resolve()
    raw_data = load_workbook_data(workbook)
    scenario_data = apply_scenario(
        raw_data,
        demand_multiplier=demand_multiplier,
        procurement=procurement or {},
    )

    planner = ProductionPlanner()
    result = planner.run(
        scenario_data,
        priority_hints=priority_hints or {},
        metadata={
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "workbook": str(workbook),
            "demand_multiplier": demand_multiplier,
            "procurement_overrides": procurement or {},
            "priority_hints_supplied": bool(priority_hints),
        },
    )
    payload = result.to_dict()

    assistant_answers: list[dict[str, Any]] = []
    if questions:
        assistant = PlanningAssistant()
        assistant_answers = [
            assistant.answer(
                question,
                payload,
                use_llm=use_llm,
                llm_model=llm_model,
            ).to_dict()
            for question in questions
        ]

    artifacts = build_artifacts(payload, assistant_answers)
    return ScenarioExecution(
        result=payload,
        artifacts=artifacts,
        assistant_answers=assistant_answers,
    )


def build_artifacts(
    payload: dict[str, Any],
    assistant_answers: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    answers = assistant_answers or []
    artifacts = {
        "scenario_summary.json": json.dumps(payload, indent=2),
        "fg_analysis.csv": _rows_to_csv(
            [
                "fg",
                "demand_qty",
                "fg_on_hand_qty",
                "net_demand_qty",
                "max_producible_qty",
                "recommended_build_qty",
                "coverage_ratio",
                "can_fulfill_demand",
                "limiting_components",
                "blocking_components",
                "priority_score",
                "priority_reason",
            ],
            [
                {
                    **row,
                    "limiting_components": ",".join(row["limiting_components"]),
                    "blocking_components": ",".join(row["blocking_components"]),
                }
                for row in payload.get("analyses", [])
            ],
        ),
        "production_plan.csv": _rows_to_csv(
            ["fg", "planned_qty", "unmet_qty", "priority_score", "rationale"],
            payload.get("production_plan", []),
        ),
        "material_shortages.csv": _rows_to_csv(
            ["component", "required_qty", "available_qty", "shortage_qty"],
            payload.get("aggregate_shortages", []),
        ),
        "material_usage_ranking.csv": _rows_to_csv(
            [
                "component",
                "used_in_fg_count",
                "used_in_fgs",
                "total_required_qty",
                "planned_consumption_qty",
                "available_qty",
                "shortage_qty",
                "usage_importance_score",
            ],
            [
                {
                    **row,
                    "used_in_fgs": ",".join(row["used_in_fgs"]),
                }
                for row in payload.get("material_usage_ranking", [])
            ],
        ),
        "phase1_report.md": build_phase1_report(payload),
    }

    if answers:
        artifacts["phase2_chat.md"] = build_chat_markdown(
            [_answer_dict_to_object(item) for item in answers]
        )
        artifacts["phase2_chat.json"] = json.dumps(answers, indent=2)

    return artifacts


def build_summary_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    analyses = payload.get("analyses", [])
    plan = payload.get("production_plan", [])
    shortages = payload.get("aggregate_shortages", [])

    total_net_demand = sum(float(row.get("net_demand_qty", 0.0)) for row in analyses)
    total_planned_qty = sum(int(row.get("planned_qty", 0)) for row in plan)
    fulfillable_fgs = sum(1 for row in analyses if row.get("can_fulfill_demand"))
    blocked_fgs = sum(1 for row in analyses if int(row.get("recommended_build_qty", 0)) == 0)
    total_shortage_qty = sum(float(row.get("shortage_qty", 0.0)) for row in shortages)

    top_fg = analyses[0]["fg"] if analyses else None
    top_shortage_component = shortages[0]["component"] if shortages else None

    return {
        "fg_count": len(analyses),
        "total_net_demand": int(round(total_net_demand)),
        "total_planned_qty": total_planned_qty,
        "fulfillable_fgs": fulfillable_fgs,
        "blocked_fgs": blocked_fgs,
        "total_shortage_qty": round(total_shortage_qty, 2),
        "top_fg": top_fg,
        "top_shortage_component": top_shortage_component,
    }


def _rows_to_csv(fieldnames: list[str], rows: list[dict[str, Any]]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in fieldnames})
    return buffer.getvalue()


def _answer_dict_to_object(answer: dict[str, Any]):
    from .assistant import AssistantAnswer

    return AssistantAnswer(
        question=str(answer.get("question", "")),
        mode=str(answer.get("mode", "")),
        intent=str(answer.get("intent", "")),
        answer=str(answer.get("answer", "")),
    )
