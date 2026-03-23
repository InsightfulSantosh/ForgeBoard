from __future__ import annotations

import unittest

from bom_ai_engine.reporting import build_phase1_report


class ReportingTests(unittest.TestCase):
    def test_phase1_report_contains_key_sections(self) -> None:
        payload = {
            "metadata": {
                "workbook": "/tmp/demo.xlsx",
                "demand_multiplier": 1.0,
                "generated_at_utc": "2026-03-22T00:00:00+00:00",
            },
            "analyses": [
                {
                    "fg": "FG01",
                    "net_demand_qty": 100,
                    "max_producible_qty": 25,
                    "recommended_build_qty": 25,
                    "coverage_ratio": 0.25,
                    "limiting_components": ["COMP-A"],
                }
            ],
            "production_plan": [
                {
                    "fg": "FG01",
                    "planned_qty": 25,
                    "unmet_qty": 75,
                    "priority_score": 42.5,
                }
            ],
            "aggregate_shortages": [
                {
                    "component": "COMP-A",
                    "required_qty": 200.0,
                    "available_qty": 50.0,
                    "shortage_qty": 150.0,
                }
            ],
        }

        report = build_phase1_report(payload)

        self.assertIn("# Phase 1 Production Feasibility Report", report)
        self.assertIn("FG01", report)
        self.assertIn("COMP-A", report)
        self.assertIn("What Phase 1 Does Not Include", report)


if __name__ == "__main__":
    unittest.main()
