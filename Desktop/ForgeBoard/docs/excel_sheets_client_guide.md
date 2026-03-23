# Excel Sheets Client Guide

This guide explains the workbook inputs that `ForgeBoard` expects and how to describe them to a client.

## Purpose

This note explains each sheet in the client workbook in simple business language.

Workbook used:

`CAN MAKE - Sample Data to Santosh - 16-03-2026.xlsx`

Sheets found in the workbook:

- `Demand`
- `BOM Explode`
- `On-hand Qty`
- `Pivot-BOM Explode`

In ForgeBoard, the first three sheets are the core calculation inputs. The pivot sheet is useful as a validation or reporting view.

---

## 1. Demand Sheet

### What this sheet means

This sheet tells us what the business wants to supply or manufacture.

In simple client language:

`This is the demand input sheet. It tells the system which finished goods are needed and in what quantity.`

### Example from the workbook

- `FG01` demand = `1000`
- `FG02` demand = `2000`
- `FG03` demand = `3000`
- `FG04` demand = `4000`

### Main columns

- `Org`
  Meaning: plant or organization code
- `Assembly (FG)`
  Meaning: finished good code
- `Demand Qty`
  Meaning: requested quantity
- `On-hand Qty`
  Meaning: finished good stock already available
- `Avail Qty`
  Meaning: demand status or planning flag in this sample

### Business interpretation

This sheet answers:

- What products are required?
- How much demand exists?
- How much finished stock is already available?

### How the engine uses it

The engine calculates:

`Net Demand = Demand Qty - FG On-hand Qty`

Example:

If `FG02` demand is `2000` and FG on-hand is `1`, then:

`Net Demand = 1999`

This net demand is what the system tries to produce.

### What to say to the client

`The Demand sheet tells the engine what has to be made after considering any finished goods already in stock.`

---

## 2. BOM Explode Sheet

### What this sheet means

This sheet explains how each finished good is built.

In simple client language:

`This is the product structure sheet. It tells the system which raw materials, parts, and subassemblies are required to produce each finished good.`

### Example from the workbook

For `FG01`, the sheet shows components such as:

- `PACKTC1D115`
- `FG01(SA)`
- `TA8DN11(115)`
- `SHMT7368`

### Main columns

- `TOP_ITEM`
  Meaning: finished good or parent item
- `COMPONENT_ITEM`
  Meaning: child material or subassembly
- `PLAN_LEVEL`
  Meaning: BOM level
- `COMPONENT_QUANTITY`
  Meaning: quantity required at that level
- `EXTENDED_QUANTITY`
  Meaning: rolled-up total quantity needed per FG

### Business interpretation

This sheet answers:

- What components are needed for each FG?
- How many units of each component are required?
- Which items are raw materials and which are subassemblies?

### How the engine uses it

The engine uses this sheet to explode FG demand into component demand.

Simple formula:

`Total component requirement = Net FG demand x quantity required per FG`

Example:

If one FG needs `2` screws and demand is `1000`, then total screw requirement is `2000`.

### What to say to the client

`The BOM Explode sheet converts product demand into material demand. Without this sheet, the system cannot know what is required to build each finished good.`

---

## 3. On-hand Qty Sheet

### What this sheet means

This sheet tells us what stock is currently available.

In simple client language:

`This is the inventory availability sheet. It tells the system which materials are in stock right now and how much quantity is available.`

### Important note

This sheet contains two views in the same worksheet:

- left side: raw inventory detail
- right side: summarized on-hand quantity by item

### Left-side detail section

Columns:

- `ITEM_CODE`
- `TRANSACTION_QUANTITY`
- `SUBINVENTORY_CODE`

Meaning:

- `ITEM_CODE` = material code
- `TRANSACTION_QUANTITY` = quantity in that record
- `SUBINVENTORY_CODE` = storage location or subinventory

Example:

- `BRAS1088 | 59150 | S15`
- `BRAS1088 | 169840 | S15`

This means the item appears in multiple inventory records.

### Right-side summary section

Columns:

- `Item Code`
- `On-hand Qty`

Meaning:

- total available stock per item

Example:

- `BRAS1088 | 228990`
- `MPTP0309 | 39488.02`

### Why some items look duplicated

Items such as `BRAS1088` and `MPTP0309` are not duplicated incorrectly.

What is happening:

- left side = detailed inventory rows
- right side = final total by item

