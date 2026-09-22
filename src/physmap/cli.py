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

    screen = sub.add_parser("screen", help="run the cheap applicability screen for a vehicle")
    screen.add_argument("vehicle")
    screen.add_argument("--qoi", required=True)

    explain = sub.add_parser("explain", help="deterministically explain a recorded assessment")
    explain.add_argument("path")
    explain.add_argument("--point", required=True)
    explain.add_argument("--format", choices=("text", "json"), default="text")

    bench = sub.add_parser("benchmark", help="run / report the closure-observability benchmark")
    bench_sub = bench.add_subparsers(dest="action", required=True)
    bench_run = bench_sub.add_parser("run")
    bench_run.add_argument("--report", action="store_true")
    bench_sub.add_parser("report")

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
    print(f"'{args.command}' is not implemented yet in this build.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
