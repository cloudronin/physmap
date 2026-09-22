"""The `physmap` console script.

The set of subcommands is fixed by `physmap.release.CURRENT_RELEASE_STATE`. It is not
computed from the filesystem: a command never appears because a data directory happens
to be present. In particular `reproduce` does not exist in a preview build at all.
"""

from __future__ import annotations

import argparse
import sys

from physmap.release import CURRENT_RELEASE_STATE, has_reproduce_command


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="physmap",
        description=(
            "Physics-aware credibility checks for AI surrogates. "
            f"Release state: {CURRENT_RELEASE_STATE.value}."
        ),
    )
    p.add_argument("--version", action="store_true", help="print version and release state")
    sub = p.add_subparsers(dest="command")

    screen = sub.add_parser("screen", help="run the cheap applicability screen for a case")
    screen.add_argument("case", nargs="?", help="case id; omit with --list")
    screen.add_argument("--qoi", help="quantity of interest (checked against the case)")
    screen.add_argument("--list", action="store_true", help="list the available cases")

    explain = sub.add_parser(
        "explain", help="deterministically explain one benchmark cell or screening case")
    explain.add_argument("subject", nargs="?", help="a benchmark vehicle id, or a screening case id")
    explain.add_argument("--list", action="store_true", help="list what can be explained")

    bench = sub.add_parser(
        "benchmark",
        help="report the seven-vehicle closure-observability benchmark, and rerun the "
             "subset whose source data is redistributable",
    )
    bench_sub = bench.add_subparsers(dest="action", required=True)
    bench_run = bench_sub.add_parser(
        "run", help="recompute the rerunnable vehicles (a SUBSET of the seven)")
    bench_run.add_argument("--report", action="store_true",
                           help="print the full seven-vehicle report afterwards")
    bench_sub.add_parser(
        "report", help="print all seven outcomes, marking which are recomputed here")
    bench_sub.add_parser(
        "coverage", help="print what the rerunnable subset does and does not cover")

    # `reproduce` is added only in a release whose benchmark has cleared the readiness
    # gate. In a preview build the command does not exist -- `physmap reproduce` is an
    # unrecognised command, not a runtime "data missing" failure.
    if has_reproduce_command():
        rep = sub.add_parser("reproduce", help="reproduce a complete published benchmark")
        rep.add_argument("benchmark_id")
        rep.add_argument("--out", default="./artifacts")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        from physmap import __version__
        print(f"physmap {__version__} (release state: {CURRENT_RELEASE_STATE.value})")
        return 0
    if not args.command:
        parser.print_help()
        return 0
    if args.command == "screen":
        return _cmd_screen(args)
    if args.command == "benchmark":
        return _cmd_benchmark(args)
    if args.command == "explain":
        return _cmd_explain(args)
    print(f"'{args.command}' is not implemented yet in this build.", file=sys.stderr)
    return 2


def _cmd_explain(args) -> int:
    from physmap.applicability.fixtures import FIXTURE_IDS, get_fixture
    from physmap.benchmarks.registry import VEHICLES
    from physmap.benchmarks.report import load_banked_matrix
    from physmap.explain.benchmark import render_cell
    from physmap.explain.causal import render_screen

    if args.list:
        print("benchmark vehicles (closure validity + observability):")
        for v in VEHICLES:
            print(f"  {v.vehicle_id}")
        print("screening cases (causal-materiality applicability, declarative):")
        for c in FIXTURE_IDS:
            print(f"  {c}")
        return 0

    if not args.subject:
        print("a subject is required (or use --list)", file=sys.stderr)
        return 2

    if args.subject in FIXTURE_IDS:
        print(render_screen(get_fixture(args.subject)))
        return 0

    cells = {c["vehicle_id"]: c for c in load_banked_matrix()["cells"]}
    if args.subject in cells:
        print(render_cell(cells[args.subject]))
        return 0

    print(f"unknown subject {args.subject!r}; use --list", file=sys.stderr)
    return 2


def _cmd_screen(args) -> int:
    from physmap.applicability.fixtures import FIXTURE_IDS, get_fixture
    from physmap.explain.causal import render_screen

    if args.list:
        for case_id in FIXTURE_IDS:
            print(case_id)
        return 0

    if not args.case:
        print("a case id is required (or use --list)", file=sys.stderr)
        return 2

    try:
        result = get_fixture(args.case)
    except KeyError as e:
        print(str(e).strip("'"), file=sys.stderr)
        return 2

    if args.qoi and args.qoi != result.qoi:
        print(
            f"case {result.case_id!r} is screened for qoi {result.qoi!r}, not "
            f"{args.qoi!r}",
            file=sys.stderr,
        )
        return 2

    print(render_screen(result))
    return 0




def _cmd_benchmark(args) -> int:
    from physmap.benchmarks.registry import (
        banked_only_ids,
        licensed_ids,
        rerunnable_ids,
        unlicensed_shipped_ids,
    )
    from physmap.benchmarks.report import coverage_note, render_report

    if args.action == "report":
        print(render_report())
        return 0

    if args.action == "coverage":
        print(coverage_note())
        return 0

    # `run`. Recompute every vehicle from the checkout, then compare against the
    # banked matrix. The comparison is the point: a benchmark that runs but is never
    # checked against its own bank will drift silently.
    from physmap.benchmarks.benchmark_v0_4 import run_matrix
    from physmap.benchmarks.compare import compare_matrices
    from physmap.benchmarks.report import load_banked_matrix

    rerun, banked = rerunnable_ids(), banked_only_ids()
    print(f"Source data ships for {len(rerun)} of {len(rerun) + len(banked)} vehicles.")
    if banked:
        print(f"Banked only ({len(banked)}): {', '.join(banked)}")
    print(f"Of those shipped, {len(licensed_ids())} carry a licence and "
          f"{len(unlicensed_shipped_ids())} do not. Shipping is not licensing -- see NOTICE.")
    print()
    print("Recomputing from this checkout ...")

    # write=False on purpose: `run` must never overwrite the committed bank it is
    # being compared against.
    fresh = run_matrix(write=False)
    cells = {c["vehicle_id"]: c for c in fresh["cells"]}
    cmp = compare_matrices(fresh, load_banked_matrix())

    print(f"Recomputed {len(cells)} vehicles.")
    if not cmp.matches:
        print(f"DRIFT against the banked matrix in: {', '.join(cmp.drifting_vehicles())}")
        for d in cmp.drift[:10]:
            print(f"  {d}")
    elif cmp.bit_identical:
        print("Every cell matches the banked matrix exactly.")
    else:
        # Floats differing in their last bits across numpy/BLAS builds. Reported
        # rather than hidden, because "matches within tolerance" and "identical"
        # are different claims.
        print(f"Every cell matches the banked matrix: {cmp.summary()}.")
        for d in cmp.within_tolerance[:5]:
            print(f"  {d}")

    if args.report:
        print()
        print(render_report(rerun_results=cells))
    return 0 if cmp.matches else 1


if __name__ == "__main__":
    raise SystemExit(main())
