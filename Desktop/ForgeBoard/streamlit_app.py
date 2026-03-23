from __future__ import annotations

import html
import json
import os
import tempfile
from pathlib import Path

try:
    import streamlit as st
except ImportError as exc:
    raise SystemExit(
        "Streamlit is not installed. Install it with `pip install -e '.[ui]'`."
    ) from exc

from dotenv import load_dotenv

from bom_ai_engine.assistant import PlanningAssistant
from bom_ai_engine.workflow import build_summary_metrics, run_scenario

load_dotenv()

APP_TITLE = "ForgeBoard"
APP_SUBTITLE = "Manufacturing feasibility cockpit for BOM, inventory, and planner questions."
SAMPLE_WORKBOOK = Path(
    "/Users/santoshkumar/Downloads/CAN MAKE - Sample Data to Santosh - 16-03-2026.xlsx"
)
DEFAULT_QUESTIONS = [
    "What can I produce today?",
    "Why is FG01 blocked?",
    "Which material should I procure first?",
]


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🏭",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _apply_theme()
    _render_header()

    with st.sidebar:
        config = _render_sidebar()

    if "execution" not in st.session_state and SAMPLE_WORKBOOK.exists():
        st.session_state.execution = _run_from_path(
            SAMPLE_WORKBOOK,
            config["demand_multiplier"],
            config["procurement"],
            config["priority_hints"],
            config["seed_questions"],
            config["use_llm"],
            config["llm_model"],
        )
        st.session_state.chat_history = list(
            st.session_state.execution["assistant_answers"]
        )

    if config["run_clicked"]:
        workbook_path = _resolve_workbook_path(
            config["source_mode"],
            config["uploaded_workbook"],
        )
        if workbook_path is None:
            st.error("Choose a workbook source before running the scenario.")
        else:
            execution = _run_from_path(
                workbook_path,
                config["demand_multiplier"],
                config["procurement"],
                config["priority_hints"],
                config["seed_questions"],
                config["use_llm"],
                config["llm_model"],
            )
            st.session_state.execution = execution
            st.session_state.chat_history = list(execution["assistant_answers"])

    execution = st.session_state.get("execution")
    if not execution:
        st.info("Run a scenario to populate the dashboard.")
        return

    result = execution["result"]
    metrics = build_summary_metrics(result)

    _render_summary_band(metrics)

    overview_tab, fg_tab, materials_tab, assistant_tab, downloads_tab = st.tabs(
        ["Overview", "Finished Goods", "Materials", "Assistant", "Downloads"]
    )

    with overview_tab:
        _render_overview(result, metrics)
    with fg_tab:
        _render_finished_goods(result)
    with materials_tab:
        _render_materials(result)
    with assistant_tab:
        _render_assistant(
            result,
            config["use_llm"],
            config["llm_model"],
        )
    with downloads_tab:
        _render_downloads(execution["artifacts"])


def _render_sidebar() -> dict:
    st.markdown("### Scenario Controls")
    source_mode = st.radio(
        "Workbook source",
        ["Use sample workbook", "Upload workbook"],
        help="Use the bundled client workbook path or upload a new `.xlsx` file.",
    )
    uploaded_workbook = st.file_uploader(
        "Upload workbook",
        type=["xlsx"],
        help="Upload a workbook with `Demand`, `BOM Explode`, and `On-hand Qty` sheets.",
        disabled=source_mode != "Upload workbook",
    )

    if source_mode == "Use sample workbook":
        if SAMPLE_WORKBOOK.exists():
            st.caption(f"Sample workbook: `{SAMPLE_WORKBOOK}`")
        else:
            st.warning("The sample workbook path is not available on this machine.")

    st.markdown("### Scenario")
    demand_multiplier = st.slider(
        "Demand multiplier",
        min_value=0.50,
        max_value=2.00,
        value=1.00,
        step=0.05,
    )
    procurement_text = st.text_area(
        "Procurement overrides (JSON)",
        value="{}",
        height=120,
        help='Example: {"PACKTC1D115": 5000}',
    )
    priority_hints_text = st.text_area(
        "Priority hints (JSON)",
        value="{}",
        height=180,
        help='Example: {"FG01": {"business_priority": 0.9, "margin_score": 0.8}}',
    )

    st.markdown("### Assistant")
    seed_questions = st.multiselect(
        "Seed planner questions",
        DEFAULT_QUESTIONS,
        default=DEFAULT_QUESTIONS,
    )
    use_llm = st.checkbox(
        "Use Gemini LangChain answers",
        value=False,
        help="If disabled, planner answers stay deterministic.",
    )
    llm_model = st.text_input(
        "Gemini model",
        value=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        help="Example: `gemini-2.5-flash`.",
    )

    run_clicked = st.button(
        "Run Production Scenario",
        type="primary",
        use_container_width=True,
    )

    procurement = _parse_json_input(procurement_text, "procurement overrides")
    priority_hints = _parse_json_input(priority_hints_text, "priority hints")

    return {
        "source_mode": source_mode,
        "uploaded_workbook": uploaded_workbook,
        "demand_multiplier": demand_multiplier,
        "procurement": procurement,
        "priority_hints": priority_hints,
        "seed_questions": seed_questions,
        "use_llm": use_llm,
        "llm_model": llm_model,
        "run_clicked": run_clicked,
    }


