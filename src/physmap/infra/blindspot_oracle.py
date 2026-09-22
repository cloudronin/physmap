"""PhysMAP Step 0 (S0.1) — two-mechanism hemolysis apparatus (truth + closures + surrogate).

The constructed-but-physically-motivated truth/closure pair for the blind-spot pilot.
Two distinguishable hemolysis mechanisms feed one QoI (the hemolysis index HI):

  shear damage    S(tau)  — instantaneous, driven by shear stress tau
  exposure damage E(t)    — cumulative, driven by residence time t
  HI = S + E              — additive, so the mechanism contributions stay separable

Each mechanism's TRUTH saturates (hemolysis saturates as cells are destroyed); each
CLOSURE is a power-law fit on its own calibration box only (tracks truth in-box,
OVERSHOOTS beyond — truth saturates, the power-law does not). A surrogate is trained on
the closure across the full envelope, so it is confident even in the extrapolation
region where the closure is wrong. That confident-but-wrong region is the candidate
blind spot.

Parameters are chosen so (a) the closures fit their box well, (b) extrapolation error is
material at plausible saturation, and (c) materiality genuinely FLIPS across the grid
(shear dominates at high tau, exposure at low-tau/high-t) — the precondition for the
causal-vs-naive lift to be testable. The choice is VERIFIED by coherence_report(), not
eyeballed (same discipline as the synthesizer coupling fix).

Torch-free: numpy + scikit-learn only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# ── operating envelope (normalized shear tau, normalized residence time t) ────
# box = calibration region (closures fit here); envelope = surrogate training span.
TAU_LO, TAU_CAL_S, TAU_HI = 1.0, 3.0, 6.0
T_LO, T_CAL_E, T_HI = 1.0, 3.0, 6.0

# ── truth: saturating exponential per mechanism ───────────────────────────────
# 1 - exp(-(k x^a)) is power-law-like (~ k x^a) below the box edge so a power-law
# closure fits the box, and bends toward the ceiling beyond it.
# Shear grows STEEPLY (as=2.0) and its in-box closure coefficient (Cs ≈ SMAX*KS)
# DOMINATES exposure's (Ce ≈ EMAX*KE), so at high tau shear carries HI and exposure
# is immaterial even when out-of-box (the disc band). Exposure grows SHALLOWLY
# (ae=1.3) but reaches far in t, so at LOW tau / HIGH t (small shear) exposure
# dominates and is material — materiality genuinely FLIPS across the grid.
SMAX, KS, AS = 1.0, 0.12, 2.0       # Cs ≈ 0.12
EMAX, KE, AE = 0.40, 0.08, 1.3      # Ce ≈ 0.032  (< Cs → immaterial at high tau)

THETA_MAT = 0.20    # a mechanism is "material" if its closure contribution fraction >= this
TOL = 0.05          # trustworthy if |HI_sur - HI_true| / (SMAX+EMAX) <= this
N_TRAIN = 300       # surrogate training points across the full envelope
K_ENSEMBLE = 10     # bootstrap ensemble size (guardrail variance signal)
GRID_N = 26         # query grid is GRID_N x GRID_N over the envelope


def s_true(tau: np.ndarray) -> np.ndarray:
    return SMAX * (1.0 - np.exp(-(KS * np.asarray(tau, float) ** AS)))


def e_true(t: np.ndarray) -> np.ndarray:
    return EMAX * (1.0 - np.exp(-(KE * np.asarray(t, float) ** AE)))


def hi_true(tau: np.ndarray, t: np.ndarray) -> np.ndarray:
    return s_true(tau) + e_true(t)


def fit_power_law(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Log-linear least squares: y = C * x**alpha  ->  log y = log C + alpha log x."""
    lx, ly = np.log(np.asarray(x, float)), np.log(np.asarray(y, float))
    alpha, logC = np.polyfit(lx, ly, 1)
    return float(np.exp(logC)), float(alpha)


@dataclass
class Closures:
    """The two power-law closures, each fit on its own calibration box."""
    Cs: float
    alphas: float
    Ce: float
    alphae: float

    def s_clo(self, tau: np.ndarray) -> np.ndarray:
        return self.Cs * np.asarray(tau, float) ** self.alphas

    def e_clo(self, t: np.ndarray) -> np.ndarray:
        return self.Ce * np.asarray(t, float) ** self.alphae

    def hi_clo(self, tau: np.ndarray, t: np.ndarray) -> np.ndarray:
        return self.s_clo(tau) + self.e_clo(t)


