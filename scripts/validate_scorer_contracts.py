#!/usr/bin/env python3
"""Validate the local P1 scorer contract and deterministic fixture corpus."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.scorer_contracts import review_progress, run_scorer_regression  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-expert-approved",
        action="store_true",
        help="Fail unless every fixture has been expert-reviewed and frozen.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = run_scorer_regression()
    if errors:
        print("SCORER_CONTRACT_REGRESSION_FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    progress = review_progress()
    print(
        "SCORER_CONTRACT_REGRESSION_OK "
        f"fixtures={progress['required']} contract_set={progress['contract_set']}"
    )
    print(
        "EXPERT_REVIEW_STATUS "
        f"approved={progress['approved']} pending={progress['pending']} "
        f"promotion_ready={str(progress['promotion_ready']).lower()}"
    )
    if args.require_expert_approved and not progress["promotion_ready"]:
        print("EXPERT_REVIEW_GATE_CLOSED")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
