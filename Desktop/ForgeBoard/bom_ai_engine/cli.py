from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from .workflow import run_scenario

load_dotenv()


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    workbook_path = Path(args.workbook).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    priority_hints = _load_json_map(args.priority_file)
    procurement = _load_json_map(args.procurement_file)

    execution = run_scenario(
        workbook_path,
        demand_multiplier=args.demand_multiplier,
        procurement=procurement,
        priority_hints=priority_hints,
        questions=args.question,
        use_llm=args.use_llm,
        llm_model=args.llm_model,
    )

    for name, contents in execution.artifacts.items():
        (output_dir / name).write_text(contents)

    _print_console_summary(execution.result, output_dir)
    if "phase2_chat.md" in execution.artifacts:
        print(f"Phase 2 chat output: {output_dir / 'phase2_chat.md'}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ForgeBoard production feasibility engine")
    parser.add_argument("--workbook", required=True, help="Path to the client XLSX workbook")
    parser.add_argument("--output-dir", required=True, help="Directory for generated outputs")
    parser.add_argument(
        "--demand-multiplier",
        type=float,
        default=1.0,
        help="Scenario multiplier for demand values. Example: 1.2 means +20%% demand.",
    )
    parser.add_argument(
        "--procurement-file",
        help="JSON file with component -> additional quantity to simulate procurement.",
    )
    parser.add_argument(
        "--priority-file",
        help="JSON file with FG -> business priority hints for smart ranking.",
    )
    parser.add_argument(
        "--question",
        action="append",
        help="Planner question for the Phase 2 conversational assistant. Use multiple times for multiple questions.",
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use Google Gemini through LangChain when GOOGLE_API_KEY is available. Falls back deterministically on failure.",
    )
    parser.add_argument(
        "--llm-model",
        default=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        help="Gemini model for Phase 2 LLM mode. Example: `gemini-2.5-flash`.",
    )
    return parser


def _load_json_map(file_path: str | None) -> dict:
    if not file_path:
        return {}
    path = Path(file_path).expanduser().resolve()
    return json.loads(path.read_text())


def _print_console_summary(result: dict, output_dir: Path) -> None:
    print("Scenario completed.")
    print(f"Output directory: {output_dir}")
    print("Finished goods summary:")
    for analysis in result["analyses"]:
        print(
            f"  {analysis['fg']}: build {analysis['recommended_build_qty']} / "
            f"{int(analysis['net_demand_qty'])}, blockers={','.join(analysis['blocking_components'][:3]) or 'none'}"
        )

    top_shortages = result["aggregate_shortages"][:5]
    if top_shortages:
        print("Top aggregate shortages:")
        for shortage in top_shortages:
            print(
                f"  {shortage['component']}: shortage={shortage['shortage_qty']:.2f}, "
                f"required={shortage['required_qty']:.2f}, available={shortage['available_qty']:.2f}"
            )
