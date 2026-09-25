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
    bench_arch = bench_sub.add_parser(
        "architectures",
        help="retrain three model types per vehicle and compare with the banked result "
             "(about 20 minutes; needs PyTorch)")
    bench_arch.add_argument("--banked", action="store_true",
                            help="print the banked result without recomputing it")

    # A stress test is a controlled demonstration of the CAUSAL path. It is deliberately not a
    # `benchmark` action: that command measures closure validity and observability, and a
    # materiality result must never appear under its name.
    stress = sub.add_parser(
        "stress-test",
        help="run a controlled stress test of the causal path -- a development demonstration, "
             "not a benchmark and not a performance claim")
    stress.add_argument("test_id", nargs="?", help="stress test id; omit with --list")
    stress.add_argument("--list", action="store_true", help="list the available stress tests")
    stress.add_argument("--json", metavar="PATH",
                        help="also write the full fresh record to PATH (never the committed bank)")

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
    from physmap._paths import CheckoutRequired, TorchRequired
    try:
        if args.command == "screen":
            return _cmd_screen(args)
        if args.command == "benchmark":
            return _cmd_benchmark(args)
        if args.command == "explain":
            return _cmd_explain(args)
        if args.command == "stress-test":
            return _cmd_stress_test(args)
    except (CheckoutRequired, TorchRequired) as e:
        # A pip-installed wheel has no checkout, and PyTorch is an optional extra. One
        # sentence saying what is missing and how to get it, not a traceback.
        print(f"physmap {args.command}: {e}", file=sys.stderr)
        return 1
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

    if args.action == "architectures":
        return _cmd_benchmark_architectures(args)

    # `run`. Recompute every vehicle from the checkout, then compare against the
    # banked matrix. The comparison is the point: a benchmark that runs but is never
    # checked against its own bank will drift silently.
    from physmap._paths import CheckoutRequired, have_checkout
    if not have_checkout():
        raise CheckoutRequired("the benchmark's vehicle data")
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

    # The home baseline is derived from the same data; it is recomputed and checked against
    # its own bank, which sits beside the matrix and changes none of it.
    from physmap.benchmarks.home_baseline import compare_with_bank as compare_home
    from physmap.benchmarks.home_baseline import compute as compute_home
    print()
    print("Recomputing the home baseline (refits the fitted surrogates without each home row) ...")
    home_cmp = compare_home(compute_home())
    if home_cmp.matches:
        print(f"The home baseline matches its bank: {home_cmp.summary()}.")
    else:
        print(f"DRIFT in the home baseline: {home_cmp.summary()}")
        for d in home_cmp.drift[:10]:
            print(f"  {d}")

    if args.report:
        print()
        print(render_report(rerun_results=cells))
    return 0 if (cmp.matches and home_cmp.matches) else 1


def _cmd_benchmark_architectures(args) -> int:
    from physmap.benchmarks.architecture_axis import (
        compare_with_bank,
        load_banked_axis,
        render_axis,
        run_axis,
    )

    if args.banked:
        print(render_axis(load_banked_axis(), recomputed=False))
        return 0
    from physmap._paths import CheckoutRequired, have_checkout
    if not have_checkout():
        raise CheckoutRequired("the benchmark's vehicle data")
    from physmap.benchmarks.architecture_axis import _require_torch
    _require_torch()                       # refuse before announcing twenty minutes of work
    print("Retraining three model types on every vehicle flagged for this axis "
          "(about 20 minutes) ...")
    fresh = run_axis(write=False)          # never overwrites the bank it is compared with
    cmp = compare_with_bank(fresh)
    print(render_axis(fresh, recomputed=True))
    print()
    if not cmp.matches:
        print(f"DRIFT against the banked result: {cmp.summary()}")
        for d in cmp.drift[:10]:
            print(f"  {d}")
    elif cmp.bit_identical:
        print("Every cell matches the banked result exactly.")
    else:
        print(f"Every cell matches the banked result: {cmp.summary()}.")
    return 0 if cmp.matches else 1


_STRESS_TESTS = {
    "lewis-reuse": "controlled model-reuse stress test on Lewis (1992) Test 35A: a "
                   "forced-convection surrogate reused where buoyancy is material",
}


def _cmd_stress_test(args) -> int:
    if args.list or not args.test_id:
        for tid, what in _STRESS_TESTS.items():
            print(f"{tid:14s} {what}")
        return 0
    if args.test_id not in _STRESS_TESTS:
        print(f"unknown stress test {args.test_id!r}; try --list", file=sys.stderr)
        return 2

    import json
    from pathlib import Path

    from physmap._paths import CheckoutRequired, have_checkout
    from physmap.stress_tests import lewis_reuse as st

    if not have_checkout():
        raise CheckoutRequired("the stress test's banked CFD-derived inputs")
    print("Recomputing from this checkout (a few minutes) ...")
    print()
    try:
        record = st.run()
    except FileNotFoundError as e:
        # The banked CFD profiles live in the checkout, like the benchmark's substrate data;
        # a wheel install says so plainly instead of failing with a traceback.
        print(f"Cannot run the stress test here: {e}", file=sys.stderr)
        return 1
    print(st.render(record))
    print()

    failures = st.check(record)
    if failures:
        print("ASSERTIONS FAILED:")
        for f in failures:
            print(f"  {f}")
    else:
        print("Assertions hold: every visible deployment input is a training input (design M); "
              "OOD scores are unchanged between gravity off and gravity on; materiality is zero "
              "with gravity off; the surrogate matches the accurate control.")

    if args.json:
        Path(args.json).write_text(json.dumps(record, indent=1) + "\n")
        print(f"Wrote the fresh record to {args.json}.")

    # Same contract as `benchmark run`: a result that is recomputed but never checked against
    # its own bank drifts silently.
    try:
        cmp = st.compare_with_bank(record)
    except FileNotFoundError as e:
        print(f"No banked record to compare against: {e}")
        return 1
    if not cmp.matches:
        print(f"DRIFT against the banked record in {len(cmp.drift)} field(s):")
        for d in cmp.drift[:10]:
            print(f"  {d}")
    elif cmp.bit_identical:
        print("The record matches the banked record exactly.")
    else:
        print(f"The record matches the banked record: {cmp.summary()}.")
    return 0 if (not failures and cmp.matches) else 1


if __name__ == "__main__":
    raise SystemExit(main())
