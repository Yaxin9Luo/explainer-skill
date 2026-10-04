The rule is short: **for one sample, the clipped objective has zero gradient only when r has already moved past the clip edge in the direction the advantage asks for.**

The objective is L = min(r·A, clip(r, 1−ε, 1+ε)·A), with r = π_θ(a|s) / π_θ_old(a|s).

- **A > 0** (make the action more likely): the slope in r is A up to r = 1+ε. Above 1+ε the curve is flat at (1+ε)·A, so the gradient is **0**.
- **A < 0** (make the action less likely): the curve is flat at (1−ε)·A for r < 1−ε, so the gradient is **0** there. Above 1−ε the slope is A.
- **A = 0**: flat everywhere.

Why: the min always picks the more pessimistic term. The clipped term is constant outside [1−ε, 1+ε].
- If r has gone past the edge in the direction A wants, the clipped term is the smaller one, so the min uses it, and the slope is 0. No more push.
- If r has gone past the edge the other way (A > 0 with r < 1−ε, or A < 0 with r > 1+ε), r·A is the smaller term. The min keeps it, and the full slope A stays. The clip never stops PPO from correcting a bad move.

So ε sets *where* the flat part starts, and the sign of A sets *which side* is flat. |A| only sets how steep the sloped part is.

The policy gradient goes through r: ∇_θ L = (∂L/∂r) · r · ∇_θ log π_θ(a|s). At the start of each update, r = 1 for every sample, so the first step is the plain policy gradient. The clip only takes effect in later epochs and minibatches, after r has drifted.

I built a page to play with this: `index.html`. Open it with

```
open index.html        # macOS; Linux: xdg-open index.html
```

It has sliders for ε, A, and r. It plots L(r) with both terms and shades the zero-gradient region, plots ∂L/∂r under it, and adds a map of the whole (r, A) plane. The "Try this" cards animate the key cases. You can also set a starting state in the URL, e.g. `index.html?A=-1&r=1.6` (the "wrong way" case).