Example:

`BRAS1088`

- raw rows:
  - `59150`
  - `169840`
- summary:
  - `228990`

Because:

`59150 + 169840 = 228990`

Another example:

`MPTP0309`

- raw rows include:
  - `706.02`
  - `1000`
  - `4080`
  - `4080`
  - `4622`
  - `25000`
- summary:
  - `39488.02`

Because:

`706.02 + 1000 + 4080 + 4080 + 4622 + 25000 = 39488.02`

### How the engine uses it

The app uses the summarized `Item Code` and `On-hand Qty` table for planning.

That means:

- it does not double-count the raw lines
- it uses the final consolidated stock quantity

### Business interpretation

This sheet answers:

- What materials are available now?
- Which components are available in sufficient quantity?
- Which materials are already at zero or very low stock?

### What to say to the client

`The On-hand Qty sheet is the current stock position. It tells the engine what material is actually available for production today.`

---

## 4. Pivot-BOM Explode Sheet

### What this sheet means

This sheet is a summarized comparison view.

In simple client language:

`This is a pre-aggregated material requirement sheet. It compares exploded BOM demand with current on-hand stock item by item.`

### Example from the workbook

- `BASY0205 | Sum of EXTENDED_QUANTITY = 4 | On-hand Qty = 0`
- `BRAS1088 | Sum of EXTENDED_QUANTITY = 4.16 | On-hand Qty = 228990`

### Main columns

- `COMPONENT_ITEM`
  Meaning: material code
- `Sum of EXTENDED_QUANTITY`
  Meaning: total required quantity from the BOM summary
- `On-hand Qty`
  Meaning: current stock available

### Business interpretation

This sheet answers:

- Which materials are required overall?
- Which materials have enough stock?
- Which materials are short?

### How to explain its role

This is useful as a validation or Excel reporting sheet, but it is not the main intelligence layer.

Why:

- it summarizes demand and stock
- but it does not decide what to produce first
- it does not optimize production allocation
- it does not explain blockers conversationally

### What to say to the client

`The Pivot-BOM Explode sheet is a good manual summary, but our engine automates and extends this logic into feasibility analysis, shortage intelligence, and decision support.`

---

## 5. How All Sheets Work Together

You can explain the full flow like this:

1. `Demand` tells us what needs to be made.
2. `BOM Explode` tells us what materials are needed to make it.
3. `On-hand Qty` tells us what stock is currently available.
4. `Pivot-BOM Explode` is a summary view of requirement vs stock.

Simple client version:

`Demand tells us what is needed, BOM tells us how to build it, inventory tells us what is available, and the engine turns all of that into production decisions.`

---

## 6. Which Sheets the Engine Actually Uses

ForgeBoard primarily uses:

- `Demand`
- `BOM Explode`
- `On-hand Qty`

These are the sheets required for core calculation.

The `Pivot-BOM Explode` sheet is helpful for checking or presenting the data, but the engine can derive similar results automatically from the core sheets.

### What to say to the client

`The system relies on the original business inputs, not only the pivot output. This is important because it keeps the solution explainable and scalable.`

---

## 7. Minimum Workbook Expectations

For the cleanest ForgeBoard run, the workbook should keep:

- consistent FG codes between `Demand` and `BOM Explode`
- consistent component codes between `BOM Explode` and `On-hand Qty`
- a usable summary inventory section with `Item Code` and `On-hand Qty`
- numeric demand and quantity fields without text placeholders

If the workbook structure changes materially, the ingestion logic may need a small mapping update.

---

## 8. What ForgeBoard Derives From These Sheets

From the workbook inputs, ForgeBoard derives:

- net demand by FG
- total component requirement
- available inventory by component
- shortage quantities
- max producible quantity
- prioritized build recommendation
- raw material importance ranking by usage
- planner-facing blocker explanations

This is why the workbook matters so much: it already contains the logic inputs needed for production planning.

---

## 9. One-Line Explanation for Each Sheet

- `Demand`: what the business wants to produce
- `BOM Explode`: what materials are needed to produce it
- `On-hand Qty`: what stock is currently available
- `Pivot-BOM Explode`: summarized material requirement vs stock comparison

---

## 10. Final Client Message

You can close with this:

`Your workbook already contains the key planning data. ForgeBoard turns those sheets into a production feasibility engine that shows what can be built, what is blocked, and what action should be taken next.`
