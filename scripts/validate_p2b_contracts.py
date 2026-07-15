#!/usr/bin/env python3
"""Validate the isolated, development-only P2b scorer contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.p2b_contracts import (  # noqa: E402
    load_p2b_contract,
    load_p2b_fixtures,
    promotion_blockers,
    validate_p2b_contract,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-promotable",
        action="store_true",
        help="Fail with exit 2 while review, rotating-policy, or authorization gates are closed.",
    )
    parser.add_argument("--json", action="store_true", help="Emit a JSON status object.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate_p2b_contract()
    if errors:
        if args.json:
            print(json.dumps({"status": "invalid", "errors": errors}, sort_keys=True))
        else:
            print("P2B_DEVELOPMENT_REGRESSION_FAILED", file=sys.stderr)
            for error in errors:
                print("- " + error, file=sys.stderr)
        return 1

    contract = load_p2b_contract()
    corpus = load_p2b_fixtures()
    blockers = promotion_blockers(contract)
    status = {
        "status": "development_regression_ok",
        "task_id": contract["task_id"],
        "scorer_version": contract["scorer_version"],
        "fixtures": len(corpus["fixtures"]),
        "expert_review_status": contract["expert_review_status"],
        "promotion_eligible": contract["promotion_eligible"],
        "evaluation_policy_ready": contract["evaluation_policy_ready"],
        "external_evaluation_authorized": contract["external_evaluation_authorized"],
        "promotion_blockers": blockers,
    }
    if args.json:
        print(json.dumps(status, sort_keys=True))
    else:
        print(
            "P2B_DEVELOPMENT_REGRESSION_OK fixtures={} scorer_version={} "
            "promotion_eligible={}".format(
                status["fixtures"],
                status["scorer_version"],
                str(status["promotion_eligible"]).lower(),
            )
        )

    if args.require_promotable and blockers:
        print(
            "P2B_PROMOTION_BLOCKED " + ",".join(blockers),
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
