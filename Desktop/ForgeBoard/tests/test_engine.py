from __future__ import annotations

import unittest

from bom_ai_engine.engine import ProductionPlanner, apply_scenario
from bom_ai_engine.models import DemandLine, WorkbookData


class ProductionPlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = WorkbookData(
            demands=[
                DemandLine(
                    organization_id="103",
                    fg="FG1",
                    demand_qty=10,
                    fg_on_hand_qty=0,
                    net_demand_qty=10,
                ),
                DemandLine(
                    organization_id="103",
                    fg="FG2",
                    demand_qty=4,
                    fg_on_hand_qty=0,
                    net_demand_qty=4,
                ),
            ],
            bom={
                "FG1": {"COMP-A": 2, "COMP-B": 1},
                "FG2": {"COMP-A": 1},
            },
            inventory={
                "COMP-A": 9,
                "COMP-B": 5,
            },
        )

    def test_feasibility_and_shortages_are_calculated(self) -> None:
        planner = ProductionPlanner()
        result = planner.run(self.data)
        analyses = {analysis.fg: analysis for analysis in result.analyses}

        fg1 = analyses["FG1"]
        self.assertEqual(fg1.max_producible_qty, 4)
        self.assertEqual(fg1.recommended_build_qty, 4)
        self.assertFalse(fg1.can_fulfill_demand)
        self.assertEqual(fg1.limiting_components, ["COMP-A"])
        self.assertEqual(fg1.shortages[0].component, "COMP-A")
        self.assertEqual(round(fg1.shortages[0].shortage_qty, 2), 11.0)

    def test_priority_and_allocation_use_shared_inventory(self) -> None:
        planner = ProductionPlanner()
        result = planner.run(self.data)
        plan = {row.fg: row for row in result.production_plan}

        self.assertEqual(plan["FG2"].planned_qty, 4)
        self.assertEqual(plan["FG1"].planned_qty, 2)
        self.assertEqual(plan["FG1"].unmet_qty, 8)
        self.assertEqual(round(result.remaining_inventory["COMP-A"], 2), 1.0)

    def test_procurement_scenario_changes_output(self) -> None:
        planner = ProductionPlanner()
        scenario = apply_scenario(self.data, demand_multiplier=1.0, procurement={"COMP-A": 20})
        result = planner.run(scenario)
        analyses = {analysis.fg: analysis for analysis in result.analyses}

        self.assertEqual(analyses["FG1"].max_producible_qty, 5)
        self.assertTrue(analyses["FG2"].can_fulfill_demand)


if __name__ == "__main__":
    unittest.main()
