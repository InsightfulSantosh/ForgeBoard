# Client Presentation Guide

Use `ForgeBoard` as the product name throughout the presentation. If needed, describe it as `ForgeBoard, an AI-assisted Production Feasibility and Planning Engine`.

## One-Line Positioning

`ForgeBoard is an AI-assisted Production Feasibility and Planning Engine.`

It helps the planning team answer:

`Given demand + BOM + inventory, what can we produce now, what is blocked, what should we procure, and what should we prioritize first?`

---

## 1. Client Problem

You can explain the business problem like this:

The Excel file is not just a report. It contains the core inputs required for a production decision:

- `Demand` sheet tells us what finished goods are needed.
- `BOM Explode` sheet tells us which components are required for each finished good.
- `On-hand Qty` sheet tells us which materials are currently available.

The real client question is:

`Can we meet current demand with available stock, and if not, what is stopping us?`

This means the solution is not only a dashboard. It is a planning and decision-support system.

---

## 2. What the System Does

You can explain the workflow in 4 steps:

1. The system reads demand, BOM, and stock from the workbook.
2. It explodes the BOM and calculates total material requirement.
3. It compares requirement vs available stock and finds shortages.
4. It recommends what can be produced, what is blocked, and what should be prioritized.

Simple explanation for client:

`The engine converts raw planning data into production decisions.`

## 2A. What the User Sees

When demoing ForgeBoard, explain that the experience is organized around five working views:

- `Overview`: overall production posture and procurement pressure
- `Finished Goods`: FG-by-FG feasibility, blockers, and shortage lines
- `Materials`: aggregate shortages and buy-first shortlist
- `Assistant`: planner Q&A on top of the current scenario
- `Downloads`: CSV, JSON, and markdown artifacts for handoff

Useful line for the client:

`ForgeBoard is not only a calculator. It is a planner workspace with scenario controls, decision views, and exportable outputs.`

---

## 3. What Is AI and What Is Not

This is important to explain clearly.

### Deterministic logic

These parts are exact business calculations:

- BOM explosion
- inventory matching
- shortage calculation
- max producible quantity
- production feasibility

Explain it like this:

`The engine calculates the truth using manufacturing rules.`

### AI layer

The AI layer is used for:

- natural-language explanations
- planner question answering
- scenario interpretation
- future recommendation and forecasting extensions

Explain it like this:

`AI does not replace the production logic. AI makes the system easier to use, easier to explain, and later can add prediction and recommendations.`

---

## 4. Sidebar Explanation

The ForgeBoard sidebar is the planner control panel. It lets the user create and test planning scenarios without editing Excel manually.

### 4.1 Workbook source

Purpose:

Choose whether to use the sample workbook or upload a real workbook.

How to explain:

`This allows the same system to be used for demo mode and live plant data.`

Example:

- `Use sample workbook` for client demo
- `Upload workbook` for today's planning file from ERP or operations

### 4.2 Upload workbook

Purpose:

Upload the latest Excel file with demand, BOM, and inventory sheets.

How to explain:

`The planner can refresh the decision engine with new operational data without changing the application.`

Example:

`At the start of the day, the planner uploads the latest workbook export and immediately sees what can be produced.`

### 4.3 Demand multiplier

Purpose:

Simulate demand increase or decrease across the scenario.

How to explain:

`This is used for what-if analysis. Instead of editing each demand line in Excel, the planner can simulate demand shocks instantly.`

Example:

- `1.00` = current demand
- `1.20` = demand increased by 20%
- `0.80` = demand reduced by 20%

Client explanation:

`If demand increases by 20%, the system immediately shows which materials will become critical.`

### 4.4 Procurement overrides

Purpose:

Simulate the impact of receiving additional stock for specific components.

How to explain:

`This helps procurement test the value of buying certain materials before placing the order.`

Example:

```json
{"PACKTC1D115": 5000}
```

Meaning:

`If we receive 5,000 units of PACKTC1D115, how much extra finished goods can we build?`

### 4.5 Priority hints

Purpose:

Add business-level importance to finished goods.

