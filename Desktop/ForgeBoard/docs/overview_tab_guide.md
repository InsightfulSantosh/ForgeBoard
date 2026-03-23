# Overview Tab Guide

This note explains what the `Overview` tab in ForgeBoard shows and how each number is calculated.

## Purpose

The `Overview` tab is the planner's high-level scenario summary. It combines:

- summary KPIs above the tabs
- a finished-goods feasibility table
- an aggregate shortages table
- a short decision snapshot

The values come from the scenario payload produced by the planning engine:

- `analyses`
- `production_plan`
- `aggregate_shortages`
- summary metrics derived from those collections

## Data Sources

The `Overview` experience is built from:

- `result["analyses"]`: FG-level planning analysis
- `result["production_plan"]`: planned allocation after priority ranking
- `result["aggregate_shortages"]`: component shortages across total scenario demand
- `build_summary_metrics(...)`: compact KPI rollup

## Client-Friendly Explanation

`The Overview tab gives management and planners a fast summary of the current production position. It shows what can be built, what is blocked, which materials are creating pressure, and what the system recommends focusing on first.`

### Simple explanation of the top summary numbers

- `Finished Goods`: how many finished products are being evaluated in this scenario
- `Net Demand`: how much demand is still open after subtracting stock already available
- `Planned Build`: how many units the system recommends producing now
- `Blocked FGs`: how many finished goods cannot be produced right now
- `Top Shortage`: the material causing the biggest shortage pressure
- `Lead FG`: the finished good the system currently wants the planner to focus on first
- `Total shortage volume`: the total missing material quantity across all shortages
- `FGs fully coverable`: how many finished goods can be fully supplied with current stock

### Simple explanation of the Production Posture table

`This table shows each finished good one by one and tells the planner how strong or weak its current production position is.`

- `Net Demand`: how much still needs to be produced
- `Max Producible`: the maximum the plant could make with today's available materials
- `Recommended Build`: what ForgeBoard suggests building now
- `Coverage`: how much of the open demand can be covered immediately
- `Priority Score`: how strongly the system recommends focusing on that item

### Simple explanation of the Procurement Pressure table

`This table shows which materials are creating the most pressure across the whole plan.`

- `Required Qty`: how much of that material is needed
- `Available Qty`: how much is currently in stock
- `Shortage Qty`: how much is missing

### Simple explanation of the Decision Snapshot

`This is the quick management summary. It tells you the top recommended finished good, the main material problems, and which workbook the scenario came from.`

## Summary Band Metrics

### Finished Goods

Formula:

```text
Finished Goods = count(analyses)
```

Meaning:

Number of finished goods included in the current scenario result.

### Net Demand

Formula:

```text
Net Demand = round(sum(net_demand_qty for each FG))
```

Meaning:

Total open demand after subtracting finished-good stock already on hand.

### Planned Build

Formula:

```text
Planned Build = sum(planned_qty for each FG in production_plan)
```

Meaning:

Total units the allocation step recommends building now.

### Blocked FGs

Formula:

```text
Blocked FGs = count(FGs where recommended_build_qty == 0)
```

Meaning:

Finished goods that cannot be built at all in the current scenario.

### Top Shortage

Formula:

```text
Top Shortage = aggregate_shortages[0].component
```

Meaning:

The component with the largest aggregate shortage quantity.

Note:

The aggregate shortages list is sorted descending by `shortage_qty`, so the first row is the highest procurement pressure item.

### Lead FG

Formula:

```text
Lead FG = analyses[0].fg
```

Meaning:

The top-ranked finished good after ForgeBoard scores and sorts the FG analyses by planning priority.

### Total Shortage Volume

Formula:

```text
Total shortage volume = sum(shortage_qty for each component in aggregate_shortages)
```

Meaning:

The total missing component quantity across all shortage lines in the current scenario.

### FGs Fully Coverable

Formula:

