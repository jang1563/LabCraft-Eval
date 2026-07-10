#!/usr/bin/env python3
"""Lightweight terminal workflow for manual human baselines on seeded tasks."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.tasks.growth_01 import build_growth_01_sample  # noqa: E402
from src.tasks.transform_01 import build_transform_01_sample  # noqa: E402
from src.tools.lab_tools import (  # noqa: E402
    cleanup_sample,
    count_colonies_call,
    fit_growth_curve_call,
    incubate_call,
    inoculate_growth_call,
    measure_od600_call,
    plate_call,
    prepare_media_call,
    set_active_sample,
    transform_call,
)
from src.tools.reference import check_safety_call, lookup_reagent_call  # noqa: E402
from src.trajectory_scorer import score_growth_trajectory, score_transform_trajectory  # noqa: E402

AsyncToolHandler = Callable[..., Awaitable[str]]


@dataclass(frozen=True)
class HumanToolSpec:
    name: str
    description: str
    example_arguments: dict[str, Any]
    handler: AsyncToolHandler


@dataclass(frozen=True)
class HumanTaskSession:
    task_id: str
    seed_index: int
    sample_id: str
    operator_id: str
    prompt: str
    prompt_variant: str
    ground_truth_path: str
    rubric_path: str
    final_answer_template: str
    tools: tuple[HumanToolSpec, ...]
    scorer: Callable[[str, list[dict[str, Any]], str], dict[str, Any]]


TRANSFORM_FINAL_ANSWER_TEMPLATE = """10 pg: <value> CFU/ug
100 pg: <value> CFU/ug
1,000 pg: <value> CFU/ug
10,000 pg: <value> CFU/ug
Interpretation: <brief note saying whether the runs were internally consistent>
"""

GROWTH_FINAL_ANSWER_TEMPLATE = """LB: <value> minutes
M9 + glucose: <value> minutes
LB + chloramphenicol (1.8 uM): <value> minutes
Ranking: <fastest> > <middle> > <slowest>
Notes: <optional troubleshooting note if any condition was undersampled>
"""

TRANSFORM_REQUIRED_LABELS = (
    "10 pg",
    "100 pg",
    "1,000 pg",
    "10,000 pg",
)
GROWTH_REQUIRED_LABELS = (
    "LB",
    "M9 + glucose",
    "LB + chloramphenicol (1.8 uM)",
)

COMMON_TOOLS: tuple[HumanToolSpec, ...] = (
    HumanToolSpec(
        name="lookup_reagent",
        description="Search the reagent database.",
        example_arguments={"reagent_name": "<choose reagent name>"},
        handler=lookup_reagent_call,
    ),
    HumanToolSpec(
        name="check_safety",
        description="Search the safety database.",
        example_arguments={"chemical_name": "<choose chemical name>"},
        handler=check_safety_call,
    ),
)

TRANSFORM_TOOLS: tuple[HumanToolSpec, ...] = COMMON_TOOLS + (
    HumanToolSpec(
        name="prepare_media",
        description="Prepare one or more ampicillin selection plates.",
        example_arguments={
            "medium": "<choose plate medium>",
            "antibiotic": "<choose selection antibiotic>",
            "antibiotic_concentration_ug_ml": "<choose concentration>",
            "plate_count": "<choose plate count>",
        },
        handler=prepare_media_call,
    ),
    HumanToolSpec(
        name="transform",
        description="Run a chemical transformation.",
        example_arguments={
            "plasmid_mass_pg": "<choose one listed DNA mass>",
            "heat_shock_seconds": "<choose duration>",
            "recovery_minutes": "<choose duration>",
            "outgrowth_media": "<choose recovery medium>",
            "shaking": "<choose true or false>",
            "ice_incubation_minutes": "<choose duration>",
        },
        handler=transform_call,
    ),
    HumanToolSpec(
        name="plate",
        description="Plate a transformed culture.",
        example_arguments={
            "culture_id": "<culture_id returned by transform>",
            "plate_id": "<plate_id returned by prepare_media>",
            "dilution_factor": "<choose dilution>",
            "volume_ul": "<choose plating volume>",
        },
        handler=plate_call,
    ),
    HumanToolSpec(
        name="count_colonies",
        description="Count colonies on a plated sample.",
        example_arguments={"plating_id": "<plating_id returned by plate>"},
        handler=count_colonies_call,
    ),
)

GROWTH_TOOLS: tuple[HumanToolSpec, ...] = COMMON_TOOLS + (
    HumanToolSpec(
        name="inoculate_growth",
        description="Start a named growth condition.",
        example_arguments={
            "condition": "<choose one listed condition>",
            "starting_od600": "<choose starting OD600>",
        },
        handler=inoculate_growth_call,
    ),
    HumanToolSpec(
        name="incubate",
        description="Advance a growth culture in time.",
        example_arguments={
            "growth_id": "<growth_id returned by inoculate_growth>",
            "duration_minutes": "<choose measurement cadence>",
        },
        handler=incubate_call,
    ),
    HumanToolSpec(
        name="measure_od600",
        description="Measure culture density.",
        example_arguments={
            "growth_id": "<growth_id returned by inoculate_growth>",
            "dilution_factor": "<choose dilution>",
        },
        handler=measure_od600_call,
    ),
    HumanToolSpec(
        name="fit_growth_curve",
        description="Fit a growth curve for one condition.",
        example_arguments={"growth_id": "<growth_id returned by inoculate_growth>"},
        handler=fit_growth_curve_call,
    ),
)


def _seeded_sample_id(base_sample_id: str, seed_index: int) -> str:
    if seed_index < 0:
        raise ValueError("seed_index must be non-negative")
    return "{}_seed_{:02d}".format(base_sample_id, seed_index)


def _build_growth_sample_for_variant(prompt_variant: str) -> dict[str, Any]:
    previous_variant = os.environ.get("LABCRAFT_GROWTH_PROMPT_VARIANT")
    os.environ["LABCRAFT_GROWTH_PROMPT_VARIANT"] = prompt_variant
    try:
        return build_growth_01_sample()
    finally:
        if previous_variant is None:
            os.environ.pop("LABCRAFT_GROWTH_PROMPT_VARIANT", None)
        else:
            os.environ["LABCRAFT_GROWTH_PROMPT_VARIANT"] = previous_variant


def build_task_session(
    task_id: str,
    seed_index: int,
    operator_id: str = "anonymous",
    growth_prompt_variant: str = "baseline",
) -> HumanTaskSession:
    if task_id == "transform_01":
        sample = build_transform_01_sample()
        return HumanTaskSession(
            task_id=task_id,
            seed_index=seed_index,
            sample_id=_seeded_sample_id(sample["id"], seed_index),
            operator_id=operator_id,
            prompt=sample["input"],
            prompt_variant="baseline",
            ground_truth_path=sample["target"],
            rubric_path=sample["metadata"]["rubric_path"],
            final_answer_template=TRANSFORM_FINAL_ANSWER_TEMPLATE,
            tools=TRANSFORM_TOOLS,
            scorer=score_transform_trajectory,
        )

    if task_id == "growth_01":
        sample = _build_growth_sample_for_variant(growth_prompt_variant)
        return HumanTaskSession(
            task_id=task_id,
            seed_index=seed_index,
            sample_id=_seeded_sample_id(sample["id"], seed_index),
            operator_id=operator_id,
            prompt=sample["input"],
            prompt_variant=growth_prompt_variant,
            ground_truth_path=sample["target"],
            rubric_path=sample["metadata"]["rubric_path"],
            final_answer_template=GROWTH_FINAL_ANSWER_TEMPLATE,
            tools=GROWTH_TOOLS,
            scorer=score_growth_trajectory,
        )

    raise ValueError("Unsupported task_id: {}".format(task_id))


def _default_session_path(task_id: str, seed_index: int) -> Path:
    return _default_session_path_for_operator(
        task_id,
        seed_index,
        operator_id="anonymous",
    )


def _safe_path_fragment(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip()).strip("._-").lower()
    return cleaned or "anonymous"


def _default_session_path_for_operator(
    task_id: str,
    seed_index: int,
    operator_id: str,
    prompt_variant: str = "baseline",
) -> Path:
    safe_operator_id = _safe_path_fragment(operator_id)
    variant_suffix = ""
    if task_id == "growth_01" and prompt_variant != "baseline":
        variant_suffix = "__{}".format(_safe_path_fragment(prompt_variant))
    return (
        REPO_ROOT
        / "results"
        / "human_baseline_sessions"
        / "{}__{}{}_seed_{:02d}.json".format(
            safe_operator_id,
            task_id,
            variant_suffix,
            seed_index,
        )
    )


def _portable_repo_path(path_str: str) -> str:
    path = Path(path_str)
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_saved_session(session_path: Path) -> dict[str, Any] | None:
    if not session_path.exists():
        return None
    try:
        payload = json.loads(session_path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError("Session file is not valid JSON: {}".format(exc)) from exc
    if not isinstance(payload, dict):
        raise ValueError("Session file must contain a JSON object.")
    return payload


def saved_session_status(session_path: Path) -> str:
    payload = load_saved_session(session_path)
    if payload is None:
        return "pending"
    status = payload.get("status")
    if status in {"in_progress", "completed"}:
        return status
    return "invalid"


def _validate_saved_session_payload(payload: dict[str, Any], session: HumanTaskSession) -> None:
    expected_fields = {
        "task_id": session.task_id,
        "seed_index": session.seed_index,
        "sample_id": session.sample_id,
        "operator_id": session.operator_id,
        "prompt_variant": session.prompt_variant,
    }
    for field_name, expected_value in expected_fields.items():
        observed_value = payload.get(field_name)
        if observed_value is None:
            continue
        if observed_value != expected_value:
            raise ValueError(
                "Existing session file does not match the requested session for {}: expected {!r}, found {!r}.".format(
                    field_name,
                    expected_value,
                    observed_value,
                )
            )


def _restore_transcript_state(
    transcript: list[dict[str, Any]],
    tools_by_name: dict[str, HumanToolSpec],
) -> None:
    for index, item in enumerate(transcript, start=1):
        if not isinstance(item, dict):
            raise ValueError("Transcript item {} is not a JSON object.".format(index))
        if item.get("type") != "tool_call":
            continue
        tool_name = item.get("tool_name")
        arguments = item.get("arguments", {})
        if not isinstance(tool_name, str) or tool_name not in tools_by_name:
            raise ValueError("Transcript item {} references an unknown tool.".format(index))
        if not isinstance(arguments, dict):
            raise ValueError("Transcript item {} arguments must be a JSON object.".format(index))
        try:
            asyncio.run(tools_by_name[tool_name].handler(**arguments))
        except Exception as exc:
            raise RuntimeError(
                "Could not restore transcript state from item {} ({}): {}".format(
                    index,
                    tool_name,
                    exc,
                )
            ) from exc


def _write_session(
    session_path: Path,
    session: HumanTaskSession,
    transcript: list[dict[str, Any]],
    final_answer: str | None = None,
    score: dict[str, Any] | None = None,
) -> None:
    session_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_id": session.task_id,
        "seed_index": session.seed_index,
        "sample_id": session.sample_id,
        "operator_id": session.operator_id,
        "prompt_variant": session.prompt_variant,
        "prompt": session.prompt,
        "ground_truth_path": _portable_repo_path(session.ground_truth_path),
        "rubric_path": _portable_repo_path(session.rubric_path),
        "transcript": transcript,
        "final_answer": final_answer,
        "score": score,
        "status": "completed" if final_answer is not None else "in_progress",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    session_path.write_text(json.dumps(payload, indent=2))


def _print_tools(session: HumanTaskSession) -> None:
    print("Available tools:")
    for tool in session.tools:
        print("- {}: {}".format(tool.name, tool.description))
        print("  example: {} {}".format(tool.name, json.dumps(tool.example_arguments)))


def _parse_tool_command(line: str) -> tuple[str, dict[str, Any]]:
    parts = line.strip().split(maxsplit=1)
    tool_name = parts[0]
    if len(parts) == 1:
        return tool_name, {}
    try:
        arguments = json.loads(parts[1])
    except json.JSONDecodeError as exc:
        raise ValueError("Arguments must be a JSON object: {}".format(exc)) from exc
    if not isinstance(arguments, dict):
        raise ValueError("Arguments must decode to a JSON object.")
    return tool_name, arguments


def _pretty_output(observation: str) -> str:
    try:
        return json.dumps(json.loads(observation), indent=2, sort_keys=True)
    except Exception:
        return observation


def _print_history(transcript: list[dict[str, Any]]) -> None:
    if not transcript:
        print("No tool calls have been recorded yet.")
        return
    for index, item in enumerate(transcript, start=1):
        if not isinstance(item, dict):
            continue
        tool_name = item.get("tool_name", "<unknown>")
        arguments = item.get("arguments", {})
        print("[{}] {} {}".format(index, tool_name, json.dumps(arguments, sort_keys=True)))
        pretty_content = _pretty_output(str(item.get("content", "")))
        for line in pretty_content.splitlines():
            print("    {}".format(line))


def _read_multiline_final_answer() -> str:
    print("Enter the final answer. Type END on its own line when finished.")
    lines = []
    while True:
        line = input()
        if line == "END":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _has_growth_insufficient_points(transcript: list[dict[str, Any]]) -> bool:
    for item in transcript:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "tool_call":
            continue
        if item.get("tool_name") != "fit_growth_curve":
            continue
        content = str(item.get("content", "")).lower()
        if "insufficient_points" in content:
            return True
    return False


def _missing_growth_labels(final_answer: str) -> list[str]:
    patterns = {
        "LB": r"(?im)^\s*LB\s*:",
        "M9 + glucose": r"(?im)^\s*M9\s*\+\s*glucose\s*:",
        "LB + chloramphenicol (1.8 uM)": r"(?im)^\s*LB\s*\+\s*chloramphenicol\s*\(1\.8\s*[uµμ]M\)\s*:",
    }
    missing = []
    for label, pattern in patterns.items():
        if re.search(pattern, final_answer) is None:
            missing.append(label)
    return missing


def _summarize_final_answer_feedback(
    session: HumanTaskSession,
    final_answer: str,
    transcript: list[dict[str, Any]],
    score: dict[str, Any],
) -> list[str]:
    feedback: list[str] = []
    final_answer_lower = final_answer.lower()

    if session.task_id == "transform_01":
        missing_labels = [label for label in TRANSFORM_REQUIRED_LABELS if label.lower() not in final_answer_lower]
        if missing_labels:
            feedback.append("Missing transform readout lines for: {}.".format(", ".join(missing_labels)))
        if "consistent" not in final_answer_lower:
            feedback.append("The transform scorer expects the word 'consistent' in the interpretation line.")
    elif session.task_id == "growth_01":
        missing_labels = _missing_growth_labels(final_answer)
        if missing_labels:
            feedback.append("Missing growth-condition lines for: {}.".format(", ".join(missing_labels)))
        if "minutes" not in final_answer_lower and " min" not in final_answer_lower:
            feedback.append("The growth scorer expects reported doubling times in minutes.")
        if _has_growth_insufficient_points(transcript):
            troubleshooting_terms = ("insufficient", "not enough", "undersampled", "too few")
            if not any(term in final_answer_lower for term in troubleshooting_terms):
                feedback.append("A growth fit reported insufficient points; consider noting that in the final answer.")

    if score.get("task_success", 0.0) == 0.0:
        feedback.append("Task success is currently 0.0, which usually means a required field is missing or misformatted.")
    elif score.get("task_success", 0.0) < 1.0:
        feedback.append("Task success is partial; double-check required fields and reported values before saving.")
    return feedback


def _review_final_answer(
    session: HumanTaskSession,
    final_answer: str,
    transcript: list[dict[str, Any]],
    score: dict[str, Any],
) -> str:
    print()
    print("Provisional score summary:")
    print(json.dumps(score, indent=2, sort_keys=True))
    feedback = _summarize_final_answer_feedback(session, final_answer, transcript, score)
    if feedback:
        print()
        print("Review notes:")
        for note in feedback:
            print("- {}".format(note))

    while True:
        print()
        choice = input("Type `save` to finalize, `edit` to rewrite the final answer, or `cancel` to return to the REPL: ").strip().lower()
        if choice in {"save", "edit", "cancel"}:
            return choice
        print("Please enter `save`, `edit`, or `cancel`.")


def _print_help() -> None:
    print("Commands:")
    print("- help: show this message")
    print("- prompt: print the task prompt again")
    print("- tools: list available tools and example JSON arguments")
    print("- history: print the recorded tool calls and observations for this session")
    print("- template: print a scorer-friendly final answer template")
    print("- status: show how many tool calls have been recorded")
    print("- final: enter a multiline final answer, review the provisional score, then save/edit/cancel")
    print("- quit: exit without scoring")
    print("- <tool_name> <json>: call a tool, for example:")
    print(
        '  prepare_media {"medium": "<choose medium>", '
        '"antibiotic": "<choose antibiotic>", '
        '"antibiotic_concentration_ug_ml": "<choose concentration>", '
        '"plate_count": "<choose count>"}'
    )


def run_human_baseline(session: HumanTaskSession, session_path: Path) -> int:
    tools_by_name = {tool.name: tool for tool in session.tools}
    transcript: list[dict[str, Any]] = []
    existing_status = "pending"

    try:
        payload = load_saved_session(session_path)
        if payload is not None:
            _validate_saved_session_payload(payload, session)
            existing_status = saved_session_status(session_path)
            if existing_status == "completed":
                print("Session file already contains a completed run: {}".format(session_path))
                print("Choose a different operator id or --session-out path to avoid overwriting it.")
                return 1
            if existing_status == "invalid":
                print("Session file has an unrecognized status and will not be overwritten: {}".format(session_path))
                return 1
            saved_transcript = payload.get("transcript", [])
            if not isinstance(saved_transcript, list):
                raise ValueError("Existing session transcript must be a list.")
            transcript = saved_transcript
    except (OSError, ValueError) as exc:
        print("Could not initialize session file {}: {}".format(session_path, exc))
        return 1

    print()
    print("Human baseline session")
    print("  task: {}".format(session.task_id))
    print("  seed_index: {}".format(session.seed_index))
    print("  sample_id: {}".format(session.sample_id))
    print("  operator_id: {}".format(session.operator_id))
    print("  prompt_variant: {}".format(session.prompt_variant))
    print("  session file: {}".format(session_path))
    print()
    print(session.prompt)
    print()
    print("Use `tools` to see available tool calls or `help` for commands.")
    # Match Inspect's seed semantics exactly: the labelled seed index, not a
    # hash of the human-baseline sample id, initializes the simulator RNG.
    set_active_sample(session.sample_id, seed=session.seed_index)
    try:
        if existing_status == "in_progress":
            print("Resuming in-progress session with {} recorded tool calls.".format(len(transcript)))
            if transcript:
                try:
                    _restore_transcript_state(transcript, tools_by_name)
                except (ValueError, RuntimeError) as exc:
                    print("Could not resume the saved session state: {}".format(exc))
                    print("The existing session file was left untouched.")
                    return 1
                print("Use `history` to inspect the previously recorded tool calls and generated IDs.")
        else:
            _write_session(session_path, session, transcript)

        while True:
            try:
                line = input("human-baseline> ").strip()
            except EOFError:
                print()
                print("EOF received. Session saved without final scoring.")
                return 0
            if not line:
                continue
            if line == "help":
                _print_help()
                continue
            if line == "prompt":
                print(session.prompt)
                continue
            if line == "tools":
                _print_tools(session)
                continue
            if line == "history":
                _print_history(transcript)
                continue
            if line == "template":
                print(session.final_answer_template)
                continue
            if line == "status":
                print("Recorded {} tool calls so far.".format(len(transcript)))
                continue
            if line == "quit":
                print("Exiting without final scoring. Partial session saved to {}.".format(session_path))
                return 0
            if line == "final":
                while True:
                    final_answer = _read_multiline_final_answer()
                    score = session.scorer(final_answer, transcript, session.ground_truth_path)
                    review_action = _review_final_answer(session, final_answer, transcript, score)
                    if review_action == "edit":
                        continue
                    if review_action == "cancel":
                        print("Returning to the REPL without finalizing the session.")
                        break
                    _write_session(session_path, session, transcript, final_answer=final_answer, score=score)
                    print("Saved completed session to {}.".format(session_path))
                    return 0
                continue

            try:
                tool_name, arguments = _parse_tool_command(line)
            except ValueError as exc:
                print("Could not parse command: {}".format(exc))
                continue

            tool = tools_by_name.get(tool_name)
            if tool is None:
                print("Unknown command or tool: {}".format(tool_name))
                continue

            try:
                result = asyncio.run(tool.handler(**arguments))
            except TypeError as exc:
                print("Tool call failed before execution: {}".format(exc))
                continue
            except Exception as exc:  # pragma: no cover - defensive for interactive use.
                print("Tool call raised an unexpected error: {}".format(exc))
                continue

            transcript.append(
                {
                    "type": "tool_call",
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "content": result,
                }
            )
            _write_session(session_path, session, transcript)
            print(_pretty_output(result))
    finally:
        cleanup_sample(session.sample_id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=("transform_01", "growth_01"), required=True)
    parser.add_argument("--seed-index", type=int, default=0)
    parser.add_argument(
        "--operator-id",
        default="anonymous",
        help="Short identifier for the human operator completing the session.",
    )
    parser.add_argument(
        "--growth-prompt-variant",
        choices=("baseline", "verbose_troubleshoot"),
        default="baseline",
        help="Prompt variant for growth_01 sessions.",
    )
    parser.add_argument(
        "--session-out",
        default=None,
        help="Optional JSON output path. Defaults to results/human_baseline_sessions/<operator_id>__<task>_seed_<NN>.json",
    )
    args = parser.parse_args(argv)

    session = build_task_session(
        task_id=args.task,
        seed_index=args.seed_index,
        operator_id=args.operator_id,
        growth_prompt_variant=args.growth_prompt_variant,
    )
    session_path = (
        Path(args.session_out)
        if args.session_out
        else _default_session_path_for_operator(
            args.task,
            args.seed_index,
            session.operator_id,
            prompt_variant=session.prompt_variant,
        )
    )
    if not session_path.is_absolute():
        session_path = (REPO_ROOT / session_path).resolve()

    return run_human_baseline(session, session_path)


if __name__ == "__main__":
    raise SystemExit(main())
