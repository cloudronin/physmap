"""Pure Nu(...) closure formulas, extracted from substrate files.

Each function takes keyword-only inputs (so the substrate engine can pass an
input bag and each closure picks what it needs) and returns Nu as a numpy
array. Formulas are byte-faithful copies of the originals — DO NOT alter
the math; the byte-for-byte substrate-migration gate compares numerical
output exactly.

Inputs that may appear in the kwarg bag (not every closure uses every one):
  Re        Reynolds number (turbulent internal flow; or Re_x for flat plate)
  Pr        Prandtl number
  Ra        Rayleigh number (natural convection)
  Nu_forced     pre-computed forced-convection Nu (for Churchill blend)
  Nu_natural    pre-computed natural-convection Nu (for Churchill blend)
  mu_ratio  μ_bulk / μ_wall (Sieder-Tate viscosity correction)
  heating   bool — Dittus-Boelter n=0.4 (heating) vs 0.3 (cooling)
  n         Churchill blend exponent

Each closure declares the kwargs it uses in `registry.ClosureEntry.required_inputs`;
the substrate engine dispatches on that to populate only what each formula needs.
"""

from __future__ import annotations

import numpy as np


# ── internal-flow closures (Re, Pr) ─────────────────────────────────────────

def modified_sparrow_cur_nu(*, Re: np.ndarray, Pr: np.ndarray) -> np.ndarray:
    """Modified Sparrow-Cur (Forrest 2014 Eq. 7): Nu = 0.036·Re^0.76·Pr^(1/3).

    Geometry-matched primary closure for one-sided heated narrow rectangular
    mini-channels with high aspect ratio (alpha* < 0.1). Validated bounds:
    Re in [10000, 70000], Pr in [2.2, 5.4]. Corpus entry:
    modified-sparrow-cur-asym-narrow-rect-channel-2014 (status: extrapolated).

    Original Sparrow & Cur (1982): Nu = 0.0464·Re^0.76 at fixed Pr=2.5,
    isothermal wall, alpha*=0.0556, Re 10000-45000. Forrest 2014 modification:
    Chilton-Colburn analogy gives explicit Pr^(1/3); coefficient adjusted
    0.0464 -> 0.036 consistent with Pr^(1/3) at Pr=2.5; wall BC extended
    from isothermal to uniform heat flux; Re extended empirically to 70000.
    """
    Re = np.asarray(Re, dtype=float)
    Pr = np.asarray(Pr, dtype=float)
    return 0.036 * Re ** 0.76 * Pr ** (1.0 / 3.0)


def gnielinski_nu(*, Re: np.ndarray, Pr: np.ndarray) -> np.ndarray:
    """Gnielinski (1976): Nu_D = (f/8)(Re-1000)Pr / (1 + 12.7*sqrt(f/8)*(Pr^(2/3)-1))
    where f = (0.790*ln(Re) - 1.64)^(-2) is Petukhov's friction factor.

    Geometry: circular pipe. Validated Re in [3000, 5e6], Pr in [0.5, 2000]
    per the corpus calibration entry gnielinski-1976.
    """
    Re = np.asarray(Re, dtype=float)
    Pr = np.asarray(Pr, dtype=float)
    f = (0.790 * np.log(np.maximum(Re, 1.0)) - 1.64) ** (-2.0)
    num = (f / 8.0) * (Re - 1000.0) * Pr
    den = 1.0 + 12.7 * np.sqrt(f / 8.0) * (Pr ** (2.0 / 3.0) - 1.0)
    return num / den


def dittus_boelter_nu(*, Re: np.ndarray, Pr: np.ndarray,
                      heating: bool = True) -> np.ndarray:
    """Dittus-Boelter (McAdams form, 1930): Nu_D = 0.023 Re^0.8 Pr^n.

    n = 0.4 for heating (fluid heated by wall), n = 0.3 for cooling.
    Geometry: circular pipe. Validated Re in [10000, 1.2e6], Pr in [0.7, 160]
    per the corpus calibration entry dittus-boelter-1930.
    """
    Re = np.asarray(Re, dtype=float)
    Pr = np.asarray(Pr, dtype=float)
    n = 0.4 if heating else 0.3
    return 0.023 * Re ** 0.8 * Pr ** n


