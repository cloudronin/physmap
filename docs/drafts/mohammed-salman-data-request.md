# DRAFT — data request to Prof. H. A. Mohammed

**Not sent.** For review and editing. Contact details to be confirmed before use; Prof.
Mohammed has moved institutions several times since 2008.

---

**Subject:** Request for underlying data — Mohammed & Salman (2008), *Experimental Heat
Transfer* 21(1)

Dear Professor Mohammed,

I am writing about your 2008 paper with Professor Salman, *Heat Transfer Measurements of
Mixed Convection for Upward and Downward Laminar Flows Inside a Vertical Circular
Cylinder* (Experimental Heat Transfer 21(1):1–23).

I work on credibility checks for machine-learned surrogate models used in place of CFD.
The method asks whether a physical mechanism that a surrogate omits is large enough to
matter for the quantity being predicted. Your vertical-pipe measurements are the
regime-matched experimental anchor for that work: laminar, uniform wall heat flux, both
assisting and opposing flow, with the buoyancy contribution varying across the envelope.

I have the paper and have read it carefully. I am writing with two requests and one
question.

**1. The underlying run data, if it still exists.**

The paper reports 88 test runs. For the work to use them as independent truth — rather
than using Equation 13, which is a fit through them — I would need, per run:

- flow direction (upward or downward),
- Reynolds number,
- Grashof or Rayleigh number,
- entrance-section length (`L/D` = 20, 40, 60 or 80),
- the measured local and/or average Nusselt number,
- and any per-run uncertainty, if it was recorded separately from the ±1.27% global figure.

Even a subset — one entrance length, upward flow only — would be valuable. I appreciate
that data from 2008 may no longer be available, and a reply saying so would itself settle
the question for me.

**2. A question about Figure 16, which I have not been able to resolve.**

Reading the figure's axis as printed, the plotted `Ra/Re` values span roughly 10⁶ to 10⁸.
From the stated envelope (`Gr` 1.1×10⁵–7.4×10⁶, `Re` 400–1600, air) I calculate `Ra/Re` in
the range of about 50 to 13,000. Separately, the fitted line drawn through the upward data
in that figure rises only a few percent across its width, whereas Equation 13 with exponent
0.11868 would rise by about 75% over the same number of decades.

I expect I am misreading either the axis quantity or the figure's scale, and I would be
grateful for a correction. It matters because a CFD model I have built is compared against
Equation 13, and I would like to be confident I am evaluating it at the right argument.

**3. Permission, if the data can be shared.**

If you are able to share data, I would also like to ask whether you would permit the
numerical values — not the paper, figures or text — to be redistributed in an open-source
repository with full attribution to you and Professor Salman and a citation to the paper.
If you would prefer the data be used without redistribution, that is entirely workable and
I will keep it out of the public repository.

I am happy to share what I build with it, and to send the comparison against Equation 13
once it is complete, whether or not it agrees.

With thanks for your time, and for the paper, which is unusually clearly reported.

Yours sincerely,

Vishnu Vettrivel
vettrivel@gmail.com

---

## Notes for the sender, not part of the letter

- **Prof. Salman** may be worth a parallel approach; he was the second author and may hold
  the laboratory records.
- **The Figure 16 question is asked as a request for correction, not as a challenge.** That
  is deliberate, and it is also honest: a misreading on my side is at least as likely as an
  error in the paper, and nothing in the project depends on which it is.
- **Do not send the redistribution request alone.** It reads as an administrative ask; the
  data question is the substantive one and should lead.
- If no reply arrives, the fallback is the alternative sources in
  `docs/findings/truth-source-discovery.md`, not a second approach.
