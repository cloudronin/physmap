# Hostile questions

Each answer is short enough to say aloud. Under it: **Fact** — what the committed evidence
shows, with where to find it; **Interpretation** — what we read into it, labelled as such. If a
question is not here, answer from [`facts-sheet.md`](facts-sheet.md) and say "one run" early.

---

### 1. "Why did you leave gravity out?"

**Say:** "On purpose, to model a reuse. The surrogate was built for forced convection, where
gravity does not vary, so it is not an input — normal for that regime. Then we reuse it where
buoyancy matters. A mixed-convection surrogate should include Ri, Gr or an equivalent."

- **Fact:** the surrogate's inputs are Re, Pr and x/D; all 13 training runs have gravity off.
  The command prints this framing and lists "Gravity should not be omitted" under NOT CLAIMED.
- **Interpretation:** models built for one regime do get reused in another; this test stands
  in for that.

### 2. "Isn't the test artificial?"

**Say:** "Controlled, yes. We built it so gravity is the only difference between the two states,
and so the visible inputs match training exactly. That is what makes it informative: anything
that changes has to come from the physics. The measurement is real — Lewis's data."

- **Fact:** the CFD pair differs only in `constant/g`; the exact input overlap is asserted by the
  command.
- **Interpretation:** real reuse is messier. This isolates one mechanism, which is the point of
  a stress test.

### 3. "Why can't the OOD detector see the change?"

**Say:** "Because the change is not in its inputs. It scores Re, Pr and x/D, and those are
identical with gravity on and off. So its scores are identical — to the last digit. That is the
detector working correctly."

- **Fact:** largest difference between the two states, over every score and percentile: 0.
- **Interpretation:** any detector that sees only these inputs must give the same answer in
  both states.

### 4. "A proper mixed-convection surrogate would include Ri or Gr. Isn't this a straw man?"

**Say:** "A proper one should, and we say so on the slide. This is not a recommendation to leave
it out. It shows what happens when a model built for forced convection is used past its design —
the case PhysMAP is for."

- **Fact:** the command's framing states it; so does every talk document.
- **Interpretation:** if the right physics is in the inputs, an input-based detector can see
  the change. See question 15.

### 5. "Is Lewis one case or twelve?"

**Say:** "One. Test 35A is one run. Its twelve stations are positions along one tube in one
experiment. They are correlated, not independent. That is why there are no rates."

- **Fact:** 12 stations, 9 comparable; Lewis disowns three.

### 6. "Why are there no performance metrics?"

**Say:** "Because one run cannot support them, and the old ones do not hold up. Precision and
recall need many independent cases with their own measured truth. We have one run. The
abstract's numbers were scored against a correlation, and the test was built so the flag and the
label move together."

- **Fact:** `protocols/known-results-declaration.md`; no metric is computed anywhere in the
  package.
- **Interpretation:** a scored validation needs a different, eligible set of independent runs.
  None is in hand.

### 7. "What does 'matched ablation' mean?"

**Say:** "Two CFD runs of the same case. Same mesh, geometry, properties, boundary conditions,
iteration count and extraction. The only change is gravity, on or off — one file. Materiality is
how much the answer changes between them: one minus Nu with gravity off over Nu with gravity
on."

- **Fact:** a recursive diff of the two case directories found only `constant/g` (recorded in
  the manifest); 3000 iterations each; energy closes to +0.15 % and +0.30 %.

### 8. "What belongs to the CFD expert, and what to your method?"

**Say:** "The CFD layer owns whether the simulation represents the physics: the model, mesh,
convergence, energy balance, how Nu is reduced, and whether steady laminar flow is the right
model for this experiment. The credibility layer owns the question put to the surrogate: which
mechanisms apply, the calibrated window, how materiality is computed from the ablation, the
thresholds, and the input contract. PhysMAP uses the CFD's ablation. It does not validate it. If
the CFD gets buoyancy wrong, the materiality is wrong too."

- **Fact:** materiality is computed from the two CFD cases; the grid pair and energy checks are
  CFD-layer evidence and are reported separately.
- **Interpretation:** the method needs CFD expertise to be trustworthy; it does not replace it.

### 9. "Isn't materiality zero with gravity off by construction?"

**Say:** "Yes. With gravity off there is no buoyancy to remove, so the ablation compares a case
with itself. The zero is not the finding. The finding is that with gravity on, materiality grows
down the tube to 0.195 — while the OOD output does not move at all."

- **Fact:** the code pairs the gravity-off case with itself for that state.

### 10. "Isn't materiality just the surrogate's error in disguise?"

**Say:** "Partly, and we say so. The surrogate was trained on gravity-off CFD, and materiality
compares gravity-off with gravity-on CFD, so they share a term. That is why we compute no rate.
The measurement adds something independent: downstream it agrees with the gravity-on CFD within
1.6–6.6 %, so the buoyancy effect is real there."

- **Fact:** the error splits exactly into missing buoyancy times the base model's gap times the
  fit error (facts sheet §6).
- **Interpretation:** the same coupling is why the abstract's precision is not presented as
  validation.

### 11. "The abstract says precision 1.00. Where did it go?"

