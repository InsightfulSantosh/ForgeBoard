from __future__ import annotations

import unittest

from bom_ai_engine.assistant import PlanningAssistant


class AssistantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = {
            "metadata": {"workbook": "/tmp/demo.xlsx"},
            "analyses": [
                {
                    "fg": "FG01",
                    "net_demand_qty": 100,
                    "max_producible_qty": 0,
                    "recommended_build_qty": 0,
                    "coverage_ratio": 0.0,
                    "priority_score": 10.0,
                    "blocking_components": ["COMP-A", "COMP-B"],
                    "limiting_components": ["COMP-A"],
                    "shortages": [
                        {
                            "component": "COMP-A",
                            "shortage_qty": 150.0,
                        },
                        {
                            "component": "COMP-B",
                            "shortage_qty": 90.0,
                        },
                    ],
                },
                {
                    "fg": "FG02",
                    "net_demand_qty": 40,
                    "max_producible_qty": 15,
                    "recommended_build_qty": 15,
                    "coverage_ratio": 0.375,
                    "priority_score": 25.0,
                    "blocking_components": ["COMP-C"],
                    "limiting_components": ["COMP-C"],
                    "shortages": [],
                },
            ],
            "production_plan": [
                {
                    "fg": "FG02",
                    "planned_qty": 15,
                    "unmet_qty": 25,
                    "priority_score": 25.0,
                },
                {
                    "fg": "FG01",
                    "planned_qty": 0,
                    "unmet_qty": 100,
                    "priority_score": 10.0,
                },
            ],
            "aggregate_shortages": [
                {
                    "component": "COMP-A",
                    "shortage_qty": 150.0,
                },
                {
                    "component": "COMP-Z",
                    "shortage_qty": 100.0,
                },
            ],
        }
        self.assistant = PlanningAssistant()

    def test_why_blocked_question(self) -> None:
        answer = self.assistant.answer("Why is FG01 blocked?", self.result)
        self.assertEqual(answer.intent, "why_blocked")
        self.assertIn("FG01", answer.answer)
        self.assertIn("COMP-A", answer.answer)

    def test_producible_question(self) -> None:
        answer = self.assistant.answer("What can I produce today?", self.result)
        self.assertEqual(answer.intent, "what_can_produce")
        self.assertIn("FG02", answer.answer)
        self.assertIn("15", answer.answer)

    def test_procurement_question(self) -> None:
        answer = self.assistant.answer("Which material should I procure first?", self.result)
        self.assertEqual(answer.intent, "what_to_procure")
        self.assertIn("COMP-A", answer.answer)

    def test_llm_mode_falls_back_cleanly_when_langchain_is_unavailable(self) -> None:
        answer = self.assistant.answer(
            "Why is FG01 blocked?",
            self.result,
            use_llm=True,
            llm_model="gemini-2.5-flash",
        )
        self.assertEqual(answer.mode, "deterministic-fallback")
        self.assertIn("Gemini LangChain", answer.answer)



if __name__ == "__main__":
    unittest.main()
