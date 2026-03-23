# ForgeBoard Client Solution Outline

`ForgeBoard` is the product name for this production-feasibility solution.

## Problem Framing

The workbook is not just a reporting artifact. It is the input to a production decision engine:

- `Demand` tells us what needs to be supplied.
- `BOM Explode` tells us what each finished good consumes.
- `On-hand Qty` tells us what is available now.

The business question is:

`Given demand + BOM + inventory, what can we manufacture now, what is blocking us, and what should we prioritize next?`

In ForgeBoard, that question is answered through a planning engine plus an optional AI explanation layer.

## Proposed Engine

The implementation in this repo provides ForgeBoard's core planning layer:

1. `BOM Intelligence`
   Converts FG demand into component-level material requirements.

2. `Inventory Matching`
   Compares component demand against on-hand stock and calculates shortages.

3. `Production Feasibility`
   Calculates the maximum producible quantity for each FG based on the limiting component.

4. `Decision Engine`
   Ranks FGs using feasibility plus optional business hints such as priority, margin, and service-level weight.

5. `What-if Simulation`
   Supports scenario runs such as demand increase and simulated procurement.

## What ForgeBoard Delivers

For each scenario, ForgeBoard can produce:

- FG-level feasibility analysis
- FG fulfillment and blocker diagnosis
- prioritized production plan
- aggregate material shortage list
- raw material importance ranking by use
- planner-friendly markdown summary
- CSV and JSON handoff artifacts
- conversational answers to planning questions

This makes the solution usable both as a backend engine and as a planner-facing tool.

## Sample Workbook Findings

Using the client workbook at `/Users/santoshkumar/Downloads/CAN MAKE - Sample Data to Santosh - 16-03-2026.xlsx`, the current stock position results in:

- `FG01`: build `0` out of net demand `1000`
- `FG02`: build `0` out of net demand `1999`
- `FG03`: build `0` out of net demand `3000`
- `FG04`: build `0` out of net demand `4000`

Common blocking materials in the sample include:

- `BASY0205`
- `COPS0420`
- `COPS0568`
- `PACKTC1D115`

Largest aggregate shortages in the sample include:

- `COPS0095`
- `MPTP3695`
- `MISC10040`
- `COPS0568`
- `COPW0150`

This confirms the client problem is a planning and optimization problem, not a dashboard problem.

## How Users Can Consume It

ForgeBoard can be used in multiple ways depending on the client environment:

- Streamlit interface for planners
- API or workflow integration behind ERP exports
- markdown, CSV, and JSON artifact handoff for procurement and operations teams

## Workflow Recommendation

Recommended daily workflow:

1. Upload or refresh the latest workbook extract.
2. Run ForgeBoard automatically.
3. Publish:
   - producible FG quantities
   - blocking components
   - fulfillment summary by FG
   - prioritized production plan
   - procurement ranking
   - raw material importance ranking
   - scenario report and downloadable artifacts
4. Optionally expose the results through:
   - API
   - dashboard
   - conversational assistant

## Positioning to the Client

You can position this as:

`ForgeBoard: AI-powered Production Feasibility Engine`

with these outcomes:

- faster production decisions
- shortage visibility without manual pivot work
- scenario simulation before procurement
- explainable prioritization instead of spreadsheet guesswork
- a cleaner path from Excel export to repeatable planning workflow
