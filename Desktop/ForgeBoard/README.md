# ForgeBoard

ForgeBoard is an AI-assisted production feasibility cockpit for BOM, inventory, and planner questions.

It does four things on top of the raw Excel workflow:

1. Explodes BOM demand into component requirements.
2. Matches requirements against current inventory.
3. Calculates what can be produced now and what is blocking production.
4. Builds a prioritized production plan with simple what-if simulation.

Naming note:

- Product name: `ForgeBoard`
- Python package and module path: `bom_ai_engine`

This means the user-facing product name is now `ForgeBoard`, while the internal import path stays `bom_ai_engine` for compatibility.

## Quick Start

Run commands from the repo root:

```bash
cd /path/to/ForgeBoard
```

Run the web application:

```bash
streamlit run streamlit_app.py
```

Then:

- use `Use sample workbook` for the bundled scenario
- or upload a live workbook from the sidebar
- adjust demand multiplier, procurement overrides, and priority hints
- run the scenario and download artifacts from the `Downloads` tab

## Installation

Preferred setup with `uv`:

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Alternative setup with `pip`:

```bash
python3 -m pip install -e ".[ui,llm-gemini]"
```

## Workbook Requirements

ForgeBoard expects a workbook with these sheets:

- `Demand`
- `BOM Explode`
- `On-hand Qty`

Helpful but optional:

- `Pivot-BOM Explode`

At a minimum, the workbook should preserve consistent finished-good and component codes across those sheets. The client notes in `docs/` explain the expected business meaning of each sheet.

## What This Solves

Given:

- `Demand`
- `BOM Explode`
- `On-hand Qty`

The engine answers:

- What finished goods can be produced now?
- What is the max producible quantity for each FG?
- Which components are blocking production?
- What procurement shortages matter most?
- How does the answer change if demand grows or stock is procured?
- Which FG should be prioritized first under the current scenario?

## Web Application UX

Install the UI dependencies first, then create a `.env` file in the repo root if you want Gemini-backed answers:

```dotenv
GOOGLE_API_KEY=your-google-ai-studio-key
GEMINI_MODEL=gemini-2.5-flash
```

Run the web frontend:

```bash
streamlit run streamlit_app.py
```

The app supports:

- executive overview snapshot with scenario status, lead FG, and procurement pressure
- sample workbook mode
- file upload for new client workbooks
- demand multiplier and procurement scenario controls
- finished-good fulfillment summary, explicit blocker-reason view, and covered-components table
- full finished-good shortage tables and aggregate material tables
- procurement ranking and raw material importance-by-use ranking
- a table of materials already available in enough quantity for the scenario
- priority hint JSON input
- planner Q&A using the Phase 2 assistant
- grounded Gemini through LangChain for optional LLM responses
- download buttons for all generated artifacts

## Output Files

Each run makes these files available in the `Downloads` tab:

- `scenario_summary.json`: complete scenario payload and summary metadata
- `fg_analysis.csv`: FG-level feasibility, coverage, and blocker view
- `production_plan.csv`: priority-ranked build recommendation
- `material_shortages.csv`: aggregated procurement pressure by component
- `material_usage_ranking.csv`: raw materials ranked by usage breadth and required quantity
- `phase1_report.md`: human-readable planning summary
- `phase2_chat.md`: planner Q&A transcript when `--question` is provided
- `phase2_chat.json`: structured Q&A payload when `--question` is provided

## Priority Hints Schema

Use this when the client wants business-aware prioritization instead of pure inventory feasibility.

```json
{
  "FG01": {
    "business_priority": 0.9,
    "margin_score": 0.7,
    "service_level_weight": 0.8
  },
  "FG02": {
    "business_priority": 0.6,
    "margin_score": 0.9
  }
}
```

Notes:

- Scores should be between `0.0` and `1.0`.
- If no hint file is supplied, the engine falls back to feasibility-driven ranking.

## Procurement Scenario Schema

```json
{
  "PACKTC1D115": 5000,
  "COPS0568": 100000
}
```

The quantities are added to current on-hand inventory before planning.

## Workflow Fit

This repo is the core decision engine. In a production workflow you can place it behind:

- a FastAPI service
- a scheduler for daily planning runs
- a dashboard
- a conversational layer that answers questions like `Why is FG01 blocked?`

## Phase 2 Assistant

You can ask planner questions directly inside the `Assistant` tab after running a scenario.

Typical planner questions:

- `What can I produce today?`
- `Why is FG01 blocked?`
- `Which material should I procure first?`
- `Which FG should I prioritize first?`

The web application loads `.env` automatically. Gemini uses `GOOGLE_API_KEY`. ForgeBoard grounds LLM answers with deterministic engine output and structured scenario context. If the LangChain Gemini call fails or returns an unusable answer, the assistant falls back to deterministic answers.

## Repo Layout

- `bom_ai_engine/`: core planning, assistant, reporting, and workflow modules
- `streamlit_app.py`: ForgeBoard web frontend
- `examples/`: sample procurement and priority JSON files
- `docs/`: client-facing explanation and presentation notes

## Related Docs

- `docs/client_solution_outline.md`
- `docs/forgeboard_solution_blueprint.md`
- `docs/cs_electrics_pitch_deck.md`
- `docs/client_presentation_guide.md`
- `docs/excel_sheets_client_guide.md`
- `docs/overview_tab_guide.md`
- `docs/finished_goods_tab_guide.md`
- `docs/materials_tab_guide.md`
- `docs/sidebar_guide.md`