def petukhov_nu(*, Re: np.ndarray, Pr: np.ndarray) -> np.ndarray:
    """Petukhov (1970): Nu = (f/8)*Re*Pr / [1.07 + 12.7*sqrt(f/8)*(Pr^(2/3)-1)]
    where f = (1.82*log10(Re) - 1.64)^(-2).

    Geometry: circular pipe. NOT IN the calibration corpus (corpus has
    Gnielinski/D-B/Sieder-Tate as the canonical turbulent-circular-pipe
    triple); kept in the registry as reference-only for Forrest's
    Table-4 cross-comparison.
    """
    Re = np.asarray(Re, dtype=float)
    Pr = np.asarray(Pr, dtype=float)
    f = (1.82 * np.log10(np.maximum(Re, 1.0)) - 1.64) ** (-2.0)
    num = (f / 8.0) * Re * Pr
    den = 1.07 + 12.7 * np.sqrt(f / 8.0) * (Pr ** (2.0 / 3.0) - 1.0)
    return num / den


def sieder_tate_nu(*, Re: np.ndarray, Pr: np.ndarray,
                   mu_ratio: np.ndarray | float = 1.0) -> np.ndarray:
    """Sieder-Tate (1936): Nu_D = 0.027 Re^0.8 Pr^(1/3) (mu_b/mu_w)^0.14.

    mu_ratio defaults to 1.0 (no viscosity correction); the substrate
    engine may supply a row-level value if available. Geometry: circular pipe.
    """
    Re = np.asarray(Re, dtype=float)
    Pr = np.asarray(Pr, dtype=float)
    return 0.027 * Re ** 0.8 * Pr ** (1.0 / 3.0) * mu_ratio ** 0.14


# ── external flat-plate / vertical-plate closures ───────────────────────────

def pohlhausen_forced_local_nu(*, Re: np.ndarray, Pr: np.ndarray) -> np.ndarray:
    """Pohlhausen local laminar forced flat-plate: Nu_x = 0.332 Re_x^(1/2) Pr^(1/3).

    LOCAL form (at position x); the length-averaged form is 0.664 Re_L^(1/2) Pr^(1/3).
    The Lance & Smith substrate computes LOCAL Nu at each measurement position
    for like-with-like comparison against the measured local q". Geometry:
    flat_plate_external_forced. Validated Re in [0, 5e5], Pr in [0.6, 50].
    Corpus entry: blasius-pohlhausen-flat-plate-forced-1921.

    The kwarg is named `Re` (not `Re_x`) for uniform-bag dispatch; the substrate
    engine populates Re with the local Re_x value at each row.
    """
    Re = np.asarray(Re, dtype=float)
    Pr = np.asarray(Pr, dtype=float)
    return 0.332 * np.sqrt(np.maximum(Re, 0.0)) * Pr ** (1.0 / 3.0)


def mcadams_natural_local_nu(*, Ra: np.ndarray) -> np.ndarray:
    """McAdams local laminar natural vertical-plate: Nu_x = 0.59 Ra_x^(1/4).

    Validated Ra in [1e4, 1e9], Pr in [0.6, 7] (Pr enters via Ra=Gr*Pr).
    Geometry: vertical_plate_external_natural. Corpus entry:
    mcadams-vertical-plate-natural-1954.
    """
    Ra = np.asarray(Ra, dtype=float)
    return 0.59 * np.maximum(Ra, 0.0) ** 0.25


# ── composite / blender closures ────────────────────────────────────────────

