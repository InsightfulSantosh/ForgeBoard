from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from .langchain_client import invoke_langchain_chat, parse_model_spec


FG_RE = re.compile(r"\bFG\d+\b", re.IGNORECASE)


@dataclass(frozen=True)
class AssistantAnswer:
    question: str
    mode: str
    intent: str
    answer: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PlanningAssistant:
    def answer(
        self,
        question: str,
        result: dict[str, Any],
        use_llm: bool = False,
        llm_model: str = "gemini-2.5-flash",
    ) -> AssistantAnswer:
        deterministic = self._deterministic_answer(question, result)
        if not use_llm:
            return deterministic

        try:
            llm_answer = self._answer_with_langchain(
                question,
                result,
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
                    f"Gemini LangChain request failed and deterministic fallback was used: {exc}"
                ),
            )

    def _deterministic_answer(self, question: str, result: dict[str, Any]) -> AssistantAnswer:
        intent = self._detect_intent(question)
        normalized = question.lower()

        if intent == "why_blocked":
            fg = self._extract_fg(question)
            answer = self._why_fg_blocked(fg, result)
        elif intent == "what_can_produce":
            answer = self._what_can_produce(result)
        elif intent == "critical_materials":
            answer = self._critical_materials(result)
        elif intent == "what_to_procure":
            answer = self._what_to_procure(result)
        elif intent == "priority_plan":
            answer = self._priority_plan(result)
        elif intent == "coverage_check" and "can" in normalized:
            fg = self._extract_fg(question)
            answer = self._coverage_check(fg, result)
        else:
            answer = self._general_summary(result)
            intent = "summary"

        return AssistantAnswer(
            question=question,
            mode="deterministic",
            intent=intent,
            answer=answer,
        )

    def _detect_intent(self, question: str) -> str:
        text = question.lower()
        if "why" in text and "block" in text:
            return "why_blocked"
        if ("what can" in text or "can i produce" in text or "produce today" in text) and "procure" not in text:
            return "what_can_produce"
        if "critical" in text and ("material" in text or "component" in text):
            return "critical_materials"
        if "procure" in text or "buy first" in text or "purchase first" in text:
            return "what_to_procure"
        if "prioritize" in text or "priority" in text or "produce first" in text:
            return "priority_plan"
        if "can" in text and self._extract_fg(question):
            return "coverage_check"
        return "summary"

    def _extract_fg(self, question: str) -> str | None:
        match = FG_RE.search(question)
        return match.group(0).upper() if match else None

    def _analysis_by_fg(self, result: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {row["fg"].upper(): row for row in result.get("analyses", [])}

    def _plan_by_fg(self, result: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {row["fg"].upper(): row for row in result.get("production_plan", [])}

    def _why_fg_blocked(self, fg: str | None, result: dict[str, Any]) -> str:
        if not fg:
            return "Specify a finished good code such as `FG01`."

        analyses = self._analysis_by_fg(result)
        analysis = analyses.get(fg)
        if not analysis:
            return f"`{fg}` is not present in the current workbook scenario."

        blockers = analysis.get("blocking_components", [])
        shortages = analysis.get("shortages", [])
        if analysis.get("recommended_build_qty", 0) > 0:
            return (
                f"`{fg}` is not fully blocked. The engine recommends building "
                f"{analysis['recommended_build_qty']} out of {int(round(analysis['net_demand_qty']))}."
            )

        top_shortages = []
        for item in shortages[:3]:
            top_shortages.append(
                f"{item['component']} short by {item['shortage_qty']:.2f}"
            )

        blocker_text = ", ".join(blockers[:5]) or "no blocker recorded"
        shortage_text = "; ".join(top_shortages) if top_shortages else "no shortage breakdown available"
        return (
            f"`{fg}` is blocked because its limiting components currently reduce build quantity to `0`. "
            f"Primary blockers: {blocker_text}. Top shortage details: {shortage_text}."
        )

    def _what_can_produce(self, result: dict[str, Any]) -> str:
        plan = result.get("production_plan", [])
        producible = [row for row in plan if row.get("planned_qty", 0) > 0]
        if not producible:
            top = plan[:3]
            if not top:
                return "No production plan is available in the current scenario."
            top_text = ", ".join(f"{row['fg']} (planned {row['planned_qty']})" for row in top)
            return (
                "No finished goods can be produced with current stock in this scenario. "
                f"Current ranked list is: {top_text}."
            )

        text = ", ".join(
            f"{row['fg']} ({row['planned_qty']} units)"
            for row in producible
        )
        return f"With current stock, the engine can produce: {text}."

    def _critical_materials(self, result: dict[str, Any]) -> str:
        shortages = result.get("aggregate_shortages", [])
        if not shortages:
            return "No aggregate shortages were found in the current scenario."

        top = shortages[:5]
        return "Most critical materials by aggregate shortage are: " + ", ".join(
            f"{row['component']} ({row['shortage_qty']:.2f})"
            for row in top
        ) + "."

    def _what_to_procure(self, result: dict[str, Any]) -> str:
        shortages = result.get("aggregate_shortages", [])
        if not shortages:
            return "There are no shortage-driven procurement recommendations in the current scenario."

        top = shortages[:5]
        return (
            "Procurement should start with the highest shortage components: "
            + ", ".join(
                f"{row['component']} (need {row['shortage_qty']:.2f})"
                for row in top
            )
            + "."
        )

    def _priority_plan(self, result: dict[str, Any]) -> str:
        plan = result.get("production_plan", [])
        if not plan:
            return "No production plan is available in the current scenario."

        top = plan[:4]
        return "Priority order from the current engine is: " + ", ".join(
            f"{row['fg']} (score {row['priority_score']:.2f}, plan {row['planned_qty']})"
            for row in top
        ) + "."

    def _coverage_check(self, fg: str | None, result: dict[str, Any]) -> str:
        if not fg:
            return "Specify a finished good code such as `FG01`."

        analyses = self._analysis_by_fg(result)
        analysis = analyses.get(fg)
        if not analysis:
            return f"`{fg}` is not present in the current workbook scenario."

        return (
            f"`{fg}` has net demand {int(round(analysis['net_demand_qty']))}, "
            f"max producible {analysis['max_producible_qty']}, "
            f"recommended build {analysis['recommended_build_qty']}, "
            f"coverage {analysis['coverage_ratio']:.0%}."
        )

    def _general_summary(self, result: dict[str, Any]) -> str:
        analyses = result.get("analyses", [])
        shortages = result.get("aggregate_shortages", [])
        if not analyses:
            return "No scenario analysis is available."

        blocked_count = sum(1 for row in analyses if row.get("recommended_build_qty", 0) == 0)
        top_fg = analyses[0]
        parts = [
            f"The scenario contains {len(analyses)} finished goods.",
            f"{blocked_count} currently have zero recommended build quantity.",
            (
                f"Highest-ranked FG is {top_fg['fg']} with priority score "
                f"{top_fg['priority_score']:.2f}."
            ),
        ]
        if shortages:
            parts.append(
                f"Top shortage is {shortages[0]['component']} at {shortages[0]['shortage_qty']:.2f} units."
            )
        return " ".join(parts)

    def _answer_with_langchain(
        self,
        question: str,
        result: dict[str, Any],
        model_spec: str,
    ) -> str:
        prompt = self._build_llm_prompt(question, result)
        config = parse_model_spec(model_spec)
        return invoke_langchain_chat(prompt, config)

    def _build_llm_prompt(self, question: str, result: dict[str, Any]) -> str:
        context = self._compact_context(result)
        return (
            "You are a manufacturing planning assistant.\n"
            "Answer only from the provided scenario data.\n"
            "Do not invent demand, inventory, or component values.\n"
            "If the answer is not present in the data, say so clearly.\n"
            "Be concise and business-facing.\n\n"
            f"Scenario data:\n{context}\n\n"
            f"User question: {question}"
        )

    def _compact_context(self, result: dict[str, Any]) -> str:
        compact = {
            "metadata": result.get("metadata", {}),
            "fg_analysis": [],
            "top_shortages": result.get("aggregate_shortages", [])[:10],
            "production_plan": result.get("production_plan", [])[:10],
        }
        for row in result.get("analyses", []):
            compact["fg_analysis"].append(
                {
                    "fg": row["fg"],
                    "net_demand_qty": row["net_demand_qty"],
                    "max_producible_qty": row["max_producible_qty"],
                    "recommended_build_qty": row["recommended_build_qty"],
                    "coverage_ratio": row["coverage_ratio"],
                    "limiting_components": row["limiting_components"][:10],
                    "blocking_components": row["blocking_components"][:5],
                    "top_shortages": row.get("shortages", [])[:5],
                }
            )
        return json.dumps(compact, indent=2)


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
