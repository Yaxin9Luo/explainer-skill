Short version: the network predicts the same thing in both phases, a **velocity** v_θ(x_t, t). Training fits that velocity with regression. Sampling uses the trained velocity as the right-hand side of an ODE and integrates it.

I drew the two phases as two lanes that share one network box: `flow_matching.svg` (open it with `open flow_matching.svg` on macOS or `xdg-open flow_matching.svg` on Linux; it follows your light/dark setting).

**Training (no ODE, one network call per example)**
1. Draw noise x₀ ~ N(0, I), a data point x₁, and a time t ~ U[0, 1].
2. Put a point on the straight line between them: x_t = (1 − t)·x₀ + t·x₁.
3. The target is the velocity of that line, dx_t/dt = x₁ − x₀. It is a constant, so no gradient goes through it.
4. Loss: ‖v_θ(x_t, t) − (x₁ − x₀)‖², averaged over many draws. Update θ.

**Sampling (no target, many network calls)**
1. Start from fresh noise x₀ ~ N(0, I) at t = 0.
2. Call the network to get the velocity v_θ(x_t, t).
3. Take an Euler step: x_{t+h} = x_t + h·v_θ(x_t, t), then t ← t + h.
4. Repeat until t = 1, which takes N = 1/h network calls. The final x₁ is your sample.

**Why the same network works for both**
The training target x₁ − x₀ is different for every pair, even pairs whose lines pass through the same point x at time t. Squared-error regression therefore learns the average: v_θ(x, t) ≈ E[x₁ − x₀ | x_t = x]. That average is a single velocity field, and integrating it from t = 0 to t = 1 moves the noise distribution onto the data distribution.

**The usual mix-ups**
- Training never integrates anything. It regresses at single, randomly chosen points.
- Sampling never sees x₁ − x₀. It only has the learned field.
- Each training path is straight, but the sampling path is usually curved, because the learned field averages many crossing lines. This is why one Euler step is not enough. Rectified-flow "reflow" exists to straighten these paths.
- In this setup the network outputs a velocity, not x₁ and not the noise. Those are other parameterizations, and you can convert between them.

Convention: t = 0 is noise and t = 1 is data, as in Lipman et al. with σ_min = 0 (this is also rectified flow). Many diffusion papers run time the other way, so their signs flip.

If it helps, I can make a small page where you change the number of Euler steps and see how the sample path changes.