How to explain:

`Not every finished good is equally important. Some have higher customer urgency, better margin, or stronger business priority.`

Example:

```json
{
  "FG01": {
    "business_priority": 0.9,
    "margin_score": 0.8
  }
}
```

Meaning:

`FG01 should be prioritized more aggressively because it is commercially important.`

### 4.6 Seed planner questions

Purpose:

Preload common operational questions for the assistant.

How to explain:

`This gives planners ready-made questions so they can start getting answers immediately.`

Examples:

- `What can I produce today?`
- `Why is FG01 blocked?`
- `Which material should I procure first?`

### 4.7 Use Gemini LangChain answers

Purpose:

Enable the Gemini-powered explanation layer.

How to explain:

`When enabled, Gemini explains the planning results in business language. The planning math still comes from the production engine.`

Important line for client:

`The engine calculates the result, and Gemini explains it.`

### 4.8 Gemini model

Purpose:

Choose which Gemini model to use.

How to explain:

`This gives flexibility between speed and reasoning quality depending on the use case and cost preference.`

Example:

`gemini-2.5-flash` for fast planner interaction.

### 4.9 Run Production Scenario

Purpose:

Run the full planning engine on the selected scenario.

How to explain:

`One click runs the complete workflow: demand explosion, shortage detection, production feasibility, prioritization, and assistant responses.`

### 4.10 Downloads

Purpose:

Export the scenario outputs for other teams.

How to explain:

`After the run, ForgeBoard produces files that planning, procurement, and management can reuse without going back to the workbook.`

Typical outputs:

- scenario summary JSON
- FG analysis CSV
- production plan CSV
- material shortages CSV
- markdown report

---

## 4A. Finished Goods Tab Explanation

This tab helps the planner understand one finished good at a time.

### Net Demand

Meaning:

`How much demand is still open after subtracting finished good stock already available.`

Example:

If demand is `1000` and FG on-hand is `100`, then net demand is `900`.

### Max Producible

Meaning:

`The maximum number of units that can be produced with the currently available components.`

How it is calculated:

For each component in the BOM:

`possible units = available component stock / quantity needed per FG`

The smallest value becomes the production limit.

### Recommended Build

Meaning:

`The quantity the engine recommends building now, based on both demand and available stock.`

Simple rule:

`Recommended Build = minimum of Net Demand and Max Producible`

### Coverage

Meaning:

`What percentage of net demand can be fulfilled right now.`

Example:

If net demand is `1000` and producible quantity is `250`, then coverage is `25%`.

### Limiting components

Meaning:

`These are the exact components that mathematically limit how many units can be produced.`

How to explain:

`The system checks every component needed for that FG and identifies which component gives the lowest possible build quantity. That component becomes the bottleneck.`

If multiple components give the same lowest limit, they all appear in `Limiting components`.

Example:

If one FG needs:

- `1 x BASY0205`, available = `0`
- `2 x PACKTC1D115`, available = `0`
- `4 x COPS0420`, available = `500`

Then:

- possible units from `BASY0205` = `0 / 1 = 0`
- possible units from `PACKTC1D115` = `0 / 2 = 0`
- possible units from `COPS0420` = `500 / 4 = 125`

So `BASY0205` and `PACKTC1D115` are limiting components because they cap production at `0`.

### Blocking components

Meaning:

`These are the main operational blockers the planner should pay attention to first.`

How to explain:

`Blocking components start with the limiting components and then include the largest shortage lines. This gives the planner a short actionable list of what is stopping production.`

Simple distinction:

- `Limiting components` = strict mathematical bottlenecks
- `Blocking components` = practical planner-facing blocker list

Why they may look similar:

`If several components are already at zero or near zero stock, the same items will appear in both lists.`

### Top shortage lines

Meaning:

`This section shows the biggest shortages for the selected finished good.`

Columns:

- `Component` = missing material
- `Qty / FG` = quantity needed for one FG
- `Required` = total material needed for current net demand
- `Available` = current stock
- `Shortage` = gap between required and available

Client explanation:

