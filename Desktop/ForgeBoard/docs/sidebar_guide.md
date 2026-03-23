# Sidebar Guide

This note explains what each control in the ForgeBoard sidebar does.

## Purpose

The sidebar is the scenario-control area of the app.

It lets the planner:

- choose the workbook source
- simulate demand changes
- simulate procurement changes
- add business-priority hints
- preload planner questions
- enable or disable grounded Gemini answers
- run the scenario

Important note:

`Downloads` is not part of the sidebar. It is a main tab that appears after a run is completed.

## Client-Friendly Explanation

`The sidebar is where the planner sets the scenario before running the engine. Instead of editing Excel manually, the user can change assumptions directly in the app and immediately see the impact on production feasibility, shortages, and priorities.`

## Sidebar Controls

### 1. Workbook source

Purpose:

Choose whether to use the bundled sample workbook or upload a live workbook.

Options:

- `Use sample workbook`: use the demo workbook already configured in the app
- `Upload workbook`: upload a new client workbook for the current run

Simple explanation:

`This lets the same app work for demos and real planning runs.`

### 2. Upload workbook

Purpose:

Upload an `.xlsx` workbook with the required planning sheets.

Expected sheets:

- `Demand`
- `BOM Explode`
- `On-hand Qty`

Simple explanation:

`The planner can refresh the engine with the latest exported workbook without changing the application.`

### 3. Demand multiplier

Purpose:

Apply a scenario-wide multiplier to demand before planning.

Examples:

- `1.00` = current demand
- `1.20` = demand increased by 20%
- `0.80` = demand reduced by 20%

Simple explanation:

`This is a what-if control. It helps the planner test how the production plan changes if demand goes up or down.`

### 4. Procurement overrides (JSON)

Purpose:

Simulate extra stock arriving for specific materials before the scenario is run.

Example:

```json
{
  "PACKTC1D115": 5000,
  "COPS0568": 100000
}
```

Meaning:

`The app temporarily adds those quantities to current inventory so the planner can test whether targeted procurement improves the plan.`

### 5. Priority hints (JSON)

Purpose:

Add business importance signals that influence `Priority Score`.

Example:

```json
{
  "FG01": {
    "business_priority": 0.9,
    "margin_score": 0.8,
    "service_level_weight": 0.7
  }
}
```

Meaning:

`This tells ForgeBoard that some finished goods should rank higher because they are strategically or commercially more important.`

Important note:

`These values do not replace feasibility logic. They influence prioritization on top of the normal planning calculation.`

### 6. Seed planner questions

Purpose:

Preload common questions for the Assistant so users can start with useful prompts immediately.

Typical examples:

- `What can I produce today?`
- `Why is FG01 blocked?`
- `Which material should I procure first?`

Simple explanation:

`This gives planners a quick starting point for asking operational questions after the scenario runs.`

### 7. Use Gemini LangChain answers

Purpose:

Enable grounded LLM rewriting for assistant answers.

Behavior:

- if enabled, Gemini rewrites the deterministic planner answer using the current scenario context
- if disabled, answers stay fully deterministic
- if Gemini fails or returns an unusable answer, ForgeBoard falls back to the deterministic planner answer

Simple explanation:

`The engine still calculates the truth. Gemini only helps explain the result more naturally.`

### 8. Gemini model

Purpose:

Choose which Gemini model to use when LLM mode is enabled.

Example:

- `gemini-2.5-flash`

Simple explanation:

`This gives flexibility between speed and reasoning quality for assistant responses.`

### 9. Run Production Scenario

Purpose:

Run the full planning workflow using the current sidebar settings.

What happens:

- workbook is loaded
- demand multiplier is applied
- procurement overrides are added
- priority hints are considered
- finished-good feasibility is calculated
- shortages are calculated
- production plan is ranked
- assistant answers are prepared

Simple explanation:

`This is the action button that turns workbook data and planner assumptions into the dashboard result.`

## Recommended Reading Order

For planners, the normal sidebar flow is:

1. Choose workbook source.
2. Upload workbook if needed.
3. Set demand multiplier.
4. Add procurement overrides if testing a supply scenario.
5. Add priority hints if business ranking is needed.
6. Keep or adjust seed questions.
7. Enable Gemini if natural-language answers are wanted.
8. Click `Run Production Scenario`.