```text
FGs fully coverable = count(FGs where can_fulfill_demand is true)
```

Meaning:

Number of finished goods for which ForgeBoard can cover the full current net demand.

## Production Posture Table

This table gives one row per finished good.

### FG

Meaning:

The finished-good code.

### Net Demand

Formula:

```text
Net Demand = max((Demand Qty x demand_multiplier) - FG On-hand Qty, 0)
```

Meaning:

Demand still needing production after applying the scenario multiplier and subtracting FG stock already available.

### Max Producible

Formula:

```text
possible units from a component = available_qty / qty_per_fg

Max Producible = floor(min(possible units across all required components))
```

Meaning:

Maximum whole units that can be built if the FG is considered in isolation against current inventory.

### Recommended Build

Formula:

```text
Recommended Build = min(Max Producible, floor(Net Demand))
```

Meaning:

How many units ForgeBoard recommends building for that FG before shared-inventory allocation is applied across the whole plan.

### Coverage

Formula:

```text
Coverage = Recommended Build / floor(Net Demand)
```

Special case:

```text
If Net Demand == 0, Coverage = 1.0
```

Meaning:

Percentage of current net demand that can be covered immediately.

### Priority Score

Formula:

```text
Priority Score =
100 x (
  0.40 x coverage_signal +
  0.15 x demand_signal +
  0.10 x efficiency_signal +
  0.10 x scarcity_signal +
  0.15 x business_priority +
  0.05 x margin_score +
  0.05 x service_level_weight
)
```

Meaning:

Composite ranking score used to sort finished goods before final shared-inventory allocation.

Signal definitions:

- `coverage_signal`: FG coverage ratio
- `demand_signal`: min-max scaled net demand
- `efficiency_signal`: min-max scaled `1 / total BOM quantity`
- `scarcity_signal`: inverse min-max scaled shortage ratio
- `business_priority`: optional hint from priority JSON, clipped to `0..1`
- `margin_score`: optional hint from priority JSON, clipped to `0..1`
- `service_level_weight`: optional hint from priority JSON, clipped to `0..1`

## Procurement Pressure Table

This table summarizes shortages by component across the full scenario.

### Component

Meaning:

The raw material, part, or subassembly under shortage pressure.

### Required Qty

Formula:

```text
Required Qty = sum(qty_per_fg x net_demand_qty across all FGs using that component)
```

Meaning:

Total material requirement generated by the scenario's net demand.

### Available Qty

Formula:

```text
Available Qty = on-hand inventory + procurement overrides
```

Meaning:

Current usable stock after any simulated procurement has been added.

### Shortage Qty

Formula:

```text
Shortage Qty = max(Required Qty - Available Qty, 0)
```

Meaning:

Material gap that must be addressed to fully support current demand.

## Decision Snapshot

The card below the tables is a narrative summary of the scenario.

It contains:

- the top-ranked FG
- the planned build quantity for that FG
- the top three shortage components
- the workbook source used for the run

Summary logic:

```text
Top-ranked FG = metrics["top_fg"]
Lead planned quantity = production_plan[0]["planned_qty"] if a plan exists
Top shortages = first 3 rows from aggregate_shortages
Workbook source = result["metadata"]["workbook"]
```

## Important Interpretation Note

The `Production posture` table and the final `production_plan` are related but not identical.

- The posture table shows FG-level feasibility and ranking signals.
- The production plan applies shared-inventory allocation across FGs in priority order.

That means one FG can look individually producible in the posture table, but its final planned quantity may drop if higher-priority FGs consume shared components first.

## Practical Reading Order

For planners, the fastest reading order is:

1. Check `Blocked FGs` and `FGs fully coverable`.
2. Check `Lead FG` and `Planned Build`.
3. Review `Production posture` for FG-by-FG feasibility.
4. Review `Procurement pressure` for the biggest material gaps.
5. Read the `Decision snapshot` for a compact narrative summary.