def fit_closures(n_box: int = 40, seed: int = 0) -> Closures:
    """Fit each power-law closure to truth samples drawn ONLY from its calibration box."""
    rng = np.random.default_rng(seed)
    tau_box = rng.uniform(TAU_LO, TAU_CAL_S, n_box)
    t_box = rng.uniform(T_LO, T_CAL_E, n_box)
    Cs, alphas = fit_power_law(tau_box, s_true(tau_box))
    Ce, alphae = fit_power_law(t_box, e_true(t_box))
    return Closures(Cs, alphas, Ce, alphae)


def _make_gp():
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel
    # WhiteKernel fixed (not optimized) → no convergence-to-bound warning, deterministic.
    kernel = (ConstantKernel(1.0) * RBF(length_scale=[1.0, 1.0])
              + WhiteKernel(noise_level=1e-6, noise_level_bounds="fixed"))
    return GaussianProcessRegressor(kernel=kernel, normalize_y=True, alpha=1e-8,
                                    n_restarts_optimizer=0, random_state=0)


@dataclass
class Surrogate:
    """GP fit to the CLOSURE across the full envelope + a K-member bootstrap ensemble.
    The surrogate approximates the closure (confident everywhere trained); its error vs
    truth is dominated by the closure's extrapolation error — the point of the pilot."""
    members: list = field(default_factory=list)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.members[0].predict(np.asarray(X, float))

    def ensemble_variance(self, X: np.ndarray) -> np.ndarray:
        preds = np.stack([m.predict(np.asarray(X, float)) for m in self.members], axis=0)
        return preds.var(axis=0)


def train_surrogate(closures: Closures, n_train: int = N_TRAIN, k: int = K_ENSEMBLE,
                    seed: int = 0, box_only: bool = False) -> tuple[Surrogate, np.ndarray]:
    """Train K surrogates on bootstrap resamples of N_train closure evaluations.
    members[0] is the full-sample fit (the point predictor); the rest are bootstrap
    members for the ensemble-variance guardrail. Returns (surrogate, X_train).

    box_only=False → train across the full envelope (the deployed surrogate; confident
    even in the extrapolation region — the blind spot). box_only=True → train ONLY on the
    calibration box (the CONTROL arm: a correctly-scoped surrogate whose guardrails, when
    recomputed against this box-only training distribution, should flag the extrapolation
    region the full-envelope surrogate's guardrails miss)."""
    rng = np.random.default_rng(seed)
    tau_max = TAU_CAL_S if box_only else TAU_HI
    t_max = T_CAL_E if box_only else T_HI
    Xtr = np.column_stack([rng.uniform(TAU_LO, tau_max, n_train),
                           rng.uniform(T_LO, t_max, n_train)])
    ytr = closures.hi_clo(Xtr[:, 0], Xtr[:, 1])
    members = []
    full = _make_gp()
    full.fit(Xtr, ytr)
    members.append(full)
    for b in range(k - 1):
        idx = rng.integers(0, n_train, n_train)         # bootstrap resample
        m = _make_gp()
        m.fit(Xtr[idx], ytr[idx])
        members.append(m)
    return Surrogate(members), Xtr


def query_grid(grid_n: int = GRID_N) -> np.ndarray:
    """Query points over the full envelope. A regular grid spans all four regions; a
    targeted refinement block deliberately populates the disc band (high tau IN box ×
    just-over-box t), where exposure is out-of-calibration but immaterial. Populating it
    by construction is explicitly allowed (the spec: "populate it deliberately"); the
    coherence report verifies those points are genuinely immaterial AND trustworthy."""
    taus = np.linspace(TAU_LO, TAU_HI, grid_n)
    ts = np.linspace(T_LO, T_HI, grid_n)
    base = np.array([[a, b] for a in taus for b in ts], float)
    # disc-band refinement: tau in the upper third of the box, t just beyond the box edge
    d_tau = np.linspace(TAU_LO + 0.6 * (TAU_CAL_S - TAU_LO), TAU_CAL_S, 7)
    d_t = np.linspace(T_CAL_E + 0.15, T_CAL_E + 1.4, 7)
    disc = np.array([[a, b] for a in d_tau for b in d_t], float)
    return np.vstack([base, disc])


@dataclass
class Dataset:
    """All per-query-point quantities the pilot reasons over."""
    X: np.ndarray            # (n, 2) [tau, t]
    hi_true: np.ndarray
    hi_clo: np.ndarray
    hi_sur: np.ndarray
    c_s: np.ndarray          # closure shear contribution
    c_e: np.ndarray          # closure exposure contribution
    in_cal_s: np.ndarray     # tau <= TAU_CAL_S
    in_cal_e: np.ndarray     # t <= T_CAL_E
    material_e: np.ndarray   # c_e / (c_s + c_e) >= THETA_MAT  (closure-based)
    material_s: np.ndarray   # c_s / (c_s + c_e) >= THETA_MAT  (closure-based)
    closures: Closures
    surrogate: Surrogate
    X_train: np.ndarray


