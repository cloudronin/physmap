# Reproduction — the public commands, from a clean public clone

**Every command exited as expected. The stress test's record matches the committed bank within
the command's stated tolerance; the benchmark's matrix and home baseline match theirs.**

**What this reproduces:** the Lewis analysis — the surrogate fit, the input-based OOD scores,
the materiality, and the command's assertions — recomputed from the CFD-derived profiles
committed in `data/stress_tests/lewis_reuse/`. **It does not rerun OpenFOAM.** Regenerating the
CFD cases needs Docker, the case generator and the solver; `data/stress_tests/lewis_reuse/manifest.json`
records how. From the same clone, the seven-vehicle benchmark (bank v0.4.1) and its home
baseline, the banked architecture axis, and the NACA x/D example.

## The run

| | |
|---|---|
| When | 2026-09-25T07:31:15Z |
| Repository | https://github.com/cloudronin/physmap — public, cloned over https with no credentials |
| Commit | `5a364fcb48e7e0fa9cc79715b9b9659c0a15fcf9` (the 0.2.5 release commit) |
| Working tree after clone | clean |
| Python | 3.11.2, in a fresh virtual environment; PyTorch not installed |
| Platform | `macOS-27.0-arm64-arm-64bit` |
| numpy, scipy, scikit-learn | 2.4.6, 1.17.1, 1.9.1 |
| Full environment | [`pip_freeze.txt`](pip_freeze.txt) |

| Command | Exit | Result |
|---|---|---|
| `physmap stress-test lewis-reuse` | **0** | 54 s. "The record matches the banked record: matches within 1e-4 relative, and 0.001 percentage points for errors (357 float field(s) differ, all by less than that)." |
| `physmap benchmark run` | **0** | 68 s. Every cell matches the v0.4.1 matrix within 1e-9 relative — one float differs in its last bits; the home baseline matches its bank bit for bit |
| `physmap benchmark report` | **0** | identical to [`benchmark_report.txt`](benchmark_report.txt) |
| `physmap benchmark architectures --banked` | **0** | reads the bank; no PyTorch needed |
| `physmap benchmark architectures` | **1**, as designed | without PyTorch it refuses in one sentence and names the extra to install |
| `python examples/naca_entrance_region.py` | **0** | identical to [`naca_example.txt`](naca_example.txt) |

The earlier record, on an Intel Mac with an older Python and older libraries, matched the stress
test's bank exactly. This machine differs in the last digits of the re-fitted Gaussian process;
the command's tolerance is set for exactly that, and still compares every flag, count and label
exactly.

## The commands, as run

```bash
git clone https://github.com/cloudronin/physmap.git physmap
cd physmap
python3.11 -m venv ../venv
../venv/bin/python -m pip install --upgrade pip
../venv/bin/python -m pip install -e .
../venv/bin/physmap stress-test lewis-reuse --json ../fresh_record.json > ../stdout.txt 2> ../stderr.txt
../venv/bin/physmap benchmark run
../venv/bin/physmap benchmark report
../venv/bin/physmap benchmark architectures --banked
../venv/bin/physmap benchmark architectures        # without PyTorch: refuses, exit 1
../venv/bin/python examples/naca_entrance_region.py
```

## The files

| File | What it is |
|---|---|
| [`log.txt`](log.txt) | Time, commit, clean-tree check, environment, every command's exit status and wall clock |
| [`stdout.txt`](stdout.txt) | The stress test's full output |
| [`stderr.txt`](stderr.txt) | Empty |
| [`pip_freeze.txt`](pip_freeze.txt) | Every installed package and version |
| [`fresh_record.json`](fresh_record.json) | The record the clean clone wrote. `tools/talk_package.py check` compares it with the bank using the command's own comparison |
| [`benchmark_report.txt`](benchmark_report.txt) | `physmap benchmark report` from this checkout. It reads the committed matrix and recomputes nothing. Both benchmark figures, and the README's benchmark table, are checked against it |
| [`naca_example.txt`](naca_example.txt) | `python examples/naca_entrance_region.py` from this checkout. The x/D figure is checked against it |

## What changed after this commit

- `physmap benchmark architectures` without PyTorch now refuses before it announces the
  twenty-minute run, instead of after. The refusal and the exit status are unchanged.
- This record.