def _resolve_workbook_path(source_mode: str, uploaded_workbook) -> Path | None:
    if source_mode == "Use sample workbook":
        return SAMPLE_WORKBOOK if SAMPLE_WORKBOOK.exists() else None

    if uploaded_workbook is None:
        return None

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as handle:
        handle.write(uploaded_workbook.getvalue())
        return Path(handle.name)


def _run_from_path(
    workbook_path: Path,
    demand_multiplier: float,
    procurement: dict,
    priority_hints: dict,
    questions: list[str],
    use_llm: bool,
    llm_model: str,
) -> dict:
    with st.spinner("Running BOM explosion, feasibility, and assistant analysis..."):
        execution = run_scenario(
            workbook_path,
            demand_multiplier=demand_multiplier,
            procurement=procurement,
            priority_hints=priority_hints,
            questions=questions,
            use_llm=use_llm,
            llm_model=llm_model,
        )
    return execution.to_dict()


def _render_header() -> None:
    st.markdown(
        """
        <section class="hero-shell">
          <div class="hero-meta">
            <div>
              <div class="hero-badge">Manufacturing Control Tower</div>
              <h1>ForgeBoard</h1>
              <p>{APP_SUBTITLE}</p>
            </div>
            <div class="hero-note">
              <span>Decision engine</span>
              <strong>Demand + BOM + Inventory</strong>
              <small>Professional planning UX on top of the same verified workflow.</small>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_summary_band(metrics: dict) -> None:
    cols = st.columns(5)
    cols[0].metric("Finished Goods", metrics["fg_count"])
    cols[1].metric("Net Demand", metrics["total_net_demand"])
    cols[2].metric("Planned Build", metrics["total_planned_qty"])
    cols[3].metric("Blocked FGs", metrics["blocked_fgs"])
    cols[4].metric("Top Shortage", metrics["top_shortage_component"] or "None")

    st.markdown(
        f"""
        <div class="status-strip">
          <div>
            <span class="status-label">Lead FG</span>
            <strong>{metrics['top_fg'] or 'None'}</strong>
          </div>
          <div>
            <span class="status-label">Total shortage volume</span>
            <strong>{metrics['total_shortage_qty']}</strong>
          </div>
          <div>
            <span class="status-label">FGs fully coverable</span>
            <strong>{metrics['fulfillable_fgs']}</strong>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_overview(result: dict, metrics: dict) -> None:
    analyses = result.get("analyses", [])
    shortages = result.get("aggregate_shortages", [])
    plan = result.get("production_plan", [])

    left, right = st.columns([1.4, 1.0])
    with left:
        with st.container(border=True):
            st.markdown("### Production posture")
            st.caption("Priority-ranked FG view based on current stock and the scenario controls in the sidebar.")
            st.dataframe(
                [
                    {
                        "FG": row["fg"],
                        "Net Demand": int(round(row["net_demand_qty"])),
                        "Max Producible": row["max_producible_qty"],
                        "Recommended Build": row["recommended_build_qty"],
                        "Coverage": f"{row['coverage_ratio']:.0%}",
                        "Priority Score": row["priority_score"],
                    }
                    for row in analyses
                ],
                use_container_width=True,
                hide_index=True,
            )
    with right:
        with st.container(border=True):
            st.markdown("### Procurement pressure")
            st.caption("Highest aggregate shortage lines across the current net demand position.")
            st.dataframe(
                [
                    {
                        "Component": row["component"],
                        "Shortage Qty": round(row["shortage_qty"], 2),
                        "Required Qty": round(row["required_qty"], 2),
                        "Available Qty": round(row["available_qty"], 2),
                    }
                    for row in shortages[:10]
                ],
                use_container_width=True,
                hide_index=True,
            )

    st.markdown("### Decision snapshot")
    st.markdown(result_to_markdown_preview(result, plan, metrics), unsafe_allow_html=True)


def _render_finished_goods(result: dict) -> None:
    analyses = result.get("analyses", [])
    fg_lookup = {row["fg"]: row for row in analyses}
    selected_fg = st.selectbox("Choose finished good", list(fg_lookup))
    fg = fg_lookup[selected_fg]

    stat_cols = st.columns(4)
    stat_cols[0].metric("Net Demand", int(round(fg["net_demand_qty"])))
    stat_cols[1].metric("Max Producible", fg["max_producible_qty"])
    stat_cols[2].metric("Recommended Build", fg["recommended_build_qty"])
    stat_cols[3].metric("Coverage", f"{fg['coverage_ratio']:.0%}")

    body_left, body_right = st.columns([1.1, 1.2])
    with body_left:
        with st.container(border=True):
            st.markdown("#### Limiting components")
            st.markdown(_badge_row(fg["limiting_components"], "info"), unsafe_allow_html=True)
            st.markdown("#### Blocking components")
            st.markdown(_badge_row(fg["blocking_components"], "alert"), unsafe_allow_html=True)
    with body_right:
        with st.container(border=True):
            st.markdown("#### Top shortage lines")
            st.dataframe(
                [
                    {
                        "Component": row["component"],
                        "Qty / FG": round(row["qty_per_fg"], 4),
                        "Required": round(row["required_qty"], 2),
                        "Available": round(row["available_qty"], 2),
                        "Shortage": round(row["shortage_qty"], 2),
                    }
                    for row in fg.get("shortages", [])[:12]
                ],
                use_container_width=True,
                hide_index=True,
            )


def _render_materials(result: dict) -> None:
    shortages = result.get("aggregate_shortages", [])
    if not shortages:
        st.success("No shortages detected in the current scenario.")
        return

    left, right = st.columns([1.45, 0.9])
    with left:
        with st.container(border=True):
            st.markdown("### Aggregate shortages")
            st.dataframe(
                [
                    {
                        "Component": row["component"],
                        "Required Qty": round(row["required_qty"], 2),
                        "Available Qty": round(row["available_qty"], 2),
                        "Shortage Qty": round(row["shortage_qty"], 2),
                    }
                    for row in shortages
                ],
                use_container_width=True,
                hide_index=True,
            )
    with right:
        with st.container(border=True):
            st.markdown("### Buy-first shortlist")
            st.caption("Fast procurement targets based on shortage magnitude.")
            st.markdown(
                _badge_row([row["component"] for row in shortages[:8]], "accent"),
                unsafe_allow_html=True,
            )


def _render_assistant(
    result: dict,
    use_llm: bool,
    llm_model: str,
) -> None:
    st.markdown("### Planner assistant")
    history = st.session_state.setdefault("chat_history", [])
    prompt_col, action_col = st.columns([1.3, 0.22])
    with prompt_col:
        question = st.text_input(
            "Ask a planner question",
            placeholder="Example: Why is FG03 blocked?",
            label_visibility="visible",
        )
    with action_col:
        st.markdown("<div class='button-spacer'></div>", unsafe_allow_html=True)
        ask_clicked = st.button("Ask", use_container_width=True)

    if ask_clicked and question.strip():
        answer = PlanningAssistant().answer(
            question.strip(),
            result,
            use_llm=use_llm,
            llm_model=llm_model,
        ).to_dict()
        history.append(answer)
        st.session_state.chat_history = history

    for item in history:
        with st.container(border=True):
            st.caption(f"{item['mode']} | {item['intent']}")
            st.markdown(f"**Q:** {item['question']}")
            st.write(item["answer"])


def _render_downloads(artifacts: dict[str, str]) -> None:
    st.markdown("### Export scenario artifacts")
    st.caption("Use these files for handoff, audit trail, or procurement and planning follow-up.")
    for name, contents in artifacts.items():
        mime = "text/markdown"
        if name.endswith(".json"):
            mime = "application/json"
        elif name.endswith(".csv"):
            mime = "text/csv"
        with st.container(border=True):
            st.download_button(
                label=f"Download {name}",
                data=contents,
                file_name=name,
                mime=mime,
                use_container_width=True,
            )


def result_to_markdown_preview(result: dict, plan: list[dict], metrics: dict) -> str:
    top_shortages = result.get("aggregate_shortages", [])[:3]
    lead_line = (
        (
            "Top-ranked FG is "
            f"<strong>{html.escape(str(metrics['top_fg']))}</strong> with planned build "
            f"<strong>{html.escape(str(plan[0]['planned_qty']))}</strong>."
        )
        if plan
        else "No production plan available."
    )
    shortage_line = ", ".join(
        f"<strong>{html.escape(str(row['component']))}</strong> ({row['shortage_qty']:.2f})"
        for row in top_shortages
    ) or "No shortages."
    return (
        "<div class='insight-card'>"
        f"<div class='insight-kicker'>Control summary</div>"
        f"<div class='insight-body'>{lead_line}</div>"
        f"<div class='insight-body'>Current highest procurement pressure is on {shortage_line}</div>"
        f"<div class='insight-foot'>Workbook source: {html.escape(result['metadata']['workbook'])}</div>"
        "</div>"
    )


def _badge_row(items: list[str], tone: str) -> str:
    if not items:
        return "<div class='badge-row'><span class='badge badge-neutral'>None</span></div>"
    badges = "".join(
        f"<span class='badge badge-{tone}'>{html.escape(item)}</span>"
        for item in items
    )
    return f"<div class='badge-row'>{badges}</div>"


def _parse_json_input(raw_text: str, label: str) -> dict:
    try:
        parsed = json.loads(raw_text.strip() or "{}")
    except json.JSONDecodeError as exc:
        st.error(f"Invalid JSON for {label}: {exc}")
        st.stop()
    if not isinstance(parsed, dict):
        st.error(f"{label.title()} must be a JSON object.")
        st.stop()
    return parsed


def _apply_theme() -> None:
    st.markdown(
        """
        <style>
          :root {
            --canvas: #f4f7fb;
            --canvas-accent: #ecf2f8;
            --surface: #ffffff;
            --surface-strong: #ffffff;
            --ink-1: #0b1220;
            --ink-2: #243447;
            --line: rgba(15, 23, 42, 0.16);
            --navy: #0f172a;
            --blue: #1d4ed8;
            --blue-soft: #dbeafe;
            --teal-soft: #dff7f2;
            --teal-ink: #0f766e;
            --amber-soft: #fff4d6;
            --amber-ink: #b45309;
            --rose-soft: #ffe4e6;
            --rose-ink: #be123c;
            --shadow: 0 14px 32px rgba(15, 23, 42, 0.07);
          }
          .stApp {
            background: linear-gradient(180deg, var(--canvas) 0%, var(--canvas-accent) 100%);
            color: var(--ink-1);
            font-family: "Space Grotesk", "IBM Plex Sans", "Avenir Next", sans-serif;
            text-rendering: optimizeLegibility;
          }
          .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2rem;
          }
          p, li, label, span, div {
            line-height: 1.45;
          }
          .hero-shell {
            padding: 1.35rem 1.5rem;
            margin-bottom: 1rem;
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 28px;
            background: linear-gradient(135deg, #0f172a 0%, #16233a 48%, #1d3557 100%);
            box-shadow: 0 24px 50px rgba(15, 23, 42, 0.18);
            color: #f8fafc;
          }
          .hero-meta {
            display: grid;
            grid-template-columns: minmax(0, 1.4fr) minmax(260px, 0.7fr);
            gap: 1rem;
            align-items: center;
          }
          .hero-shell h1 {
            margin: 0.2rem 0 0.4rem 0;
            font-size: 3rem;
            line-height: 1;
            letter-spacing: -0.06em;
            color: #f8fafc;
          }
          .hero-shell p {
            margin: 0;
            max-width: 64ch;
            color: rgba(248, 250, 252, 0.96);
            font-size: 1.05rem;
            font-weight: 500;
          }
          .hero-badge {
            display: inline-block;
            padding: 0.28rem 0.72rem;
            border-radius: 999px;
            background: rgba(148, 163, 184, 0.16);
            color: #dbeafe;
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
          }
          .hero-note {
            justify-self: end;
            padding: 1rem 1.1rem;
            border-radius: 18px;
            border: 1px solid rgba(255, 255, 255, 0.22);
            background: rgba(255, 255, 255, 0.12);
            min-width: 250px;
          }
          .hero-note span {
            display: block;
            text-transform: uppercase;
            font-size: 0.72rem;
            letter-spacing: 0.1em;
            color: rgba(219, 234, 254, 0.78);
          }
          .hero-note strong {
            display: block;
            margin-top: 0.35rem;
            font-size: 1.1rem;
            color: #ffffff;
          }
          .hero-note small {
            display: block;
            margin-top: 0.4rem;
            color: rgba(248, 250, 252, 0.92);
            line-height: 1.4;
          }
          div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--surface);
            border: 1px solid rgba(15, 23, 42, 0.14);
            border-radius: 18px;
            box-shadow: var(--shadow);
          }
          .status-strip {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.8rem;
            margin: 1rem 0 1.2rem 0;
            padding: 1rem 1.1rem;
            border-radius: 20px;
            border: 1px solid rgba(15, 23, 42, 0.14);
            background: #ffffff;
            box-shadow: var(--shadow);
          }
          .status-label {
            display: block;
            font-size: 0.75rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--ink-2);
            margin-bottom: 0.25rem;
            font-weight: 700;
          }
          [data-testid="stMetric"] {
            border: 1px solid var(--line);
            border-top: 4px solid var(--blue);
            border-radius: 18px;
            padding: 0.95rem 1rem;
            background: var(--surface);
            box-shadow: var(--shadow);
          }
          [data-testid="stMetricLabel"] {
            color: var(--ink-2) !important;
            font-weight: 700 !important;
          }
          [data-testid="stMetricValue"] {
            color: var(--ink-1) !important;
            font-weight: 800 !important;
          }
          [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f8fbff 0%, #eef4fb 100%);
            border-right: 1px solid rgba(15, 23, 42, 0.10);
          }
          [data-testid="stSidebar"] * {
            color: var(--ink-1);
          }
          [data-testid="stSidebar"] h1,
          [data-testid="stSidebar"] h2,
          [data-testid="stSidebar"] h3,
          [data-testid="stSidebar"] label,
          [data-testid="stSidebar"] p,
          [data-testid="stSidebar"] small,
          [data-testid="stSidebar"] span {
            color: var(--ink-1) !important;
          }
          [data-testid="stSidebar"] .stCaption {
            color: var(--ink-2) !important;
          }
          [data-testid="stSidebar"] .stButton button {
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            border: 0;
            color: white !important;
          }
          [data-testid="stSidebar"] .stTextInput input,
          [data-testid="stSidebar"] .stTextArea textarea,
          [data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"] > div,
          [data-testid="stSidebar"] div[data-baseweb="select"] > div {
            background: #ffffff;
            color: var(--ink-1) !important;
            border: 1px solid rgba(15, 23, 42, 0.18);
          }
          [data-testid="stSidebar"] div[data-baseweb="select"] input,
          [data-testid="stSidebar"] .stTextInput input::placeholder,
          [data-testid="stSidebar"] .stTextArea textarea::placeholder {
            color: #526173 !important;
            opacity: 1;
          }
          [data-testid="stSidebar"] .stSlider [data-baseweb="slider"] * {
            color: var(--ink-1) !important;
          }
          [data-testid="stSidebar"] div[data-testid="stFileUploader"] section {
            background: #ffffff;
            border: 1px dashed rgba(37, 99, 235, 0.38);
          }
          [data-testid="stSidebar"] [data-baseweb="radio"] > div,
          [data-testid="stSidebar"] [data-baseweb="checkbox"] > div {
            color: var(--ink-1) !important;
          }
          [data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 18px;
            overflow: hidden;
            background: var(--surface-strong);
          }
          [data-testid="stDataFrame"] div[role="grid"] {
            background: var(--surface-strong);
          }
          [data-testid="stDataFrame"] * {
            color: var(--ink-1);
          }
          div[data-testid="stTextInputRootElement"] input,
          div[data-testid="stTextAreaRootElement"] textarea,
          div[data-baseweb="select"] > div,
          div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            background: #ffffff;
            color: var(--ink-1);
            border-color: rgba(15, 23, 42, 0.2);
          }
          div[data-baseweb="select"] input {
            color: var(--ink-1);
          }
          div[data-testid="stTextInputRootElement"] input::placeholder,
          div[data-testid="stTextAreaRootElement"] textarea::placeholder {
            color: #526173;
            opacity: 1;
          }
          div[data-testid="stFileUploader"] section {
            background: #ffffff;
            border: 1px dashed rgba(37, 99, 235, 0.4);
            border-radius: 16px;
          }
          div[data-testid="stFileUploader"] small,
          div[data-testid="stFileUploader"] span {
            color: var(--ink-1);
          }
          h1, h2, h3, h4 {
            color: var(--ink-1);
            letter-spacing: -0.02em;
          }
          [data-testid="stMarkdownContainer"] p,
          [data-testid="stMarkdownContainer"] li,
          .stCaption {
            color: var(--ink-1);
          }
          .stCaption {
            opacity: 0.9;
          }
          [data-baseweb="tab-list"] {
            gap: 0.5rem;
            margin-bottom: 0.6rem;
          }
          [data-baseweb="tab"] {
            background: #ffffff;
            border: 1px solid rgba(15, 23, 42, 0.16);
            border-radius: 999px;
            color: var(--ink-1);
            font-weight: 700;
          }
          [aria-selected="true"][data-baseweb="tab"] {
            background: var(--navy);
            color: white;
            border-color: var(--navy);
          }
          .badge-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin: 0.25rem 0 0.15rem 0;
          }
          .badge {
            display: inline-flex;
            align-items: center;
            padding: 0.34rem 0.66rem;
            border-radius: 999px;
            font-size: 0.86rem;
            font-weight: 700;
            border: 1px solid transparent;
          }
          .badge-info {
            background: var(--blue-soft);
            color: var(--blue);
            border-color: rgba(29, 78, 216, 0.12);
          }
          .badge-alert {
            background: var(--rose-soft);
            color: var(--rose-ink);
            border-color: rgba(190, 18, 60, 0.12);
          }
          .badge-accent {
            background: var(--amber-soft);
            color: var(--amber-ink);
            border-color: rgba(180, 83, 9, 0.14);
          }
          .badge-neutral {
            background: #e2e8f0;
            color: #475569;
            border-color: rgba(71, 85, 105, 0.12);
          }
          .insight-card {
            margin-top: 0.45rem;
            padding: 1rem 1.1rem;
            border-radius: 20px;
            border: 1px solid rgba(15, 23, 42, 0.14);
            background: #ffffff;
            box-shadow: var(--shadow);
          }
          .insight-kicker {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--blue);
            font-weight: 800;
            margin-bottom: 0.35rem;
          }
          .insight-body {
            color: var(--ink-1);
            margin-bottom: 0.45rem;
            line-height: 1.5;
          }
          .insight-foot {
            color: var(--ink-2);
            font-size: 0.88rem;
          }
          .button-spacer {
            height: 1.85rem;
          }
          [data-testid="stButton"] button, [data-testid="stDownloadButton"] button {
            border-radius: 12px;
            border: 1px solid rgba(37, 99, 235, 0.18);
            font-weight: 700;
          }
          [data-testid="stButton"] button {
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            color: white;
          }
          [data-testid="stDownloadButton"] button {
            background: white;
            color: var(--ink-1);
          }
          @media (max-width: 900px) {
            .hero-meta {
              grid-template-columns: 1fr;
            }
            .hero-note {
              justify-self: stretch;
            }
            .status-strip {
              grid-template-columns: 1fr;
            }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
