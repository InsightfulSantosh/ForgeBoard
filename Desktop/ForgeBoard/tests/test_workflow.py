from __future__ import annotations

import unittest

from bom_ai_engine.workflow import build_artifacts, build_summary_metrics


class WorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = {
            "metadata": {"workbook": "/tmp/demo.xlsx"},
            "analyses": [
                {
                    "fg": "FG01",
                    "demand_qty": 100,
                    "fg_on_hand_qty": 0,
                    "net_demand_qty": 100,
                    "max_producible_qty": 40,
                    "recommended_build_qty": 40,
                    "coverage_ratio": 0.4,
                    "can_fulfill_demand": False,
                    "limiting_components": ["COMP-A"],
                    "blocking_components": ["COMP-A"],
                    "priority_score": 42.0,
                    "priority_reason": "coverage=40%",
                },
                {
                    "fg": "FG02",
                    "demand_qty": 50,
                    "fg_on_hand_qty": 0,
                    "net_demand_qty": 50,
                    "max_producible_qty": 0,
                    "recommended_build_qty": 0,
                    "coverage_ratio": 0.0,
                    "can_fulfill_demand": False,
                    "limiting_components": ["COMP-B"],
                    "blocking_components": ["COMP-B"],
                    "priority_score": 10.0,
                    "priority_reason": "coverage=0%",
                },
            ],
            "production_plan": [
                {
                    "fg": "FG01",
                    "planned_qty": 40,
                    "unmet_qty": 60,
                    "priority_score": 42.0,
                    "rationale": "coverage=40%",
                },
                {
                    "fg": "FG02",
                    "planned_qty": 0,
                    "unmet_qty": 50,
                    "priority_score": 10.0,
                    "rationale": "coverage=0%",
                },
            ],
            "aggregate_shortages": [
                {
                    "component": "COMP-A",
                    "required_qty": 200.0,
                    "available_qty": 120.0,
                    "shortage_qty": 80.0,
                },
                {
                    "component": "COMP-B",
                    "required_qty": 50.0,
                    "available_qty": 0.0,
                    "shortage_qty": 50.0,
                },
            ],
        }

    def test_build_summary_metrics(self) -> None:
        metrics = build_summary_metrics(self.payload)
        self.assertEqual(metrics["fg_count"], 2)
        self.assertEqual(metrics["total_net_demand"], 150)
        self.assertEqual(metrics["total_planned_qty"], 40)
        self.assertEqual(metrics["blocked_fgs"], 1)
        self.assertEqual(metrics["top_fg"], "FG01")
        self.assertEqual(metrics["top_shortage_component"], "COMP-A")

    def test_build_artifacts(self) -> None:
        artifacts = build_artifacts(self.payload, assistant_answers=[])
        self.assertIn("scenario_summary.json", artifacts)
        self.assertIn("fg_analysis.csv", artifacts)
        self.assertIn("phase1_report.md", artifacts)
        self.assertIn("FG01", artifacts["fg_analysis.csv"])


if __name__ == "__main__":
    unittest.main()
