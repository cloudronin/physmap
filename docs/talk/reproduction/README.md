# Reproduction — `physmap stress-test lewis-reuse` from a clean public clone

**Exit status 0. The clean clone's record matches the committed bank exactly.**

**What this reproduces:** the Lewis analysis — the surrogate fit, the input-based OOD scores,
the materiality, and the command's assertions — recomputed from the CFD-derived profiles
committed in `data/stress_tests/lewis_reuse/`. **It does not rerun OpenFOAM.** Regenerating the
CFD cases needs Docker, the case generator and the solver; `data/stress_tests/lewis_reuse/manifest.json`
records how.

## The run

| | |
|---|---|
| When | 2026-09-23T23:38:00Z |
| Repository | https://github.com/cloudronin/physmap — public, cloned over https with no credentials |
| Commit | `47ae207487a3be6862cab3ce410911da420277f7` |
| Working tree after clone | clean |
| Python | 3.10.15, in a fresh virtual environment |
| Platform | macOS-26.5.2-x86_64-i386-64bit |
| numpy, scipy, scikit-learn | 2.2.6, 1.15.3, 1.7.2 |
| Full environment | [`pip_freeze.txt`](pip_freeze.txt) |
| Exit status | **0** |
| Wall clock | 212 s |
| The command's last line | "The record matches the banked record exactly." |

## The commands, as run

```bash
git clone https://github.com/cloudronin/physmap.git physmap
cd physmap
python3.10 -m venv ../venv
../venv/bin/python -m pip install --upgrade pip
../venv/bin/python -m pip install -e .
../venv/bin/physmap stress-test lewis-reuse --json ../fresh_record.json > ../stdout.txt 2> ../stderr.txt
echo "exit status: $?"
```

## The files

| File | What it is |
|---|---|
| [`log.txt`](log.txt) | Time, commit, clean-tree check, environment, exit status, wall clock |
| [`stdout.txt`](stdout.txt) | The command's full output. The one machine-specific path, in the line naming the record file, is replaced with `<WORK>` |
| [`stderr.txt`](stderr.txt) | Empty |
| [`pip_freeze.txt`](pip_freeze.txt) | Every installed package and version |
| [`fresh_record.json`](fresh_record.json) | The record the clean clone wrote. `tools/talk_package.py check` compares it with the bank using the command's own comparison |
| [`benchmark_report.txt`](benchmark_report.txt) | `physmap benchmark report` from this checkout. It reads the committed matrix and recomputes nothing. The seven-vehicle figure is checked against it |
| [`naca_example.txt`](naca_example.txt) | `python examples/naca_entrance_region.py` from this checkout. The x/D figure is checked against it |

## What the talk package adds after this commit

Documentation, the figure script `tools/talk_package.py` and its test, and a one-sentence
correction to the text `physmap benchmark report` prints. Nothing the stress test runs — its
module, the command, its inputs or its bank — changed after `47ae207`.

## Run it yourself

```bash
git clone https://github.com/cloudronin/physmap.git
cd physmap
pip install -e .
physmap stress-test lewis-reuse
```

A few minutes. Exit status 0 means the assertions held and the record matched the bank.
