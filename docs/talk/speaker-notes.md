# Speaker notes — one section per technical figure

Plain English, short sentences, meant to be said aloud. Each section has: what is on screen,
what to say, what to point at, what to answer if asked, and what not to say. Figures and their
captions: [`figures/README.md`](figures/README.md).

---

## Applicability assurance: the x/D entrance region — `bench_1_naca_entrance`

**On screen:** measured Nu against x/D. Grey rings are the fully developed points. Black dots are
the entrance region. A line at x/D = 10. Counts on the right.

**Say:**

- "A classic case. A heated pipe. The prediction comes from the Gnielinski correlation, which
  uses Re and Pr and is validated for fully developed flow — from x/D = 10 on."
- "At the entrance, Re and Pr are ordinary — the same curves. What is new is x/D, and nothing
  that uses only Re and Pr can see it."
- "Against the measurement: within the numerical-error threshold on all 40 fully developed
  points. Over it on 9 of the 45 entrance points, all near the inlet."
- "PhysMAP places all 45 entrance predictions outside the closure's supported region. The two
  input-based detectors fire on none — they cannot see x/D."
- "And the other 36? Numerically acceptable. Not physically supported by that closure. Close by
  luck, not by physics."
- Land it: **"Numerical agreement does not by itself establish that a prediction is credibly
  supported. That is applicability assurance."**

**Point at:** the line at x/D = 10, then the 45, then the two zeros.

**If asked:**

- *"So 36 false alarms?"* — "As detection, yes. As applicability, no: they are predictions the
  correlation does not support, that happened to land close. I show both numbers."
- *"Would a lower threshold make the detectors fire?"* — "Not for the right reason. The entrance
  points have the same Re and Pr as the training curves."
- *"Is this the benchmark's NACA row?"* — "The same data. Bank v0.4.1 uses this two-reader read;
  the original bank used an automated read that turned out to be invalid, and I withdrew it."

**Do not say:** "PhysMAP caught 45 errors"; that this shows the causal method works.

---

## Supporting evidence: Casper, across three model types — text slide

**On screen:** a small table. Three model types — Gaussian process, DeepONet, gradient-boosted
trees. For each: passes the home-accuracy check; leaves 4 of 8 deployment errors that only
PhysMAP flags.

**Say:**

- "Now the supporting evidence. Hypersonic transition, from Casper's measurements. The cause of
  failure, tunnel freestream noise, is not a surrogate input."
- "The surrogate is accurate at home: 6 of 159 wrong, held out. Deployed on the quiet tunnel:
  8 of 8 wrong."
- "Swap the surrogate for a DeepONet, or for boosted trees. Each passes the same home-accuracy
  check, and each leaves 4 of 8 errors that only PhysMAP flags."
- "That's because the detectors never look inside the model. What changes with the model is
  only which predictions are wrong."

**If asked:**

- *"Only one dataset?"* — "Only one where two or more model types pass the home check. I don't
  count a model that fails it."
- *"Is it the same four rows each time?"* — "Every model gets all eight wrong, and the flags do
  not depend on the model, so yes."

**Do not say:** "PhysMAP works with any model."

---

## Seven datasets, with their limitations — `bench_4_home_baseline`

**On screen:** one row per dataset. Hollow dot: the surrogate's error rate at home, held out.
Filled dot: when deployed. On the right, the counts and where the home error comes from.

**Say:**

- "The whole benchmark, every dataset. For each: how often is the surrogate wrong at home, and
  how often when deployed?"
- "Casper: 6 of 159 at home, 8 of 8 deployed. Dirker, water in a horizontal tube: 0 of 31, and
  11 of 60. NACA is the case you just saw: 0 of 40, and 9 of 45."
- "Jin and Velazquez: the correlation is wrong almost everywhere, at home too. PhysMAP still
  flags errors the detectors miss there, but those counts cannot show that deployment did it."
- "Marineau: the cause is an input; the detectors see it; PhysMAP adds nothing. Forrest has one
  training row."
- "Two kinds of home error, never mixed. Where the surrogate was fitted to the home rows, I refit
  it without each row. Where it's a published correlation, it was never fitted to them."
- Land it: **"Every dataset stays on the slide, with its limitation. None of this is a rate."**

**If asked:**

- *"How did you decide which ones count?"* — "No gate decides it. The counts are on the slide,
  and each dataset's reading is written out in the report. I did run a Fisher test after seeing
  these counts; it's labelled exploratory, and it decides nothing."
- *"What's the overall catch rate?"* — "I don't pool them. Different physics, different sizes,
  and rows within a dataset aren't independent cases."

**Do not say:** that every count shows a failure deployment created; a rate pooled across
datasets.

---

## The detector counts, per dataset — `bench_3_what_physmap_adds` (backup)

**On screen:** seven datasets in three groups — cause hidden from the inputs, partly visible,
visible. Left: wrong predictions, and the part only PhysMAP flagged. Right: accurate predictions
flagged anyway, because they sit outside the closure's supported region.

**Say, if it comes up:**

- "Per dataset, at the default setting: which wrong predictions did PhysMAP flag that the
  input-based detectors missed? Casper 4 of 8. NACA 9 of 9. Jin 15 of 26, Velazquez 18 of 67 —
  but read those with the home baseline."
- "Where the cause is an input, nothing: 0 of 6 for Marineau."
- "On the right, accurate predictions it flags anyway: 19 for NACA, 16 for Dirker. As detection,
  false alarms. As applicability, predictions the closure does not support."

**Do not say:** "PhysMAP beats OOD detection" without the condition; anything that hides the
flags on accurate predictions.

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
