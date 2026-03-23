# ForgeBoard

ForgeBoard turns the client's Excel workbook into a production-feasibility engine.

It does four things on top of the raw Excel logic:

1. Explodes BOM demand into component requirements.
2. Matches requirements against current inventory.
3. Calculates what can be produced now and what is blocking production.
4. Builds a prioritized production plan with simple what-if simulation.

The implementation is intentionally dependency-free so it runs with the default `python3` in this workspace.

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

## Quick Start

```bash
python3 -m bom_ai_engine \
  --workbook "/Users/santoshkumar/Downloads/CAN MAKE - Sample Data to Santosh - 16-03-2026.xlsx" \
  --output-dir "/Users/santoshkumar/Desktop/ForgeBoard/outputs/sample_run"
```

Optional scenario inputs:

```bash
python3 -m bom_ai_engine \
  --workbook "/path/to/client.xlsx" \
  --output-dir "/path/to/output" \
  --demand-multiplier 1.2 \
  --procurement-file "/Users/santoshkumar/Desktop/ForgeBoard/examples/procurement.example.json" \
  --priority-file "/Users/santoshkumar/Desktop/ForgeBoard/examples/priority_hints.example.json"
```

## Streamlit UX

Install the UI dependency:

```bash
pip install -e ".[ui,llm-gemini]"
```

Or set up with `uv` and the new `requirements.txt`:

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Create `/Users/santoshkumar/Desktop/ForgeBoard/.env` and add your Gemini key:

```dotenv
GOOGLE_API_KEY=your-google-ai-studio-key
GEMINI_MODEL=gemini-2.5-flash
```

Run the frontend:

```bash
streamlit run /Users/santoshkumar/Desktop/ForgeBoard/streamlit_app.py
```

The app supports:

- sample workbook mode
- file upload for new client workbooks
- demand multiplier and procurement scenario controls
- priority hint JSON input
- planner Q&A using the Phase 2 assistant
- Gemini through LangChain for optional LLM responses
- download buttons for all generated artifacts

## Output Files

Each run writes:

- `scenario_summary.json`
- `fg_analysis.csv`
- `production_plan.csv`
- `material_shortages.csv`
- `phase1_report.md`
- `phase2_chat.md` when `--question` is provided

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

You can ask planner questions directly against the workbook scenario:

```bash
python3 -m bom_ai_engine \
  --workbook "/Users/santoshkumar/Downloads/CAN MAKE - Sample Data to Santosh - 16-03-2026.xlsx" \
  --output-dir "/Users/santoshkumar/Desktop/ForgeBoard/outputs/sample_run" \
  --question "What can I produce today?" \
  --question "Why is FG01 blocked?" \
  --question "Which material should I procure first?"
```

This creates `phase2_chat.md`.

Optional Gemini LangChain mode:

```bash
python3 -m bom_ai_engine \
  --workbook "/Users/santoshkumar/Downloads/CAN MAKE - Sample Data to Santosh - 16-03-2026.xlsx" \
  --output-dir "/Users/santoshkumar/Desktop/ForgeBoard/outputs/sample_run" \
  --question "Summarize the main risks for today's plan." \
  --use-llm \
  --llm-model "gemini-2.5-flash"
```

The CLI and Streamlit app load `.env` automatically. Gemini uses `GOOGLE_API_KEY`. If the LangChain Gemini call fails, the assistant falls back to deterministic answers.

Typical install:

```bash
pip install -e ".[ui,llm-gemini]"
```

## Validation

Run the tests with:

```bash
python3 -m unittest discover -s tests -v
```
