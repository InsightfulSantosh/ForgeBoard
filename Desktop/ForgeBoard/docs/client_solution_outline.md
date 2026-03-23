# Client Solution Outline

## Problem Framing

The workbook is not just a reporting artifact. It is the input to a production decision engine:

- `Demand` tells us what needs to be supplied.
- `BOM Explode` tells us what each finished good consumes.
- `On-hand Qty` tells us what is available now.

The business question is:

`Given demand + BOM + inventory, what can we manufacture now, what is blocking us, and what should we prioritize next?`

## Proposed Engine

The implementation in this repo provides the core planning layer:

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

## Workflow Recommendation

Recommended daily workflow:

1. Upload or refresh the latest workbook extract.
2. Run the engine automatically.
3. Publish:
   - producible FG quantities
   - blocking components
   - prioritized production plan
   - procurement shortlist
4. Optionally expose the results through:
   - API
   - dashboard
   - conversational assistant

## Positioning to the Client

You can position this as:

`AI-powered Production Feasibility Engine`

with these outcomes:

- faster production decisions
- shortage visibility without manual pivot work
- scenario simulation before procurement
- explainable prioritization instead of spreadsheet guesswork
