"""Controlled vocabulary for closure / vehicle geometry classes.

The geometry-match invariant in `substrate_engine.build_substrate(...)` is an
exact-string comparison between `ClosureEntry.geometry_class` and
`VehicleConfig.geometry.class_`. Both sides MUST draw from this vocabulary.
String constants (not Enum) so YAML serialization is trivial.

A geometry class describes WHAT KIND of flow/heat-transfer configuration a
closure was derived for OR a vehicle realizes. Mismatch between the matched
closure's geometry class and the vehicle's geometry class is exactly the
Sparrow-Cur / Lance & Smith trap that motivates the invariant.

NOTE: geometry is INTENTIONALLY absent from `corpus.jsonl` (gate 6 of the
calibration corpus schema forbids geometry in `physics_coordinates`).
The registry is the place where geometry meets the executable formula.
"""

from typing import Literal


# Forrest mini-channel — Modified Sparrow-Cur was derived for this exact
# configuration (one-sided heated, high aspect ratio rectangular).
NARROW_RECT_CHANNEL_ONE_SIDED = "narrow_rect_channel_one_sided"

# Generic circular pipe — Gnielinski, Dittus-Boelter, Petukhov, Sieder-Tate
# are circular-pipe correlations. Used as REFERENCE closures on other
# geometries (Forrest, Lance & Smith) for Table-4 cross-comparison.
CIRCULAR_PIPE = "circular_pipe"

# Mudhafar smooth micro-tubes (50-950 μm inner diameter). Geometrically a
# sub-class of circular_pipe, but kept distinct because micro-scale physics
# may diverge from macro-scale circular-pipe closures.
CIRCULAR_MICRO_TUBE_SMOOTH = "circular_micro_tube_smooth"

# Mudhafar rough micro-tubes (Ra 5.3-60 μm). Roughness puts the flow outside
# all standard smooth-pipe correlations.
CIRCULAR_PIPE_ROUGH = "circular_pipe_rough"

# Lance & Smith / Pohlhausen — external flat-plate laminar forced.
FLAT_PLATE_EXTERNAL_FORCED = "flat_plate_external_forced"

# Lance & Smith / McAdams — vertical-plate laminar natural convection.
VERTICAL_PLATE_EXTERNAL_NATURAL = "vertical_plate_external_natural"

# Lance & Smith / Churchill — mixed-convection assisting flow on flat plate.
# This is the matched geometry for the L&S substrate.
FLAT_PLATE_EXTERNAL_MIXED = "flat_plate_external_mixed"

# NACA TN-1451 — circular pipe with entrance-region effects (x/D matters).
# Per v0.2 steelman, NACA's matched closure is Gnielinski (circular_pipe),
# applied to this geometry as the documented practitioner habit (aggregate
# HE surrogates omit x/D). The Hausen multiplicative correction lives in
# the substrate as a justification signal; it's not a closure family.
CIRCULAR_PIPE_ENTRANCE_REGION = "circular_pipe_entrance_region"

# Casper hypersonic sharp cone — boundary-layer transition driven by tunnel
# freestream disturbance (Pate-Stainback noise validity boundary). Aerospace
# domain; matched closure carries the freestream-noise validity bound.
HYPERSONIC_SHARP_CONE = "hypersonic_sharp_cone"

# Marineau hypersonic blunt cone — transition driven by entropy-layer / shock
# interaction (nose bluntness). Aerospace domain; matched closure carries the
# entropy-layer/shock-interaction (S_T/X_SW) validity bound.
HYPERSONIC_BLUNT_CONE = "hypersonic_blunt_cone"


GeometryClass = Literal[
    "narrow_rect_channel_one_sided",
    "circular_pipe",
    "circular_micro_tube_smooth",
    "circular_pipe_rough",
    "flat_plate_external_forced",
    "vertical_plate_external_natural",
    "flat_plate_external_mixed",
    "circular_pipe_entrance_region",
    "hypersonic_sharp_cone",
    "hypersonic_blunt_cone",
]


ALL_GEOMETRY_CLASSES: frozenset[str] = frozenset({
    NARROW_RECT_CHANNEL_ONE_SIDED,
    CIRCULAR_PIPE,
    CIRCULAR_MICRO_TUBE_SMOOTH,
    CIRCULAR_PIPE_ROUGH,
    FLAT_PLATE_EXTERNAL_FORCED,
    VERTICAL_PLATE_EXTERNAL_NATURAL,
    FLAT_PLATE_EXTERNAL_MIXED,
    CIRCULAR_PIPE_ENTRANCE_REGION,
    HYPERSONIC_SHARP_CONE,
    HYPERSONIC_BLUNT_CONE,
})


def assert_known_geometry(geometry_class: str) -> None:
    """Raise ValueError if the string is not in the controlled vocabulary.

    Both ClosureEntry construction and VehicleConfig loading call this to fail
    fast on typos (cheap defense against the silent-string-mismatch class of
    bug the invariant is designed to catch).
    """
    if geometry_class not in ALL_GEOMETRY_CLASSES:
        raise ValueError(
            f"Unknown geometry_class {geometry_class!r}. "
            f"Must be one of: {sorted(ALL_GEOMETRY_CLASSES)}. "
            f"Add it to physmap/closures/geometry_classes.py if it's a new "
            f"configuration; do NOT silently accept unknown strings — the "
            f"geometry-match invariant compares strings exactly."
        )