def churchill_mixed_nu(*, Nu_forced: np.ndarray, Nu_natural: np.ndarray,
                       n: float = 3.0) -> np.ndarray:
    """Churchill mixed-convection blend (assisting flow): Nu_M^n = Nu_F^n + Nu_N^n.

    n=3 for assisting flow (standard Churchill exponent). Geometry:
    flat_plate_external_mixed. NOT IN the calibration corpus today; kept in
    the registry as the Lance & Smith matched-prediction surrogate.
    """
    Nu_F = np.asarray(Nu_forced, float)
    Nu_N = np.asarray(Nu_natural, float)
    return (Nu_F ** n + Nu_N ** n) ** (1.0 / n)


def aung_worku_mixed_nu(*, Re: np.ndarray, Pr: np.ndarray) -> np.ndarray:
    """Aung & Worku (1986) mixed forced-natural convection — registered as a
    CORPUS-VALIDITY ANCHOR ONLY, not as an executable predictor.

    This closure exists in the registry so the substrate engine's geometry-match
    invariant and matched-closure lookup resolve for the Stage-3 MIDDLE vehicle
    (Dirker/Meyer/Reid water tube). main's regime framework maps
    MIXED_CONVECTION_HORIZONTAL_TUBE -> this closure; it carries the
    `richardson_number` validity bound (Ri in [0.1, 10]) that the vehicle's
    closure-validity detector reads directly from the corpus. The vehicle's
    surrogate-of-record is a data-driven GP fit (loader
    `dirker_water_richardson_bands`), NOT this correlation, so the Nu formula is
    deliberately unimplemented (the original is a vertical-channel Eq-13 family
    form; porting it to the horizontal-tube geometry is out of scope and unused).
    Raises loudly if ever dispatched as a predictor.
    """
    raise NotImplementedError(
        "aung-worku-mixed-convection-1986 is a corpus-validity anchor "
        "(richardson_number bound) only; it has no executable Nu predictor. The "
        "dirker_water Stage-3 vehicle uses a data-driven GP surrogate, not this "
        "correlation."
    )


def pate_freestream_noise_bound(**kwargs) -> np.ndarray:
    """Pate-Stainback freestream-disturbance transition boundary — CORPUS-
    VALIDITY ANCHOR ONLY, not an executable predictor.

    Registered so the substrate engine's geometry-match invariant + matched-
    closure lookup resolve for the aerospace Casper vehicle (quiet-vs-noisy
    hypersonic transition). It carries the freestream_noise_rms_pitot_pct
    validity bound (conventional tunnels validated for RMS Pitot >= ~0.5%);
    the QUIET deploy points (~0.05%) fall below it and the closure-validity
    detector fires. Casper's surrogate-of-record is a GP transition model
    (loader `casper_hypersonic_transition`), so no Nu/rms formula is needed.
    Raises loudly if ever dispatched as a predictor.
    """
    raise NotImplementedError(
        "pate-stainback-freestream-noise-hypersonic-1980 is a corpus-validity "
        "anchor (freestream_noise_rms_pitot_pct bound) only; it has no executable "
        "predictor. The Casper vehicle uses a GP surrogate."
    )


def marineau_entropy_shock_bound(**kwargs) -> np.ndarray:
    """Marineau entropy-layer / shock-interaction transition boundary — CORPUS-
    VALIDITY ANCHOR ONLY, not an executable predictor.

    Registered so the geometry-match invariant + matched-closure lookup resolve
    for the aerospace Marineau vehicle (bluntness negative control). It carries
    the entropy_layer_shock_ratio (S_T/X_SW) validity bound (>= 0.1 for the
    e^N / 2nd-mode regime); the large-bluntness deploy points fall below it and
    the closure-validity detector fires — but the steelman baseline ALSO fires
    (nose radius is a surrogate input), so PhysMAP correctly declines a clean
    differentiator. Marineau's surrogate-of-record is a data-driven fit (loader
    `marineau_hypersonic_transition`). Raises loudly if dispatched as a predictor.
    """
    raise NotImplementedError(
        "marineau-entropy-layer-shock-interaction-2014 is a corpus-validity "
        "anchor (entropy_layer_shock_ratio bound) only; it has no executable "
        "predictor. The Marineau vehicle uses a data-driven surrogate."
    )
