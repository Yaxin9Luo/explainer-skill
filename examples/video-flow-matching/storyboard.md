# Storyboard — Flow matching: what the network learns

## Color legend (fixed for the whole video)
Re-themed in 2026-10 with a color-blindness simulation (deuteranopia, protanopia, tritanopia); the old red/green pair for conditional vs marginal was ΔE 9 for deuteranopes. Every color also has a second, color-free cue.
- LIGHT GREY `#E0E0E0` = noise: x0, p0 = N(0,1) (p0 is p_t at t = 0, so it shares the neutral density color)
- BLUISH GREEN `#009E73`, dots = data: x1, q = ½δ(−2) + ½δ(+2)
- ORANGE `#E69F00`, DASHED lines = per-sample (conditional) straight lines, their densities, and their target x1 − x0
- LIGHT BLUE `#9CC8FF`, SOLID lines = marginal velocity u_t(x), its field and its (curved) trajectories
- PURPLE `#B07CFF` = the network v_θ and the sampler that queries it (Euler steps)
- WHITE/GREY = axes, neutral labels, intermediate densities p_t

Times below are sentence starts from the current `audio/cues.json`. 
## Layout zones
Title top (y≈3.4). Main stage: (t, x) plot on the left, t∈[0,1] horizontal, x∈[−3,3] vertical,
centered at (−2.8, −0.35). Right panel (x≈1.6…6.9) for formulas and tables. Captions bottom (y≈−3.45).

## Intro (23.0 s) — 2-D teaser
[0]   0.05 "How do you turn noise into data?"          title; grey 2-D Gaussian cloud fades in center; faint green target clusters left-up / right-down
[1]   2.35 "…velocity field."                          purple arrow grid (field at t=0) grows in; label "velocity field v_θ(x,t)"
[2]   5.09 "…at every point and time…"                 t counter appears; t sweeps 0→0.7→0 and arrows change with it (dots fixed)
[3] 11.20 "…start from noise and follow the arrows."  t 0→1: dots flow along the field into the two green clusters
[4] 14.72 "But there is a puzzle."                     everything dims to 0.25
[5] 15.96 "…target it can never match exactly."       loss formula, target (x1 − x0) orange, "min > 0" note
[6] 19.81 "…what it learns, and why that works."      three keyword chips: "what it learns · why it works · how to sample"

## Path (40.8 s)
[0]   0.05 "…simplest case, one dimension."            title "Setup: 1-D, straight paths"; axes Create
[1]   2.81 "Time runs from zero to one…"               t-axis and labels 0, 1 Indicate; small dot sweeps along t axis
[2]   6.34 "…noise, x0, standard Gaussian."            grey sideways density at t=0 grows; label x0 ~ N(0,1)
[3] 11.41 "At time one we have data, x1."             green dots at (1, ±2) pop in; label x1
[4] 13.75 "…two points, ±2, prob ½."                  right panel: q = ½δ₋₂ + ½δ₊₂; dot labels "½"
[5] 19.89 "Pick one noise sample and one data point…" grey dot x0=−0.8 at t=0; (1,2) indicated; orange line Create
[6] 25.31 "At time t, the point is (1−t)x0 + t x1."   formula x_t = (1−t)x0 + t x1; white dot slides along line 0→0.6
[7] 31.84 "Its velocity … x1 − x0."                    formula dx_t/dt = x1 − x0 = 2.8 (orange); orange tangent arrow on the dot
[8] 36.21 "…same at every time…constant speed."       dot+arrow slide 0.6→1→0.2; arrow never changes; "same at every t"

## Loss (35.7 s)
[0]   0.05 "Training uses this velocity as target."    previous plot state; title "Training: conditional flow matching"
[1]   3.67 "Sample a time, a noise point, a data point." right panel: t~U[0,1], x0~N(0,1), x1~q appear one by one; dashed t=0.6 line
[2]   6.92 "Form the point x_t on their line."         white x_t dot on the orange line at t=0.6
[3]   9.24 "The network sees x_t and t … squared error." loss formula (v_θ purple, target orange); purple arrow from x_t (prediction) next to orange arrow (target)
[4] 16.14 "This is the conditional FM loss."          "L_CFM" box Indicate
[5] 19.04 "Now draw many such pairs."                 14 more orange lines Create (lagged), single example dims
[6] 20.86 "The straight lines cross."                 small white circles flash at several crossings
[7] 22.85 "…x = 0 at time one half."                  white dot at (½, 0) with dashed guides
[8] 26.29 "…slope +4 … slope −4."                     two bold orange lines (−2→+2 and +2→−2) through it; others dim; labels +4, −4
[9] 30.99 "Same input, two targets."                  right: "(x=0, t=½) → +4 or −4"
[10] 33.48 "Loss can never reach zero."               right: "⇒ min_θ L_CFM > 0"

## Marginal (40.7 s)
[0]   0.05 "What does the network learn?"              title; small plot (left) with point (½,0) and the ±4 lines
[1]   1.51 "best prediction = average of targets"     argmin_c E(Y−c)² = E[Y]; light-blue flat arrow at the point "avg = 0"
[2]   6.46 "…all lines through x at time t."           both lines through the point Indicate
[3] 10.69 "…marginal velocity u_t(x)."                light-blue u_t(x) appears
[4] 14.00 "…conditional expectation…"                 u_t(x) = E[x1 − x0 | x_t = x]
[5] 20.25 "Now expand the loss around it."            plot fades; L_CFM moves top; expanded square with (v_θ − u_t) + (u_t − (x1−x0))
[6] 22.23 "First term: distance to u_t."              term 1 boxed LIGHT-BLUE, tag "L_FM: what we want"
[7] 26.27 "Second term: variance, no θ."              term 2 boxed GREY, tag "variance, no θ"
[8] 30.90 "Cross term zero…"                          cross term appears then gets "= 0" with reason E[x1−x0 | x_t] = u_t
[9] 34.90 "same gradients as marginal loss"           ∇_θ L_CFM = ∇_θ L_FM boxed

