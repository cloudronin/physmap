"""UQAIS, Uncertainty Quantification for AI Surrogates (pronounced like "ukase").

It accounts for the uncertainty a surrogate inherits from the physics it learned, in Roy and
Oberkampf's accounting, around PhysMAP's two checks.

Aleatory uncertainty (input variability) is propagated by sampling. Epistemic uncertainty is
carried as intervals and never averaged away. The intervals are kept on separate lines:

- **emulation error** -- the surrogate against the simulation it learned, on held-out runs;
- **model form inside the validated range** -- the closure against measurement, a declared
  validation metric;
- **model form outside the validated range** -- PhysMAP's W-SURR-05: no validation evidence
  bounds it, so it is UNBOUNDED unless an extrapolation band is declared and named;
- **omitted mechanism** -- PhysMAP's W-SURR-06: the materiality from a matched ablation, where
  the mechanism is active and material.

The machine-learning UQ toolbox (ensembles, dropout, Bayesian layers, conformal intervals)
quantifies the first of these relative to the training distribution. It is silent about the
others, because they are not in the inputs. `physmap uq` propagates all of them into a
probability box on the quantity of interest and reports each term on its own line. It never
reduces the answer to one number, and "unbounded" is a legal, reported outcome.

Everything here uses numpy and scipy only, imported inside the modules that need them, so a
bare `import physmap` stays free of the scientific stack.
"""
