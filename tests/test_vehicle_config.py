"""VehicleConfig tests — schema validation + YAML round-trip + escape-hatch discipline.

Pins three things:

  1. The seven committed benchmark YAMLs load and validate cleanly. Drift
     between the YAML and the registry is caught.

  2. Schema validation catches misconfiguration: unknown top-level keys,
     unknown geometry vocab, missing matched_closure, unknown reference
     closures, wrong cell_bands shape.

  3. The expect_mismatch escape hatch enforces:
       - rationale required when set
       - rationale forbidden when not set (no orphan rationales)
     (The geometry-match invariant itself lives in `substrate_engine`, not
     here; this file tests the LOAD-time discipline only.)
"""

from __future__ import annotations

import pytest
import yaml

from physmap.substrate.vehicle_config import (
    VehicleConfig,
    VehicleConfigError,
    from_dict,
    load_named_vehicle,
    load_vehicle_config,
    _vehicles_dir,
)

VEHICLES_DIR = _vehicles_dir()
SEVEN = ("naca_tn1451", "casper_hypersonic_transition", "jin_sco2_buoyancy",
         "velazquez_sco2", "dirker_water", "marineau_hypersonic_transition", "forrest")


# ── YAML round-trip ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("vid", SEVEN)
def test_committed_yaml_loads(vid: str):
    cfg = load_named_vehicle(vid)
    assert isinstance(cfg, VehicleConfig)
    assert cfg.vehicle_id == vid


def test_forrest_matches_geometry():
    """Forrest's matched closure and vehicle geometry must agree (the
    invariant will be checked by substrate_engine; here we just sanity-pin
    the YAML's intent)."""
    cfg = load_named_vehicle("forrest")
    assert cfg.geometry.class_ == "narrow_rect_channel_one_sided"
    assert cfg.matched_closure_id == "modified-sparrow-cur-asym-narrow-rect-channel-2014"
    assert cfg.expect_mismatch is False


def test_continuous_cells_carry_no_bands():
    """A vehicle with no Re-band cells declares cell_bands.type 'continuous'."""
    payload = _forrest_base()
    payload["cell_bands"] = {"type": "continuous"}
    cfg = from_dict(payload)
    assert cfg.cell_bands.type == "continuous"
    assert cfg.cell_bands.bands == ()


# ── schema-validation guards ────────────────────────────────────────────────

# Use the Forrest YAML as a base and inject deltas; keeps tests self-contained.
def _forrest_base() -> dict:
    return yaml.safe_load((VEHICLES_DIR / "forrest.yaml").read_text())


def test_unknown_top_level_key_raises():
    payload = _forrest_base()
    payload["foo_bar"] = "junk"
    with pytest.raises(VehicleConfigError, match="unknown keys"):
        from_dict(payload)


def test_unknown_geometry_class_raises():
    payload = _forrest_base()
    payload["geometry"]["class"] = "imaginary_geometry"
    with pytest.raises(ValueError, match="Unknown geometry_class"):
        from_dict(payload)


def test_unknown_matched_closure_raises():
    payload = _forrest_base()
    payload["matched_closure_id"] = "not-a-real-closure-2099"
    with pytest.raises(VehicleConfigError, match="not in REGISTRY"):
        from_dict(payload)


def test_unknown_reference_closure_raises():
    payload = _forrest_base()
    payload["reference_closure_ids"] = ["gnielinski-1976", "still-fake-2099"]
    with pytest.raises(VehicleConfigError, match="unknown entries"):
        from_dict(payload)


def test_missing_required_key_raises():
    payload = _forrest_base()
    del payload["domain"]
    with pytest.raises(VehicleConfigError, match="missing required key 'domain'"):
        from_dict(payload)


def test_re_bands_must_have_bands():
    payload = _forrest_base()
    payload["cell_bands"]["bands"] = []
    with pytest.raises(VehicleConfigError, match="requires a non-empty"):
        from_dict(payload)


def test_continuous_must_not_have_bands():
    payload = _forrest_base()
    payload["cell_bands"] = {"type": "continuous", "bands": [{"name": "spurious"}]}
    with pytest.raises(VehicleConfigError, match="must not carry a `bands` list"):
        from_dict(payload)


def test_unknown_cell_bands_type_raises():
    payload = _forrest_base()
    payload["cell_bands"]["type"] = "invented_band_type"
    with pytest.raises(VehicleConfigError, match="not in"):
        from_dict(payload)


def test_band_entry_missing_name_raises():
    payload = _forrest_base()
    payload["cell_bands"]["bands"][0] = {"re_lt": 4000.0}    # name missing
    with pytest.raises(VehicleConfigError, match="missing 'name'"):
        from_dict(payload)


# ── expect_mismatch escape-hatch discipline ─────────────────────────────────

def test_expect_mismatch_requires_rationale():
    payload = _forrest_base()
    payload["expect_mismatch"] = True
    # rationale absent
    with pytest.raises(VehicleConfigError, match="non-empty mismatch_rationale"):
        from_dict(payload)


def test_expect_mismatch_with_empty_rationale_raises():
    payload = _forrest_base()
    payload["expect_mismatch"] = True
    payload["mismatch_rationale"] = "   "    # whitespace only
    with pytest.raises(VehicleConfigError, match="non-empty mismatch_rationale"):
        from_dict(payload)


def test_orphan_rationale_without_expect_mismatch_raises():
    """A mismatch_rationale without expect_mismatch=true is dead text and
    misleading — fail load so it gets noticed."""
    payload = _forrest_base()
    payload["mismatch_rationale"] = "some leftover text"
    # expect_mismatch defaults to False
    with pytest.raises(VehicleConfigError, match="mismatch_rationale is set but"):
        from_dict(payload)


# ── file errors ─────────────────────────────────────────────────────────────

def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_vehicle_config(tmp_path / "does_not_exist.yaml")


def test_empty_yaml_raises(tmp_path):
    p = tmp_path / "empty.yaml"
    p.write_text("")
    with pytest.raises(VehicleConfigError, match="file is empty"):
        load_vehicle_config(p)


def test_non_mapping_yaml_raises(tmp_path):
    p = tmp_path / "scalar.yaml"
    p.write_text("just a string")
    with pytest.raises(VehicleConfigError, match="must be a dict"):
        load_vehicle_config(p)