## Transport (35.6 s)
[0]   0.05 "Why is u_t the field we want?"             title; axes + grey p0 + green dots
[1]   1.84 "…distribution of x_t at a few times."     white sideways density profile appears at t=0
[2]   5.05 "…one Gaussian, two bumps, two points."     profile slides t: 0→0.95, leaving faint copies at 0.25, 0.5, 0.75
[3] 10.51 "Each line moves its own conditional distribution." at t=½: two orange dashed component bumps (½N(±1, ½²)) under the white sum
[4] 17.10 "…weighted by how likely each line is"     formula u_t(x) = Σ w(x1|x,t) u_t(x|x1), w posterior
[5] 23.79 "Continuity equation linear in p·u"         conditional eq (orange) → average over x1 → marginal eq (light-blue)
[6] 28.14 "…moves the whole noise distribution…"     p0 (grey) —u_t→ p1 (green) labels; formulas dim
[7] 33.05 "Following u_t from noise gives data."      five light-blue trajectories drawn from grey to green

## Example (36.2 s)
[0]   0.05 "…real numbers, at time one half."          title; axes; dashed t=½ line
[1]   3.30 "At x = 0, targets +4 and −4."              point (½,0); two orange lines and orange arrows +4/−4; table row
[2]   8.40 "Equally likely, marginal = 0."             weights ½, ½; u = ½·4 + ½·(−4) = 0; light-blue flat arrow
[3] 13.28 "…a value it never saw as a target."        light-blue 0 Indicate; tag "never a target"
[4] 17.52 "Move to x = ½."                            old arrows fade; dot slides to (½, ½)
[5] 19.85 "Toward +2: target +3."                     orange line (0,−1)→(1,2), arrow +3
[6] 22.80 "Toward −2: target −5."                     orange line (0,3)→(1,−2), arrow −5
[7] 25.98 "Posterior weights not equal."              two conditional densities at t=½ (sideways); heights at x=½ marked; w ∝ N(½; ±1, ½²)
[8] 28.25 "≈ 98% and 2%."                             weights 0.982 / 0.018; −5 line fades to 0.15
[9] 31.20 "Marginal ≈ 2.86 toward +2."                u = 0.982·3 + 0.018·(−5) ≈ 2.86; light-blue arrow at the point

## Field (28.1 s)
[0]   0.05 "…whole marginal field."                    light-blue slope-field arrows grow over the plane
[1]   3.74 "Closed form: (E[x1|x_t=x] − x)/(1 − t)"    formula, plus this data's 2·tanh(2tx/(1−t)²)
[2]   9.72 "Follow the field from many noise samples." 13 light-blue trajectories Create from grey x0's
[3] 12.47 "Curved, do not cross."                     field dims; trajectories thicken
[4] 16.14 "…hesitate, then split."                    the two trajectories nearest 0 highlighted; circle at the split region
[5] 20.07 "Compare the training lines."               faint orange straight lines fade in
[6] 21.74 "Straight, but they cross."                 crossing circles flash on orange lines
[7] 24.00 "Deterministic map noise → data."           "x0 > 0 ↦ +2, x0 < 0 ↦ −2" tag; orange lines fade

## Sampling (34.0 s)
[0]   0.05 "Draw x0 from the Gaussian."                title; axes; faint light-blue field; grey dot at (0, 0.4)
[1]   3.00 "Solve dx/dt = v_θ(x,t) from 0 to 1."      ODE formula (purple v_θ); faint light-blue exact trajectory from 0.4
[2] 11.26 "Euler's method."                           x_{k+1} = x_k + h·v_θ(x_k, t_k)
[3] 13.89 "Step of size h…evaluate again"             (scaffold arrow) "h" brace on t axis
[4] 19.21 "x0 = 0.4, four steps of ¼."                table k | t_k | x_k with first row 0 | 0 | 0.40
[5] 24.57 "0.30, 0.37, 1.09, 2."                      4 purple segments drawn in turn, table rows filled
[6] 31.38 "Lands on +2."                              final dot on (1,2) Indicate

## OneStep (26.4 s)
[0]   0.05 "Only one step?"                            title; axes; grey density; green dots
[1]   1.79 "At t=0, x_t carries no info about data."  t=0 line highlighted; "x_0 ⟂ x_1"
[2]   5.71 "u_0(x) = E[x1] − x."                       formula
[3]   9.49 "Mean 0 → velocity −x0."                    = −x; light-blue arrows on t=0 line pointing to 0
[4] 13.69 "One step sends every sample to 0."        7 purple straight segments from x0's to (1,0); dot at (1,0)
[5] 18.02 "Not a data point."                         white cross + "mean, not data"
[6] 19.73 "Straight lines ≠ straight marginal paths." curved light-blue trajectories over faint orange lines
[7] 23.16 "Curvature → several steps."                the 4-step purple path from Sampling reappears, lands at 2

## Recap (30.0 s)
[0..6] one line per sentence, stacked left-aligned, colored by legend:
  v_θ(x,t) · target x1−x0 on x_t=(1−t)x0+t x1 · v* = u_t(x)=E[x1−x0|x_t=x] · u_t moves p0 → p1 · min L_CFM = E Var > 0 · sample dx/dt = v_θ, t: 0→1
