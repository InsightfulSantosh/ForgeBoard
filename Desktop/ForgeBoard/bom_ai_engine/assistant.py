from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .langchain_client import invoke_langchain_chat, parse_model_spec


FG_RE = re.compile(r"\bFG\d+\b", re.IGNORECASE)
UNGROUNDED_LLM_PHRASES = (
    "as an ai",
    "i don't have access",
    "i do not have access",
    "cannot access the data",
    "can't access the data",
    "without access to the data",
)


@dataclass(frozen=True)
class AssistantAnswer:
    question: str
    mode: str
    intent: str
    answer: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QuestionInterpretation:
    intent: str
    fg: str | None = None
    component: str | None = None


class PlanningAssistant:
    def answer(
        self,
        question: str,
        result: dict[str, Any],
        use_llm: bool = False,
        llm_model: str = "gemini-2.5-flash",
    ) -> AssistantAnswer:
        interpretation = self._interpret_question(question, result)
        deterministic = self._deterministic_answer(question, result, interpretation)
        if not use_llm:
            return deterministic

        try:
            llm_answer = self._answer_with_langchain(
                question,
                result,
                deterministic,
                interpretation,
                model_spec=llm_model,
            )
            return AssistantAnswer(
                question=question,
                mode="langchain",
                intent=deterministic.intent,
                answer=llm_answer,
            )
        except Exception as exc:
            return AssistantAnswer(
                question=question,
                mode="deterministic-fallback",
                intent=deterministic.intent,
                answer=(
                    f"{deterministic.answer}\n\n"
                    "Gemini LangChain answer was unavailable or ungrounded, so ForgeBoard "
                    f"used the deterministic planner answer instead. Reason: {exc}"
                ),
            )

    def _deterministic_answer(
        self,
        question: str,
        result: dict[str, Any],
        interpretation: QuestionInterpretation,
    ) -> AssistantAnswer:
        intent = interpretation.intent
        normalized = question.lower()

        if intent == "why_blocked":
            answer = self._why_fg_blocked(interpretation.fg, result)
        elif intent == "what_can_produce":
            answer = self._what_can_produce(result)
        elif intent == "critical_materials":
            answer = self._critical_materials(result)
        elif intent == "what_to_procure":
            answer = self._what_to_procure(result)
        elif intent == "material_importance":
            answer = self._material_importance(result)
        elif intent == "component_detail":
            answer = self._component_detail(interpretation.component, result)
        elif intent == "priority_plan":
            answer = self._priority_plan(result)
        elif intent == "coverage_check" and any(
            token in normalized for token in ("can", "coverage", "fulfill", "build", "make")
        ):
            answer = self._coverage_check(interpretation.fg, result)
        else:
            answer = self._general_summary(result)
            intent = "summary"

        return AssistantAnswer(
            question=question,
            mode="deterministic",
            intent=intent,
            answer=answer,
        )

    def _interpret_question(self, question: str, result: dict[str, Any]) -> QuestionInterpretation:
        fg = self._extract_fg(question)
        component = self._extract_component(question, result)
        return QuestionInterpretation(
            intent=self._detect_intent(question, fg=fg, component=component),
            fg=fg,
            component=component,
        )

    def _detect_intent(
        self,
        question: str,
        fg: str | None = None,
        component: str | None = None,
    ) -> str:
        text = question.lower()
        if fg and any(
            phrase in text for phrase in ("why", "blocked", "blocking", "cannot make", "can't make")
        ):
            return "why_blocked"
        if "why" in text and "block" in text:
            return "why_blocked"
        if ("what can" in text or "can i produce" in text or "produce today" in text) and "procure" not in text:
            return "what_can_produce"
        if any(
            phrase in text
            for phrase in (
                "most important raw material",
                "important raw material",
                "important material",
                "importance by use",
                "usage importance",
                "used in many",
                "shared material",
            )
        ):
            return "material_importance"
        if component and any(
            phrase in text
            for phrase in (
                "important",
                "use",
                "used in",
                "critical",
                "short",
                "stock",
                "available",
                "blocking",
                "limiting",
            )
        ):
            return "component_detail"
        if "critical" in text and ("material" in text or "component" in text):
            return "critical_materials"
        if "procure" in text or "buy first" in text or "purchase first" in text or "order first" in text:
            return "what_to_procure"
        if "prioritize" in text or "priority" in text or "produce first" in text or "lead fg" in text:
            return "priority_plan"
        if fg and any(token in text for token in ("can", "coverage", "fulfill", "build", "make")):
            return "coverage_check"
        if component:
            return "component_detail"
        return "summary"

    def _extract_fg(self, question: str) -> str | None:
        match = FG_RE.search(question)
        return match.group(0).upper() if match else None

    def _extract_component(self, question: str, result: dict[str, Any]) -> str | None:
        question_upper = question.upper()
        for component in sorted(self._known_components(result), key=len, reverse=True):
            if component.upper() in question_upper:
                return component
        return None

    def _analysis_by_fg(self, result: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {row["fg"].upper(): row for row in result.get("analyses", [])}

    def _plan_by_fg(self, result: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {row["fg"].upper(): row for row in result.get("production_plan", [])}

    def _aggregate_shortage_by_component(self, result: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {
            row["component"].upper(): row
            for row in result.get("aggregate_shortages", [])
            if row.get("component")
        }

    def _usage_by_component(self, result: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {
            row["component"].upper(): row
            for row in result.get("material_usage_ranking", [])
            if row.get("component")
        }

    def _known_components(self, result: dict[str, Any]) -> list[str]:
        seen: set[str] = set()
        components: list[str] = []

        def _add(component: str | None) -> None:
            if not component:
                return
            upper = component.upper()
            if upper in seen:
                return
            seen.add(upper)
            components.append(component)

        for row in result.get("aggregate_shortages", []):
            _add(row.get("component"))
        for row in result.get("material_usage_ranking", []):
            _add(row.get("component"))
        for analysis in result.get("analyses", []):
            for component in analysis.get("limiting_components", []):
                _add(component)
            for component in analysis.get("blocking_components", []):
                _add(component)
            for shortage in analysis.get("shortages", []):
                _add(shortage.get("component"))

        return components

    def _why_fg_blocked(self, fg: str | None, result: dict[str, Any]) -> str:
        if not fg:
            return "Specify a finished good code such as `FG01`."

        analyses = self._analysis_by_fg(result)
        analysis = analyses.get(fg)
        if not analysis:
            return f"`{fg}` is not present in the current workbook scenario."

        blockers = analysis.get("blocking_components", [])
        limiting = analysis.get("limiting_components", [])
        shortages = analysis.get("shortages", [])
        planned_qty = int(analysis.get("recommended_build_qty", 0))
        net_demand = int(round(analysis.get("net_demand_qty", 0)))
        if planned_qty > 0:
            blocker_text = ", ".join(blockers) or "no blocker recorded"
            return (
                f"`{fg}` is partially constrained, not fully blocked. The engine recommends building "
                f"{planned_qty} out of {net_demand}. Current blocking components are: {blocker_text}."
            )

        top_shortages = [
            f"{item['component']} short by {item['shortage_qty']:.2f}"
            for item in shortages
            if item.get("component")
        ]

        blocker_text = ", ".join(blockers) or "no blocker recorded"
        limiting_text = ", ".join(limiting) or "no limiting component recorded"
        shortage_text = "; ".join(top_shortages) if top_shortages else "no shortage breakdown available"
        return (
            f"`{fg}` is blocked because its limiting components currently reduce build quantity to `0`. "
            f"Limiting components: {limiting_text}. Primary blockers: {blocker_text}. "
            f"Top shortage details: {shortage_text}."
        )

    def _what_can_produce(self, result: dict[str, Any]) -> str:
        plan = result.get("production_plan", [])
        producible = [row for row in plan if row.get("planned_qty", 0) > 0]
        if not producible:
            if not plan:
                return "No production plan is available in the current scenario."
            top_text = ", ".join(f"{row['fg']} (planned {row['planned_qty']})" for row in plan)
            return (
                "No finished goods can be produced with current stock in this scenario. "
                f"Current ranked list is: {top_text}."
            )

        text = ", ".join(
            f"{row['fg']} ({row['planned_qty']} units, unmet {row.get('unmet_qty', 0)})"
            for row in producible
        )
        return f"With current stock, the engine can produce: {text}."

    def _critical_materials(self, result: dict[str, Any]) -> str:
        shortages = result.get("aggregate_shortages", [])
        ranking = result.get("material_usage_ranking", [])
        if not shortages:
            return "No aggregate shortages were found in the current scenario."

        shortage_text = ", ".join(
            f"{row['component']} ({row['shortage_qty']:.2f})"
            for row in shortages
        )
        if not ranking:
            return f"Critical materials by aggregate shortage are: {shortage_text}."

        usage_text = ", ".join(
            f"{row['component']} (used in {row['used_in_fg_count']} FGs, score {row['usage_importance_score']:.2f})"
            for row in ranking
        )
        return (
            f"Critical materials by aggregate shortage are: {shortage_text}. "
            f"Strategic importance by use is: {usage_text}."
        )

    def _what_to_procure(self, result: dict[str, Any]) -> str:
        shortages = result.get("aggregate_shortages", [])
        ranking = result.get("material_usage_ranking", [])
        if not shortages:
            return "There are no shortage-driven procurement recommendations in the current scenario."

        answer = (
            "Shortage-driven procurement ranking is: "
            + ", ".join(
                f"{row['component']} (need {row['shortage_qty']:.2f})"
                for row in shortages
            )
        )
        if ranking:
            answer += (
                ". If you want the materials with the widest cross-FG impact, importance by use is: "
                + ", ".join(
                    f"{row['component']} (used in {row['used_in_fg_count']} FGs, score {row['usage_importance_score']:.2f})"
                    for row in ranking
                )
            )
        return answer + "."

    def _material_importance(self, result: dict[str, Any]) -> str:
        ranking = result.get("material_usage_ranking", [])
        if not ranking:
            return "No material-usage ranking is available in the current scenario."

        lead = ranking[0]
        ranking_text = ", ".join(
            f"{row['component']} (used in {row['used_in_fg_count']} FGs, required {row['total_required_qty']:.2f}, score {row['usage_importance_score']:.2f})"
            for row in ranking
        )
        return (
            f"The most important raw material by cross-FG use is `{lead['component']}`. "
            f"Full usage-based ranking is: {ranking_text}."
        )

    def _component_detail(self, component: str | None, result: dict[str, Any]) -> str:
        if not component:
            return "Specify a component or raw-material code such as `COMP-A`."

        aggregate_row = self._aggregate_shortage_by_component(result).get(component.upper())
        usage_row = self._usage_by_component(result).get(component.upper())

        limiting_fgs: list[str] = []
        blocking_fgs: list[str] = []
        shortage_details: list[str] = []
        for analysis in result.get("analyses", []):
            fg = str(analysis.get("fg", ""))
            if component in analysis.get("limiting_components", []):
                limiting_fgs.append(fg)
            if component in analysis.get("blocking_components", []):
                blocking_fgs.append(fg)
            for shortage in analysis.get("shortages", []):
                if shortage.get("component", "").upper() == component.upper():
                    shortage_details.append(
                        f"{fg} (short {float(shortage.get('shortage_qty', 0.0)):.2f})"
                    )

        if not aggregate_row and not usage_row and not limiting_fgs and not blocking_fgs and not shortage_details:
            return f"`{component}` is not present in the current scenario data."

        parts: list[str] = []
        if aggregate_row:
            required = float(aggregate_row.get("required_qty", 0.0))
            available = float(aggregate_row.get("available_qty", 0.0))
            shortage = float(aggregate_row.get("shortage_qty", 0.0))
            parts.append(
                f"`{component}` has aggregate required quantity {required:.2f}, available quantity {available:.2f}, "
                f"and shortage {shortage:.2f}."
            )
        elif usage_row:
            parts.append(f"`{component}` is present in the scenario and currently has no aggregate shortage.")

        if usage_row:
            used_in_fgs = ", ".join(usage_row.get("used_in_fgs", [])) or "none recorded"
            parts.append(
                f"It is used in {int(usage_row.get('used_in_fg_count', 0))} finished goods ({used_in_fgs}), "
                f"planned consumption is {float(usage_row.get('planned_consumption_qty', 0.0)):.2f}, "
                f"and usage importance score is {float(usage_row.get('usage_importance_score', 0.0)):.2f}."
            )

        if limiting_fgs:
            parts.append(f"It is a limiting component for: {', '.join(limiting_fgs)}.")
        if blocking_fgs:
            parts.append(f"It appears in blocking components for: {', '.join(blocking_fgs)}.")
        if shortage_details:
            parts.append(f"FG shortage detail: {', '.join(shortage_details)}.")

        return " ".join(parts)

    def _priority_plan(self, result: dict[str, Any]) -> str:
        plan = result.get("production_plan", [])
        if not plan:
            return "No production plan is available in the current scenario."

        return "Priority order from the current engine is: " + ", ".join(
            f"{row['fg']} (score {row['priority_score']:.2f}, plan {row['planned_qty']})"
            for row in plan
        ) + "."

    def _coverage_check(self, fg: str | None, result: dict[str, Any]) -> str:
        if not fg:
            return "Specify a finished good code such as `FG01`."

        analyses = self._analysis_by_fg(result)
        analysis = analyses.get(fg)
        if not analysis:
            return f"`{fg}` is not present in the current workbook scenario."

        net_demand = int(round(analysis["net_demand_qty"]))
        recommended = int(analysis["recommended_build_qty"])
        unmet = max(net_demand - recommended, 0)
        return (
            f"`{fg}` has net demand {net_demand}, "
            f"max producible {analysis['max_producible_qty']}, "
            f"recommended build {recommended}, "
            f"coverage {analysis['coverage_ratio']:.0%}, "
            f"and unmet demand {unmet}."
        )

    def _general_summary(self, result: dict[str, Any]) -> str:
        analyses = result.get("analyses", [])
        shortages = result.get("aggregate_shortages", [])
        plan = result.get("production_plan", [])
        usage_ranking = result.get("material_usage_ranking", [])
        if not analyses:
            return "No scenario analysis is available."

        blocked_count = sum(1 for row in analyses if row.get("recommended_build_qty", 0) == 0)
        fully_coverable = sum(1 for row in analyses if row.get("can_fulfill_demand"))
        total_net_demand = int(round(sum(float(row.get("net_demand_qty", 0.0)) for row in analyses)))
        total_planned = sum(int(row.get("planned_qty", 0)) for row in plan)
        top_fg = analyses[0]
        parts = [
            f"The scenario contains {len(analyses)} finished goods with total net demand {total_net_demand} and planned build {total_planned}.",
            f"{blocked_count} currently have zero recommended build quantity and {fully_coverable} are fully coverable.",
            (
                f"Highest-ranked FG is {top_fg['fg']} with priority score "
                f"{top_fg['priority_score']:.2f} and recommended build {top_fg['recommended_build_qty']}."
            ),
        ]
        if shortages:
            parts.append(
                f"Top shortage is {shortages[0]['component']} at {shortages[0]['shortage_qty']:.2f} units."
            )
        if usage_ranking:
            parts.append(
                f"Most widely leveraged raw material is {usage_ranking[0]['component']} with usage importance score "
                f"{usage_ranking[0]['usage_importance_score']:.2f}."
            )
        return " ".join(parts)

    def _answer_with_langchain(
        self,
        question: str,
        result: dict[str, Any],
        deterministic: AssistantAnswer,
        interpretation: QuestionInterpretation,
        model_spec: str,
    ) -> str:
        prompt = self._build_llm_prompt(question, result, deterministic, interpretation)
        config = parse_model_spec(model_spec)
        raw_answer = invoke_langchain_chat(prompt, config)
        return self._finalize_llm_answer(raw_answer, deterministic, interpretation)

    def _build_llm_prompt(
        self,
        question: str,
        result: dict[str, Any],
        deterministic: AssistantAnswer,
        interpretation: QuestionInterpretation,
    ) -> str:
        context = self._compact_context(result, interpretation)
        return (
            "You are ForgeBoard, a manufacturing planning assistant.\n"
            "Answer only from the provided scenario data and deterministic engine answer.\n"
            "Do not invent demand, inventory, FG, or component values.\n"
            "Do not contradict the deterministic engine answer.\n"
            "If the answer is not present in the data, say so clearly.\n"
            "Be concise, business-facing, and operational.\n"
            "Return this structure exactly:\n"
            "Direct answer: <1-3 sentences>\n"
            "Grounded details:\n"
            "- <bullet>\n"
            "- <bullet>\n\n"
            f"Question interpretation:\n{json.dumps(asdict(interpretation), indent=2)}\n\n"
            f"Deterministic engine answer:\n{deterministic.answer}\n\n"
            f"Scenario data:\n{context}\n\n"
            f"User question: {question}"
        )

    def _compact_context(self, result: dict[str, Any], interpretation: QuestionInterpretation) -> str:
        overview = self._summary_snapshot(result)
        compact = {
            "metadata": {
                **result.get("metadata", {}),
                "workbook_basename": Path(str(result.get("metadata", {}).get("workbook", ""))).name,
            },
            "scenario_overview": overview,
            "question_focus": asdict(interpretation),
            "fg_analysis": [],
            "aggregate_shortages": result.get("aggregate_shortages", []),
            "material_usage_ranking": result.get("material_usage_ranking", []),
            "production_plan": result.get("production_plan", []),
        }
        for row in result.get("analyses", []):
            compact["fg_analysis"].append(
                {
                    "fg": row["fg"],
                    "net_demand_qty": row["net_demand_qty"],
                    "max_producible_qty": row["max_producible_qty"],
                    "recommended_build_qty": row["recommended_build_qty"],
                    "coverage_ratio": row["coverage_ratio"],
                    "priority_score": row.get("priority_score"),
                    "limiting_components": row["limiting_components"],
                    "blocking_components": row["blocking_components"],
                    "shortages": row.get("shortages", []),
                }
            )
        if interpretation.fg:
            compact["selected_fg"] = self._analysis_by_fg(result).get(interpretation.fg)
            compact["selected_fg_plan"] = self._plan_by_fg(result).get(interpretation.fg)
        if interpretation.component:
            compact["selected_component"] = self._component_context(interpretation.component, result)
        return json.dumps(compact, indent=2)

    def _summary_snapshot(self, result: dict[str, Any]) -> dict[str, Any]:
        analyses = result.get("analyses", [])
        plan = result.get("production_plan", [])
        shortages = result.get("aggregate_shortages", [])
        usage_ranking = result.get("material_usage_ranking", [])
        return {
            "fg_count": len(analyses),
            "blocked_fgs": sum(1 for row in analyses if int(row.get("recommended_build_qty", 0)) == 0),
            "fully_coverable_fgs": sum(1 for row in analyses if row.get("can_fulfill_demand")),
            "total_net_demand": int(round(sum(float(row.get("net_demand_qty", 0.0)) for row in analyses))),
            "total_planned_qty": sum(int(row.get("planned_qty", 0)) for row in plan),
            "lead_fg": analyses[0]["fg"] if analyses else None,
            "top_shortage_component": shortages[0]["component"] if shortages else None,
            "top_usage_material": usage_ranking[0]["component"] if usage_ranking else None,
        }

    def _component_context(self, component: str, result: dict[str, Any]) -> dict[str, Any]:
        aggregate_row = self._aggregate_shortage_by_component(result).get(component.upper())
        usage_row = self._usage_by_component(result).get(component.upper())
        impacted_fgs: list[dict[str, Any]] = []
        for analysis in result.get("analyses", []):
            fg_shortage = next(
                (
                    item
                    for item in analysis.get("shortages", [])
                    if item.get("component", "").upper() == component.upper()
                ),
                None,
            )
            if (
                component in analysis.get("limiting_components", [])
                or component in analysis.get("blocking_components", [])
                or fg_shortage
            ):
                impacted_fgs.append(
                    {
                        "fg": analysis.get("fg"),
                        "is_limiting": component in analysis.get("limiting_components", []),
                        "is_blocking": component in analysis.get("blocking_components", []),
                        "fg_shortage": fg_shortage,
                    }
                )
        return {
            "component": component,
            "aggregate_shortage": aggregate_row,
            "material_usage": usage_row,
            "impacted_finished_goods": impacted_fgs,
        }

    def _finalize_llm_answer(
        self,
        raw_answer: str,
        deterministic: AssistantAnswer,
        interpretation: QuestionInterpretation,
    ) -> str:
        answer = str(raw_answer).strip()
        if len(answer) < 24:
            raise ValueError("empty LLM answer")

        normalized = answer.lower()
        if any(phrase in normalized for phrase in UNGROUNDED_LLM_PHRASES):
            raise ValueError("ungrounded LLM answer")

        if "grounded details:" not in normalized:
            answer = (
                f"Direct answer: {answer}\n\n"
                f"Grounded details:\n- {deterministic.answer}"
            )
        elif deterministic.answer not in answer:
            answer = f"{answer}\n- Engine baseline: {deterministic.answer}"

        upper_answer = answer.upper()
        if interpretation.fg and interpretation.fg not in upper_answer:
            answer = f"{answer}\n- Focus FG: {interpretation.fg}"
        if interpretation.component and interpretation.component.upper() not in upper_answer:
            answer = f"{answer}\n- Focus component: {interpretation.component}"

        return answer.strip()


def build_chat_markdown(answers: list[AssistantAnswer]) -> str:
    lines = ["# Phase 2 Conversational Assistant Output", ""]
    for index, item in enumerate(answers, start=1):
        lines.append(f"## Q{index}")
        lines.append("")
        lines.append(f"**Question:** {item.question}")
        lines.append("")
        lines.append(f"**Mode:** {item.mode}")
        lines.append("")
        lines.append(f"**Intent:** {item.intent}")
        lines.append("")
        lines.append(item.answer)
        lines.append("")
    return "\n".join(lines)
