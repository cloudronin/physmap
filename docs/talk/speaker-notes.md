# Speaker notes — one section per technical figure

Plain English, short sentences, meant to be said aloud. Each section has: what is on screen,
what to say, what to point at, what to answer if asked, and what not to say. Figures and their
captions: [`figures/README.md`](figures/README.md).

---

## The x/D entrance region — `bench_1_naca_entrance`

**On screen:** measured Nu against x/D. Grey rings are training points, fully developed flow.
Black dots are the entrance region. A line at x/D = 10. Three counts on the right.

**Say:**

- "A classic case. A heated pipe. We train a surrogate on the fully developed flow, using Re and
  Pr, and then use it at the entrance."
- "At the entrance, Re and Pr are ordinary — they are the same curves. What is new is x/D, and
  the surrogate never had it."
- "The correlation behind it is only validated from x/D = 10. Left of the line, it is outside
  its range."
- "PhysMAP's closure check fires on all 45 entrance points. The two input-based detectors fire on
  none. They are not wrong about the inputs. They just cannot see x/D."
- "This is the core of PhysMAP: a check on a variable the detectors cannot see. The next slide
  shows it across seven datasets. The causal question comes later, and is separate."

**Point at:** the 45 and the two zeros.

**If asked:**

- *"45 here, 47 in the benchmark?"* — "The example uses its own split; the benchmark's NACA cell
  uses another, 47 test rows. Same pattern in both."
- *"Would a lower threshold make them fire?"* — "Not for the right reason. The entrance points
  have the same Re and Pr as the training curves."

**Do not say:** that this shows the causal method works.

---

## What PhysMAP adds, across seven datasets — `bench_3_what_physmap_adds`

**This is the point of the talk.** Give it time.

**On screen:** seven datasets in three groups — cause hidden from the inputs, partly visible,
visible. Left: the surrogate's wrong predictions (grey) and the part PhysMAP caught that the OOD
detectors missed (green), with "20 of 20"-style counts. Right: right predictions PhysMAP flagged
anyway.

**Say:**

- "The same idea, on seven published datasets in two domains. For each one: which wrong
  predictions did PhysMAP catch that the input-based detectors missed — and what did it cost?"
- "Top group: the cause of failure is hidden from the surrogate's inputs. Here PhysMAP catches
  what the OOD detectors can't. All 20 at the pipe entrance. 4 of 8 in the hypersonic case. 15 of
  26 for supercritical CO2."
- "Middle group: the cause is partly visible. It still helps: 18 of 67, and 2 of 11."
- "Bottom group: the cause is an input. The OOD detectors already see it, and PhysMAP adds
  nothing — 0 of 6. That is the control, and it is the right answer."
- "And the cost, on the right. The closure check flags anything outside its tested range, even
  when the surrogate happens to be right: 24 false alarms at the pipe entrance, 16 for Dirker."
- Land it: **"Where the cause of failure isn't one of the surrogate's inputs, PhysMAP catches
  what the OOD detectors can't. Where it is, it adds nothing. And it costs false alarms."**

**Point at:** the NACA bar, then the Marineau bar, then the right panel.

**If asked:**

- *"What's the overall catch rate?"* — "I don't pool them. Each dataset is a different physics
  and a different size, and rows within a dataset aren't independent cases. The counts are per
  dataset, on purpose."
- *"Why do the partly visible ones catch less?"* — "Because the OOD detectors see part of the
  cause there, so more of the wrong predictions are already theirs."
- *"How does it know when to override the OOD detectors?"* — "At setup it classes each bounded
  variable as visible to the surrogate's inputs or not. It overrides only on the hidden ones."
- *"What about Forrest?"* — "One training row, so no detector could be fitted. Not tested."

**Do not say:** a rate pooled across datasets; "PhysMAP beats OOD detection" without the
condition; anything that hides the false alarms.

---

## Seven-vehicle benchmark, in full — `bench_2_seven_vehicles` (backup)

**On screen:** a table of seven datasets: domain, failure variable, observability, outcome, and
the licence basis of the data.

**Say, if it comes up:**

- "The full table behind the chart: each dataset's failure variable, how visible it is, the
  benchmark's outcome label, and where the data comes from."
- "Forrest is weak, and I will say so: its own data file calls its values visual estimates for
  triage, and it has one training row. Its result is short-circuited, not earned."
- "None of this is evidence about materiality — that is a separate question."
- "It all reruns from a clone: physmap benchmark run."

**If asked:**

- *"Did you have permission for the data?"* — "Two of the seven carry a licence. Five ship
  without one, four of those against publisher terms. Numbers only, no figures or papers, and
  they come out if anyone objects."
- *"Jin is a vertical mixed-convection tube. Isn't that your causal case?"* — "Same geometry
  family, different question. Jin measures whether the buoyancy parameter is visible. It computes
  no ablation and no materiality."

**Do not say:** any rate across datasets, such as "three out of seven".

---

## The input contract — `lewis_1_input_contract`

**On screen:** training on the top left, deployment on the bottom left, the three visible inputs
in the middle, what neither model receives below them, then the surrogate, the OOD detector and
PhysMAP on the right.

