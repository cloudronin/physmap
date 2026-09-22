"""Repo guard: what a bare `import physmap` is allowed to drag in.

Two separate promises, and they fail in different ways:

1. **Forbidden anywhere.** No LLM client, no deep-learning stack, and -- new in
   this repository -- no rdflib, no pyshacl, no uofa. rdflib used to arrive
   through a single unused import line: pipeline/detectors.py imported
   infra.corpus_runtime, which imported experiments.blindspot_pilot, which
   imported experiments.blindspot_causal, which imported rdflib. Nothing on the
   guardrail path called any of it. The chain is cut; this test keeps it cut.

2. **Not on the bare-import path.** numpy, sklearn, scipy and joblib are real
   dependencies, but `import physmap` must not pay for them. The public surface
   is re-exported lazily through PEP 562, so `from physmap import
   CredibilityGuardrail` pulls the stack and a bare import does not. An eager
   re-export in __init__.py would break this silently.
"""

from __future__ import annotations

import importlib
import pkgutil
import subprocess
import sys

import physmap

FORBIDDEN_AT_IMPORT = (
    "torch", "torch_geometric", "torch_scatter", "torch_sparse", "pykeen",
    "transformers", "openai", "anthropic", "ollama", "llama_cpp", "vllm",
    "rdflib", "pyshacl",
    "uofa", "uofa_cli",
)

#: Real dependencies that a BARE `import physmap` must still not load.
LAZY_ONLY = ("numpy", "sklearn", "scipy", "joblib")


def _all_submodule_names() -> list[str]:
    names = [physmap.__name__]
    for info in pkgutil.walk_packages(physmap.__path__, prefix="physmap."):
        names.append(info.name)
    return names


def _roots(names) -> set[str]:
    return {n.split(".")[0] for n in names}


def test_no_forbidden_module_at_import():
    for mod in list(sys.modules):
        if mod.split(".")[0] in _roots(FORBIDDEN_AT_IMPORT):
            del sys.modules[mod]

    for name in _all_submodule_names():
        importlib.import_module(name)

    leaked = sorted(_roots(sys.modules) & _roots(FORBIDDEN_AT_IMPORT))
    assert leaked == [], f"forbidden modules imported at load time: {leaked}"


def test_every_submodule_imports():
    for name in _all_submodule_names():
        importlib.import_module(name)


def test_bare_import_is_free_of_the_scientific_stack():
    """Measured in a CLEAN subprocess: an in-process check cannot tell whether
    numpy arrived via physmap or via pytest's own plugins."""
    code = (
        "import sys; import physmap; "
        f"print(','.join(sorted(m for m in {LAZY_ONLY!r} if m in sys.modules)))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    loaded = [m for m in out.stdout.strip().split(",") if m]
    assert loaded == [], f"bare `import physmap` eagerly loaded: {loaded}"


def test_guardrail_import_is_rdflib_free():
    code = (
        "import sys; import physmap.guardrail; "
        "print(','.join(sorted({m.split('.')[0] for m in sys.modules} "
        f"& {set(_roots(FORBIDDEN_AT_IMPORT))!r})))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    leaked = [m for m in out.stdout.strip().split(",") if m]
    assert leaked == [], f"importing the guardrail pulled: {leaked}"
