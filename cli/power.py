"""`evalrun power`: how many trials the statistical gate needs to catch a drop."""

import argparse
import sys
from typing import List, Optional, Tuple

from framework.regression import load_baseline_manifest
from framework.stats import minimum_detectable_drop, sample_std, trials_for_power


def _scenario_sigmas(baseline: str) -> List[Tuple[str, Optional[float], int]]:
    """(scenario name, score standard deviation, trials) for each baseline scenario."""
    data = load_baseline_manifest(baseline)
    rows = []
    for s_id, info in sorted(data["scenarios"].items()):
        scores = (info.get("statistics") or {}).get("trial_scores") or []
        rows.append((info.get("scenario_name") or s_id, sample_std(scores), len(scores)))
    return rows


def power_command(args: argparse.Namespace) -> int:
    """Prints, per scenario, the trials needed to catch --drop and the smallest drop caught now."""
    if args.drop <= 0:
        print("Error: --drop must be a positive number of score points.", file=sys.stderr)
        return 2
    if args.max_regression < 0:
        print("Error: --max-regression must not be negative.", file=sys.stderr)
        return 2

    if args.std is not None:
        if args.std < 0:
            print("Error: --std must not be negative.", file=sys.stderr)
            return 2
        rows = [("(given --std)", args.std, args.trials or 0)]
    else:
        try:
            rows = _scenario_sigmas(args.baseline)
        except Exception as e:
            print(f"Error loading baseline '{args.baseline}': {e}", file=sys.stderr)
            return 2
        if not any(sigma is not None for _, sigma, _ in rows):
            print(
                "Error: the baseline has no scenario with 2 or more trials, so its score noise "
                "is unknown. Re-run it with --trials 3 or more, or pass --std.",
                file=sys.stderr,
            )
            return 2

    threshold = args.max_regression
    print(
        f"Statistical gate power: catch a {args.drop:g}-point drop 80% of the time "
        f"(gate blocks when the 95% interval excludes 0 and the drop exceeds {threshold:g})."
    )
    print(f"{'Scenario':<32} | {'Trials':>6} | {'Score SD':>8} | {'Smallest drop caught':>20} | {'Trials needed':>13}")
    print("-" * 92)
    for name, sigma, trials in rows:
        if sigma is None:
            print(f"{name[:32]:<32} | {trials:>6} | {'n/a':>8} | {'needs 2+ trials':>20} | {'n/a':>13}")
            continue
        caught = f"{minimum_detectable_drop(sigma, threshold, trials):.1f}" if trials >= 2 else "n/a"
        needed = trials_for_power(sigma, args.drop, threshold)
        needed_text = str(needed) if needed is not None else "unreachable"
        print(f"{name[:32]:<32} | {trials:>6} | {sigma:>8.2f} | {caught:>20} | {needed_text:>13}")

    if args.drop <= threshold:
        print(
            f"\nA {args.drop:g}-point drop can never be caught 80% of the time: the gate only blocks "
            f"drops estimated above --max-regression {threshold:g}. Lower --max-regression to catch it."
        )
    print(
        "\nScore SD comes from the baseline's own trials; with few trials it is itself uncertain. "
        "Trials are per side: the baseline and the candidate each need that many."
    )
    return 0


def add_power_parser(subparsers) -> None:
    power_parser = subparsers.add_parser(
        "power",
        help="Estimate how many trials the statistical gate needs to catch a score drop",
        description=(
            "Uses the score noise measured in a baseline run (or --std) to report, per scenario, "
            "the trials per side needed to catch --drop with 80% probability under the "
            "statistical gate, and the smallest drop the baseline's trial count can catch."
        ),
    )
    source = power_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--baseline", type=str, help="Baseline run directory or manifest.json run with --trials 2+")
    source.add_argument("--std", type=float, help="Score standard deviation to assume instead of a baseline")
    power_parser.add_argument("--drop", type=float, required=True, help="Score drop (points) you want to catch")
    power_parser.add_argument(
        "--max-regression", type=float, default=5.0,
        help="The gate's allowed drop, as in 'evalrun run' (default: 5.0)",
    )
    power_parser.add_argument(
        "--trials", type=int, default=None,
        help="With --std: trials per side to report the smallest caught drop for",
    )