**Say:**

- "This is the setup for the Lewis test. On the left, the training data: thirteen CFD runs of
  forced convection. Gravity is off in all of them, because in that regime it did not vary."
- "In the middle, the inputs. The surrogate and the OOD detector get the same three: Re, Pr and
  x/D."
- "Below: what neither gets. Gravity, Richardson number, Grashof number, heat flux."
- "Bottom left is the deployment, Lewis's Test 35A. Every one of its visible inputs is a
  training input. From the inputs' point of view, nothing is new."
- "PhysMAP reads something else: the mechanism. With gravity on, Ri is 0.29. Training only ever
  saw Ri = 0."

**Point at:** the grey box, "Not an input to either".

**If asked:**

- *"Why is one training run at 35A's own operating point?"* — "To remove the input gap on
  purpose. Without it, the detector fires because 35A sits between training runs. That version is
  in backup, and it fires identically with gravity on and off."
- *"Is the OOD detector handicapped?"* — "No. It gets every input the surrogate gets, position
  included."

**Do not say:** "we hid gravity from the detector". Gravity is not an input to either model.

---

## Same inputs, two physical states — `lewis_2_control_vs_gravity_on`

**On screen:** four panels over the same twelve positions along one tube. Blue is gravity off,
orange is gravity on, black is the surrogate. Hollow markers are stations Lewis disowns.

**Say:**

- "Four views of one run, twelve positions along the tube."
- "Top left: the black line is the surrogate. Blue is gravity-off CFD — the control. The line
  goes straight through it. Orange is what Lewis measured, with gravity on."
- "Top right: the error. Against the control, within 0.06 %. Against the measurement, 17–18 %
  low by the end of the tube."
- "Bottom left: the OOD detector. Rings are gravity off, dots are gravity on. The same score at
  every station, and well under its threshold."
- "Bottom right: materiality. Zero with gravity off. With gravity on, it rises to 0.195."
- Land it: **"Same inputs, same OOD scores. Different physics, different materiality — and
  where materiality is largest, the surrogate is 17–18 % off."**

**Point at:** the downstream orange points in the top right, then the same stations in the
bottom right.

**If asked:**

- *"What is the +63.0 %?"* — "x/D 0.31. Lewis disowns it, and 0.85, because of heat conducting
  along the tube wall near the start of heating; 159.33 is marked suspect. They are hollow and
  left out of every summary."
- *"What about the errors at 2.45 and 16.32?"* — "Those come from the base model: the
  gravity-on CFD itself differs from the measurement there. PhysMAP checks buoyancy, not that."
- *"Is materiality taken from the measurement?"* — "No. It comes from the two CFD cases. The
  measurement is what the surrogate is scored against."

**Do not say:** "PhysMAP flagged these stations" as a verdict. Do not say "twelve cases".

---

## The OOD scores are identical — `lewis_3_ood_identical`

**On screen:** two square plots. Each point is one station: its score with gravity off across,
with gravity on up. Shaded: where the detector would fire.

**Say:**

- "Each point is one station. Across is its OOD score with gravity off. Up is the same score
  with gravity on."
- "Every point sits on the diagonal. The largest difference, over both scores and every
  operating percentile, is zero."
- "That is not a failure. The detector did its job. The inputs were the same, so the scores are
  the same. The change that mattered was not an input."

**Point at:** the diagonal, then the empty shaded region.

**If asked:**

- *"Would a different threshold help?"* — "No. The scores are identical, so any threshold gives
  the same answer in both states."

**Do not say:** "the OOD detector failed" or "OOD detection doesn't work".

---

## Materiality is continuous — `lewis_4_materiality`

**On screen:** left, materiality along the tube with the illustrative θ as a dashed line. Right,
how many comparable stations would flag at each θ.

**Say:**

- "Left: materiality along the tube. With gravity on, it grows from almost nothing at the
  entrance to 0.195 near the end. With gravity off it is zero — there is no buoyancy to remove."
- "The dashed line is θ = 0.10. It is illustrative. It is the original study's value, and we have
  not locked θ."
- "Right: what θ would change. For any θ up to 0.195, at least one station flags with gravity
  on. With gravity off, none at any θ. So the headline does not depend on θ."

**Point at:** the flat blue line on the right.

**If asked:**

- *"Why not lock θ now?"* — "Choosing it after seeing this result would be tuning. The protocol
  sets it."
- *"Isn't zero with gravity off automatic?"* — "Yes, by construction. The finding is the
  gravity-on profile, and that the OOD output does not move while it does."

**Do not say:** "three stations are untrustworthy".

---

## The control table — `lewis_5_control_table`

**On screen:** two rows — gravity off and gravity on — against surrogate error, OOD detector,
materiality and the illustrative θ.

**Say:**

- "One-slide summary. Two rows. One difference between them: gravity. Gravity is not an input."
- "Gravity off: within 0.06 %, OOD quiet, materiality zero."
- "Gravity on: 17–18 % off, the same OOD scores, materiality up to 0.195."
- "One run. No rates."

**If asked:** use [`hostile-questions.md`](hostile-questions.md).

**Do not say:** anything that sounds like a scorecard.