def build_dataset(seed: int = 0, grid_n: int = GRID_N, theta_mat: float = THETA_MAT,
                  box_only: bool = False) -> Dataset:
    """box_only=False → the deployed full-envelope surrogate (default, the main pilot).
    box_only=True → the control-arm surrogate trained only on the calibration box; the
    oracle, closures, grid, and all closure-derived fields are IDENTICAL — only the
    surrogate's training distribution (and hence hi_sur + X_train) changes."""
    closures = fit_closures(seed=seed)
    surrogate, Xtr = train_surrogate(closures, seed=seed, box_only=box_only)
    X = query_grid(grid_n)
    tau, t = X[:, 0], X[:, 1]
    c_s, c_e = closures.s_clo(tau), closures.e_clo(t)
    total = c_s + c_e
    return Dataset(
        X=X, hi_true=hi_true(tau, t), hi_clo=closures.hi_clo(tau, t),
        hi_sur=surrogate.predict(X), c_s=c_s, c_e=c_e,
        in_cal_s=tau <= TAU_CAL_S, in_cal_e=t <= T_CAL_E,
        material_e=(c_e / total) >= theta_mat, material_s=(c_s / total) >= theta_mat,
        closures=closures, surrogate=surrogate, X_train=Xtr,
    )


# ── specificity-cell substrate (ensemble experiment, vehicle (a)) ────────────
# Tighter calibration box than the default — leaves a benign out-of-envelope band.
TAU_CAL_S_SPEC = 2.0
T_CAL_E_SPEC = 2.0


class _QuietSurrogate:
    """Stub surrogate for the specificity STAND-IN: predicts closure exactly and
    reports zero ensemble variance. Keeps the guardrail signals silent on the
    out-of-envelope band where truth ≡ closure (the spec's 'baseline FA ≈ 0 by cell
    definition' premise). Duck-types Surrogate's interface used by pilot_compute."""

    def __init__(self, closures: "Closures") -> None:
        self._closures = closures

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, float)
        return self._closures.hi_clo(X[:, 0], X[:, 1])

    def ensemble_variance(self, X: np.ndarray) -> np.ndarray:
        return np.zeros(len(np.asarray(X, float)))


def build_specificity_dataset(seed: int = 0, grid_n: int = GRID_N,
                              theta_mat: float = THETA_MAT,
                              tau_cal: float = TAU_CAL_S_SPEC,
                              t_cal: float = T_CAL_E_SPEC) -> Dataset:
    """Specificity-cell synthetic substrate for the ensemble experiment (STAND-IN).

    Builds a Dataset where:
      - truth ≡ closure ≡ surrogate everywhere (err = 0 by construction; trustworthy.all())
      - the surrogate is a quiet stub (exact closure, zero ensemble variance) so the
        guardrail signals stay silent — matches the spec's 'baseline FA ≈ 0 by cell
        definition' premise; a GP-trained surrogate's variance would fire on
        out-of-envelope points even when truth tracks closure, contaminating the
        baseline reading.
      - the calibration box is tightened (tau_cal, t_cal) so the query grid contains a
        BENIGN OUT-OF-ENVELOPE band: points beyond the box have closure tracking truth
        but are flagged out-of-calibration by naive/causal.
      - materiality (c_s, c_e fractions) varies across the band — some out-of-envelope
        rows are causal-firing (material out-of-cal mechanism), some causal-silent
        (immaterial out-of-cal mechanism); both must be present for H-harm to be
        empirically falsifiable.

    Status: STAND-IN — the EMPIRICAL upgrade is vehicle (b), a grounded convection
    sub-range where the correlation is inside its validated range across a
    materiality-varying sweep.
    """
    closures = fit_closures(seed=seed)
    surrogate = _QuietSurrogate(closures)
    X = query_grid(grid_n)
    tau, t = X[:, 0], X[:, 1]
    c_s, c_e = closures.s_clo(tau), closures.e_clo(t)
    total = c_s + c_e
    # Clip closure to the saturating bound. The corpus_runtime PDE-residual signal
    # checks hi_sur > BOUND (SMAX + EMAX) as a physics constraint; the algebraic
    # closures overshoot this bound at high (tau, t), which would fire the PDE arm
    # as a spurious baseline FA in the specificity cell where truth tracks closure
    # by definition. Clipping hi_sur AND hi_clo to BOUND preserves truth ≡ closure
    # (both clip to the same value) while keeping the PDE signal silent.
    bound = SMAX + EMAX
    hi_clo_raw = closures.hi_clo(tau, t)
    hi_clo_arr = np.clip(hi_clo_raw, 0.0, bound)
    # truth ≡ closure ≡ surrogate everywhere (the specificity condition)
    hi_true_arr = hi_clo_arr.copy()
    hi_sur_arr = hi_clo_arr.copy()
    # Uniform training reference for the OOD guardrail self-calibration. Sampling
    # over the same envelope as the query keeps maha distances comparable, so
    # baseline guardrails fire only on the ~5% Mahalanobis tail.
    rng = np.random.default_rng(seed)
    Xtr = np.column_stack([
        rng.uniform(TAU_LO, TAU_HI, N_TRAIN),
        rng.uniform(T_LO, T_HI, N_TRAIN),
    ])
    return Dataset(
        X=X, hi_true=hi_true_arr, hi_clo=hi_clo_arr,
        hi_sur=hi_sur_arr, c_s=c_s, c_e=c_e,
        in_cal_s=tau <= tau_cal, in_cal_e=t <= t_cal,
        material_e=(c_e / total) >= theta_mat, material_s=(c_s / total) >= theta_mat,
        closures=closures, surrogate=surrogate, X_train=Xtr,
    )