`This helps the planner understand not only which parts are blocking production, but also how large the shortage is for each part.`

---

## 5. How To Demo It Live

Use this sequence in front of the client.

### Step 1: Show the baseline

Say:

`First, we load the current workbook and let the engine calculate what is possible with today's stock position.`

Then click:

- `Use sample workbook`
- `Run Production Scenario`

What to point out:

- blocked finished goods
- top shortages
- recommended build quantities
- downloadable planning artifacts

### Step 2: Show demand simulation

Say:

`Now let us simulate a sudden increase in demand without changing the original workbook.`

Then change:

- `Demand multiplier = 1.20`

What to point out:

- shortages increase
- coverage drops
- more pressure on critical components

### Step 3: Show procurement simulation

Say:

`Now let us test whether targeted procurement improves the production plan.`

Enter:

```json
{"PACKTC1D115": 5000}
```

What to point out:

- some FG feasibility may improve
- procurement impact becomes visible before actual purchase

### Step 4: Show business prioritization

Say:

`Now we tell the engine that one finished good is strategically more important.`

Enter:

```json
{
  "FG01": {
    "business_priority": 0.9,
    "margin_score": 0.8
  }
}
```

What to point out:

- ranking changes
- planning becomes business-aware, not only stock-aware

### Step 5: Show the AI assistant

Say:

`Now we move from static planning output to conversational planning support.`

Ask:

- `Why is FG01 blocked?`
- `Which material should I procure first?`
- `What can I produce today?`

What to point out:

- faster planner understanding
- less dependency on spreadsheet experts
- easier management communication
- same scenario can be exported immediately after discussion

---

## 6. What the Client Gains

Use these talking points:

- faster production decision-making
- immediate visibility into shortages
- ability to simulate demand and procurement before acting
- reduced manual Excel effort
- more explainable planning decisions
- foundation for future forecasting and AI recommendations
- a repeatable planning workflow instead of ad hoc workbook interpretation

Short version:

`This reduces planning time, improves visibility, and makes decisions explainable.`

---

## 7. Future AI Roadmap

If the client asks what comes next, explain it in phases.

### Phase 1

Deterministic planning engine:

- BOM explosion
- inventory matching
- shortage detection
- production feasibility

### Phase 2

AI-assisted planner interface:

- Gemini-powered explanations
- conversational Q&A
- easier scenario interpretation

### Phase 3

Predictive intelligence:

- shortage forecasting
- demand trend prediction
- procurement recommendation

### Phase 4

Optimization:

- recommended production sequence
- smarter procurement prioritization
- service-level and margin-aware planning

---

## 8. Questions the Client May Ask

### Is this replacing ERP?

Answer:

`No. ERP remains the system of record. ForgeBoard acts as a planning intelligence layer on top of ERP exports or data feeds.`

### Is this just a dashboard?

Answer:

`No. A dashboard only shows data. ForgeBoard calculates feasibility, detects blockers, simulates scenarios, and supports planning decisions.`

### Where exactly is AI used?

Answer:

`The manufacturing calculations are deterministic. AI is used in the explanation layer and can later be extended into prediction and recommendation.`

### Can it work with our real files?

Answer:

`Yes. The UI already supports workbook upload, and the next step can be ERP/API integration if required.`

### Can planners test procurement before buying?

Answer:

`Yes. Procurement overrides are built specifically for that what-if scenario.`

---

## 9. Closing Statement

You can close with this:

`Today, planners often rely on manual Excel work to understand shortages and production feasibility. ForgeBoard converts that spreadsheet workflow into a decision engine with AI-assisted interaction. It gives the team faster answers, clearer priorities, and a foundation for predictive planning.`

---

## 10. Demo Inputs You Can Reuse

### Procurement example

```json
{"PACKTC1D115": 5000}
```

### Priority example

```json
{
  "FG01": {
    "business_priority": 0.9,
    "margin_score": 0.8
  }
}
```

### Questions to ask

- `What can I produce today?`
- `Why is FG01 blocked?`
- `Which material should I procure first?`
- `Which FG should I prioritize first?`