**Say:** "It is still in the abstract, and I named it earlier. Rebuilding the study showed it was
scored against a fitted correlation, not measurements, and that the construction ties the flag
to the label. So we do not present it as validation. We replaced it with a controlled test and a
smaller claim."

- **Fact:** [`historical-reconciliation.md`](historical-reconciliation.md).

### 12. "Why θ = 0.10? Isn't your flag just a threshold choice?"

**Say:** "θ is not locked, and the headline does not need it: zero against up to 0.195 is a
value. We show 0.10 only as an illustration. It is the original study's value, recorded before
any Lewis work. At 0.05, five stations would flag; at 0.20, none. The protocol will set θ — not
this result."

- **Fact:** the command's THRESHOLDS section; `protocols/protocol.json`.

### 13. "At percentile 75 the OOD detector fires downstream. Doesn't it catch this?"

**Say:** "At 75 it fires on 3 of 9 stations — identically with gravity off, where the surrogate
is right. At that setting it also fires on 97 % of its own training rows between x/D 50 and 100.
It is reacting to sparse training data downstream, not to buoyancy. Its reference setting is 99,
and it is quiet there."

- **Fact:** the sweep line in the command's output; `design_M_low_pct_mechanism.json`.

### 14. "Is your CFD validated?"

**Say:** "No. It is development evidence. From x/D 9.92 on it is grid-converged and within 9.6 %
of the measurement, and within 4.3–6.0 % of Lewis's own laminar prediction. Grid convergence shows
numerical stability, not that steady laminar flow is the right model. The entrance stations are
sensitive to mesh and to how Nu is read off the wall."

- **Fact:** facts sheet §8; `results/lewis35A_vp/grid_pair.json`.
- **Interpretation:** 35A was inspected while the model was built, so agreement on it is not an
  independent test.

### 15. "Why not just give the OOD detector Ri?"

**Say:** "Then it would see this: Ri is 0.29 against a training value of 0, so it would fire.
That is the right design for a mixed-convection model. Two things remain. Ri is one number for
the whole run, so a check on Ri treats every station the same; materiality runs from 0.006 near
the entrance to 0.195 downstream. And someone has to know Ri is the thing to add — naming the
mechanism is the job PhysMAP does."

- **Fact:** Ri = 0.29 for 35A; materiality 0.006 to 0.195 across the comparable stations.
- **Interpretation:** we did not run an OOD detector with Ri as an input. The first sentence
  follows from the definitions, not from a run.

### 16. "Why Lewis 1992? Why only one run?"

**Say:** "35A is the only run in the thesis whose local Nu is printed as numbers; the rest exist
only as plots. We have not scored the others, because Lewis gives no independent way to say which
are steady laminar flow — and we will not pick runs by how well our CFD matches them."

- **Fact:** `data/lewis1992/test_35A_reduction.json`; the eligibility rule in
  `protocols/protocol.json`.

### 17. "What about NVIDIA PhysicsNeMo?"

**Say:** "We make no claim about it. Its OOD check and its physics checks are different things,
and we ran neither. What we tested is an input-based OOD detector — the benchmark's own."

- **Fact:** the command lists this under NOT CLAIMED.

### 18. "Your benchmark says PHYSMAP_WINS. Isn't that a performance claim?"

**Say:** "It is the classifier's label for an observability class, not a score. It means the
failure variable was invisible to the input-based baseline and the closure check caught wrong
rows the baseline missed. Three vehicles have it. We do not turn that into a rate, and it says
nothing about materiality."

- **Fact:** `src/physmap/benchmarks/benchmark_v0_4.py`, `_classify`.

### 19. "Did you tune anything to get this?"

**Say:** "No. The detector is the benchmark's, imported unchanged, with its reference
percentile fixed in code before this work. Design M and its success criteria were committed
before any output existed. θ was not chosen from this result. The one labelling choice — tagging
the matched run with 35A's reported Re and Pr, which differ from its own by -0.062 % and
+0.141 % — was pre-declared."

- **Fact:** `results/lewis35A_head_to_head/PREDECLARE_design_M_matched.md`, committed before
  the results.

### 20. "Your own protocol bars 35A from materiality figures."

**Say:** "From scored ones — any metric, or anything counted as validation. 35A was inspected
while the model was built. So its materiality is shown only as a development demonstration,
labelled that way, and nothing is scored from it. The protocol says exactly that."

- **Fact:** `protocols/protocol.json` — `development_vs_evaluation_split` bars 13A, 16A and
  35A from "any SCORED precision, recall, F1 or materiality figure";
  `threshold_presentation.lewis_design_M` reports 35A's materiality as a development
  demonstration.
- **Fact:** the word "scored" was added on 2026-09-23, because the literal wording contradicted
  the threshold section. The change is recorded in the protocol and in the known-results
  declaration. No run, result, threshold or rule changed.

### 21. "Can I rerun it?"

**Say:** "Yes. Clone the repository, install it, and run physmap stress-test lewis-reuse. It
takes a few minutes, asserts the input contract and the identical OOD scores, and compares
itself with the committed record. It uses committed CFD profiles; it does not rerun OpenFOAM.
On a different machine the last few digits can move. The command allows for that, far below
anything it prints, and says so."

- **Fact:** [`reproduction/README.md`](reproduction/README.md) — exit status 0 from a clean
  public clone.