def coherence_report(ds: Dataset | None = None, seed: int = 0) -> dict:
    """Verify the construction is sound (not manufactured): box fit good, extrapolation
    error material, materiality flips, disc_region populated + genuinely trustworthy."""
    if ds is None:
        ds = build_dataset(seed=seed)
    tau, t = ds.X[:, 0], ds.X[:, 1]
    scale = SMAX + EMAX

    # box-fit quality (max relative residual inside each box)
    box_tau = np.linspace(TAU_LO, TAU_CAL_S, 50)
    box_t = np.linspace(T_LO, T_CAL_E, 50)
    s_box_res = float(np.max(np.abs(ds.closures.s_clo(box_tau) - s_true(box_tau)) / SMAX))
    e_box_res = float(np.max(np.abs(ds.closures.e_clo(box_t) - e_true(box_t)) / EMAX))

    # extrapolation error (closure vs truth) at the far corner
    far = np.abs(ds.closures.hi_clo(np.array([TAU_HI]), np.array([T_HI]))
                 - hi_true(np.array([TAU_HI]), np.array([T_HI])))[0] / scale

    err = np.abs(ds.hi_sur - ds.hi_true) / scale
    trustworthy = err <= TOL

    # disc_region = exactly one mechanism out-of-box AND that mechanism not material
    exactly_one_out = (ds.in_cal_s ^ ds.in_cal_e)
    # the out-of-box mechanism: if exposure out (not in_cal_e) it must be immaterial
    exp_out_immaterial = (~ds.in_cal_e) & ds.in_cal_s & (~ds.material_e)
    shear_out_immaterial = (~ds.in_cal_s) & ds.in_cal_e & (~ds.material_s)
    disc = exp_out_immaterial | shear_out_immaterial

    return {
        "box_fit_max_rel_residual": {"shear": round(s_box_res, 4), "exposure": round(e_box_res, 4)},
        "extrapolation_error_far_corner": round(float(far), 4),
        "closure_alphas": round(ds.closures.alphas, 3),
        "closure_alphae": round(ds.closures.alphae, 3),
        "n_grid": len(ds.X),
        "materiality_flip": {
            "frac_exposure_material": round(float(ds.material_e.mean()), 3),
            "frac_shear_material": round(float(ds.material_s.mean()), 3),
        },
        "region_counts": {
            "both_in": int((ds.in_cal_s & ds.in_cal_e).sum()),
            "exactly_one_out": int(exactly_one_out.sum()),
            "both_out": int((~ds.in_cal_s & ~ds.in_cal_e).sum()),
            "disc_region": int(disc.sum()),
        },
        "disc_region": {
            "n": int(disc.sum()),
            "frac_trustworthy": round(float(trustworthy[disc].mean()), 3) if disc.any() else None,
            "mean_exposure_materiality": round(float((ds.c_e / (ds.c_s + ds.c_e))[disc].mean()), 3)
            if disc.any() else None,
        },
        "n_untrustworthy": int((~trustworthy).sum()),
    }


def main(argv=None) -> int:
    import json
    print("PhysMAP Step 0 — oracle coherence report\n")
    print(json.dumps(coherence_report(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
