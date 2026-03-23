# Materials Tab Guide

This note explains what the `Materials` tab in ForgeBoard shows and how each section is calculated.

## Purpose

The `Materials` tab helps the planner understand raw-material pressure across the full scenario, not only for one finished good.

It combines:

- aggregate shortages
- procurement ranking
- raw material importance by use

## Data Sources

The tab is built from:

- `result["aggregate_shortages"]`: component shortages across total scenario demand
- `result["material_usage_ranking"]`: component importance ranking based on usage breadth and quantity
- current scenario inventory after procurement overrides

## Client-Friendly Explanation

`The Materials tab is the raw-material control view. It tells the planner which materials are short, which materials procurement should pay attention to first, and which materials are strategically important because they are used across many finished goods or large total demand.`

### Simple explanation of Aggregate Shortages

- `Component`: the raw material or part
- `Required Qty`: how much total quantity is needed in the current scenario
- `Available Qty`: how much stock is available now
- `Shortage Qty`: how much material is missing

Simple explanation:

`This is the total shortage table for the current plan.`

### Simple explanation of Procurement Ranking

`This is the shortage-driven component ranking. It lists all shortage materials from the largest gap to the smallest gap.`

### Simple explanation of Raw Material Importance by Use

`This is the strategic material ranking. It shows which materials matter most because they support many finished goods or large total planned demand.`

Useful business interpretation:

`A material can be important even if it is not the largest shortage, because it may affect many finished goods at once.`

## Aggregate Shortages

This section shows the full shortage list across the scenario.

### Required Qty

Formula:

```text
Required Qty = sum(qty_per_fg x net_demand_qty across all FGs using that component)
```

### Available Qty

Formula:

```text
Available Qty = on-hand inventory + procurement overrides
```

### Shortage Qty

Formula:

```text
Shortage Qty = max(Required Qty - Available Qty, 0)
```

Meaning:

This is the component-level gap that must be addressed to fully support the current demand position.

## Procurement Ranking

This section uses the same shortage list, but presents only the component names as an easy planner or procurement ranking.

Sort logic:

```text
Components are ranked by Shortage Qty descending
```

Meaning:

The first component in the list is the highest shortage-pressure item in the current scenario.

## Raw Material Importance by Use

This section ranks components by business importance in the scenario, not only by shortage gap.

Displayed columns:

- `Component`
- `Used In FG Count`
- `Used In FGs`
- `Total Required Qty`
- `Planned Consumption Qty`
- `Available Qty`
- `Shortage Qty`
- `Usage Importance Score`

### Used In FG Count

Formula:

```text
Used In FG Count = number of finished goods whose BOM includes this component
```

Meaning:

How broadly the material is shared across the product mix.

### Used In FGs

Meaning:

The exact finished goods that use that material in the current scenario.

### Total Required Qty

Formula:

```text
Total Required Qty = sum(qty_per_fg x net_demand_qty across all FGs using the component)
```

Meaning:

Total quantity demand created for that material by the current scenario.

### Planned Consumption Qty

Formula:

```text
Planned Consumption Qty = sum(consumed component quantity from the production plan)
```

Meaning:

How much of the material the current recommended production plan would actually consume.

### Available Qty

Meaning:

Current stock after procurement overrides are applied.

### Shortage Qty

Formula:

```text
Shortage Qty = max(Total Required Qty - Available Qty, 0)
```

Meaning:

Material gap at the scenario level.

### Usage Importance Score

Formula:

```text
Usage Importance Score =
100 x (
  0.45 x fg_count_signal +
  0.40 x required_qty_signal +
  0.15 x planned_consumption_signal
)
```

Signal definitions:

- `fg_count_signal`: scaled `Used In FG Count`
- `required_qty_signal`: scaled `Total Required Qty`
- `planned_consumption_signal`: scaled `Planned Consumption Qty`

Meaning:

This score ranks materials by combined usage breadth and quantity significance in the current scenario.

## Practical Reading Order

For planners and procurement teams, the fastest reading order is:

1. Review `Aggregate shortages` for the full gap table.
2. Review `Procurement ranking` for shortage-driven action order.
3. Review `Raw material importance by use` to identify strategically important shared materials.
4. Cross-check important materials against finished-good blockers in the `Finished Goods` tab.
