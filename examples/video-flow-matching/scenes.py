import os, sys; sys.path.insert(0, os.path.expanduser("~/.claude/skills/explainer/scripts"))
from timed import Timed
from manim import *
import numpy as np

# ---------- color legend (see storyboard.md) ----------
C_NOISE = BLUE
C_DATA = YELLOW
C_COND = RED
C_MARG = GREEN
C_NET = "#C77DFF"     # purple: network v_theta and sampler
C_AX = GREY_B

PLOT_C = np.array([-3.1, -0.3, 0])
PANEL_X = 3.85


# ---------- 1-D toy: x0 ~ N(0,1), q = 1/2 delta(-2) + 1/2 delta(+2) ----------
def m1(x, t):
    return 2 * np.tanh(2 * t * x / (1 - t) ** 2)


def u1(x, t):
    return (m1(x, t) - x) / (1 - t)


def gauss(x, mu, sd):
    return np.exp(-0.5 * ((x - mu) / sd) ** 2) / (sd * np.sqrt(2 * np.pi))


def pt_pdf(t):
    sd = max(1 - t, 1e-3)
    return lambda x: 0.5 * gauss(x, 2 * t, sd) + 0.5 * gauss(x, -2 * t, sd)


def marg_traj(x0, n=500, tend=0.995):
    ts = np.linspace(0, tend, n)
    xs = [x0]
    x = x0
    for i in range(n - 1):
        t, h = ts[i], ts[i + 1] - ts[i]
        k1 = u1(x, t); k2 = u1(x + h / 2 * k1, t + h / 2)
        k3 = u1(x + h / 2 * k2, t + h / 2); k4 = u1(x + h * k3, t + h)
        x = x + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        xs.append(x)
    ts = np.append(ts, 1.0)
    xs = np.append(xs, 2.0 * np.sign(xs[-1]))
    return ts, np.array(xs)


def euler(x0, n):
    xs = [x0]
    h = 1 / n
    for k in range(n):
        xs.append(xs[-1] + h * u1(xs[-1], k * h))
    return xs


# ---------- shared plot ----------
def make_plot():
    ax = Axes(x_range=[0, 1, 0.5], y_range=[-3, 3, 1], x_length=6.0, y_length=5.2, tips=False).move_to(PLOT_C)
    o = ax.c2p
    yaxis = Line(o(0, -3), o(0, 3), color=C_AX, stroke_width=2)
    taxis = Line(o(0, -3), o(1.05, -3), color=C_AX, stroke_width=2)
    g = VGroup(yaxis, taxis)
    for x in [-2, 0, 2]:
        g.add(Line(o(0, x) + LEFT * 0.08, o(0, x) + RIGHT * 0.08, color=C_AX, stroke_width=2))
        g.add(MathTex(f"{x:+d}" if x else "0", font_size=30, color=C_AX).next_to(o(0, x), LEFT, buff=0.15))
    for t, s in [(0, "0"), (0.5, r"\tfrac12"), (1, "1")]:
        g.add(Line(o(t, -3) + DOWN * 0.08, o(t, -3) + UP * 0.08, color=C_AX, stroke_width=2))
        g.add(MathTex(s, font_size=30, color=C_AX).next_to(o(t, -3), DOWN, buff=0.12))
    g.add(MathTex("t", font_size=34, color=C_AX).next_to(taxis.get_end(), RIGHT, buff=0.15))
    g.add(MathTex("x", font_size=34, color=C_AX).next_to(yaxis.get_end(), UP, buff=0.12))
    g.add(DashedLine(o(1, -3), o(1, 3), color=GREY_D, stroke_width=1.5))
    return ax, g


def side_density(ax, t0, pdf, color=WHITE, width=0.4, cap=0.32, fill=0.22, sw=2.5, n=241, closed=True):
    xs = np.linspace(-3, 3, n)
    vals = np.array([pdf(x) for x in xs])
    k = width if abs(width) * vals.max() <= cap else np.sign(width) * cap / vals.max()   # scale, never clip
    pts = [ax.c2p(t0 + k * v, x) for x, v in zip(xs, vals)]
    if not closed:
        return VMobject(color=color, stroke_width=sw).set_points_as_corners(pts)
    return Polygon(*pts, ax.c2p(t0, 3), ax.c2p(t0, -3), color=color, stroke_width=sw,
                   fill_color=color, fill_opacity=fill)


def noise_density(ax):
    return side_density(ax, 0, lambda x: gauss(x, 0, 1), color=C_NOISE)


def data_dots(ax):
    return VGroup(*[Dot(ax.c2p(1, s), radius=0.09, color=C_DATA) for s in (-2, 2)])


def seg(ax, x0, x1, color=C_COND, sw=3, op=1.0):
    return Line(ax.c2p(0, x0), ax.c2p(1, x1), color=color, stroke_width=sw, stroke_opacity=op)


def slope_arrow(ax, t, x, s, L=0.9, color=C_COND, sw=5):
    p = ax.c2p(t, x)
    q = ax.c2p(t + 0.01, x + 0.01 * s)
    d = (q - p) / np.linalg.norm(q - p)
    return Arrow(p, p + L * d, buff=0, color=color, stroke_width=sw,
                 max_tip_length_to_length_ratio=0.28, max_stroke_width_to_length_ratio=10)


def curve(ax, ts, xs, color=C_MARG, sw=3, op=1.0):
    return VMobject(color=color, stroke_width=sw, stroke_opacity=op).set_points_as_corners(
        [ax.c2p(t, x) for t, x in zip(ts, xs)])


def slope_field(ax, color=C_MARG, L=0.28, op=0.8):
    g = VGroup()
    for t in np.arange(0.05, 0.9, 0.075):
        for x in np.arange(-2.75, 2.76, 0.5):
            a = slope_arrow(ax, t, x, u1(x, t), L=L, color=color, sw=2.5)
            a.set_opacity(op)
            g.add(a)
    return g


def title(s):
    return Text(s, font_size=38).move_to(UP * 3.45)


def panel(m, y):
    return m.move_to([PANEL_X, y, 0])


TRAJ_X0 = [-2.2, -1.5, -1.0, -0.6, -0.3, -0.08, 0.08, 0.3, 0.6, 1.0, 1.5, 2.2]
TRAIN_X0 = [-2.2, -1.6, -1.1, -0.7, -0.3, 0.1, 0.5, 0.9, 1.3, 1.8, 2.3, -0.5, 0.2, 1.0]
TRAIN_X1 = [2, -2, 2, 2, -2, 2, -2, -2, 2, -2, -2, -2, 2, 2]


# ======================================================================
class Intro(Timed):
    def construct(self):
        ttl = Text("Flow matching", font_size=44).move_to(UP * 3.45)
        rng = np.random.default_rng(3)
        mus = np.array([[-2.8, 1.0], [2.8, -1.2]])
        s = 0.3
        CEN = np.array([0.0, -0.3, 0])

        def u2(p, t):
            sig2 = (1 - t) ** 2 + t * t * s * s
            c = (t * s * s - (1 - t)) / sig2
            d = np.array([np.sum((p - t * m) ** 2) for m in mus])
            w = np.exp(-(d - d.min()) / (2 * sig2)); w /= w.sum()
            return sum(w[k] * (mus[k] + c * (p - t * mus[k])) for k in range(2))

        pts = rng.normal(size=(70, 2))
        pts = pts[np.linalg.norm(pts, axis=1) < 2.2]
        N = 300
        trajs = []
        for p in pts:
            tr = [p.copy()]
            x = p.copy()
            for k in range(N):
                x = x + (1 / N) * u2(x, k / N)
                tr.append(x.copy())
            trajs.append(np.array(tr))

        def at(tr, t):
            f = t * N; i = int(min(f, N - 1)); a = f - i
            p = (1 - a) * tr[i] + a * tr[i + 1]
            return CEN + np.array([p[0], p[1], 0])

        tp = ValueTracker(0)
        tf = ValueTracker(0)
        dots = VGroup(*[Dot(at(tr, 0), radius=0.055, color=C_NOISE) for tr in trajs])

        def upd(g):
            t = tp.get_value()
            for d, tr in zip(g, trajs):
                d.move_to(at(tr, t))
                d.set_color(interpolate_color(C_NOISE, C_DATA, t))
        dots.add_updater(upd)
        data = VGroup(*[Dot(CEN + np.array([*(m + s * rng.normal(size=2)), 0]), radius=0.05, color=C_DATA,
                            fill_opacity=0.45) for m in mus for _ in range(30)])
        noise_lab = Text("noise", font_size=28, color=C_NOISE).move_to(CEN + DOWN * 2.75)
        data_lab = Text("data", font_size=28, color=C_DATA).move_to(CEN + np.array([*mus[0], 0]) + UP * 0.8)

        def field():
            t = tf.get_value()
            g = VGroup()
            for X in np.arange(-5.5, 5.6, 1.1):
                for Y in np.arange(-2.4, 2.0, 0.95):
                    v = u2(np.array([X, Y + 0.3]), min(t, 0.85))
                    n = np.linalg.norm(v)
                    if n < 1e-3:
                        continue
                    L = min(0.6, 0.16 * n)
                    st = np.array([X, Y, 0])
                    g.add(Arrow(st, st + L * np.array([v[0], v[1], 0]) / n, buff=0, color=C_NET, stroke_width=3,
                                max_tip_length_to_length_ratio=0.35, max_stroke_width_to_length_ratio=12))
            return g
        arrows = always_redraw(field)
        flab = MathTex(r"\text{velocity field }", r"v_\theta(x,t)", font_size=36).to_corner(UR, buff=0.4).shift(DOWN * 0.55)
        flab[1].set_color(C_NET)
        tnum = DecimalNumber(0, num_decimal_places=2, font_size=34)
        tnum.add_updater(lambda m: m.set_value(min(tf.get_value(), 0.85)))
        tlab = VGroup(MathTex("t=", font_size=34), tnum).arrange(RIGHT, buff=0.1).to_corner(UL, buff=0.4).shift(DOWN * 0.55)

        self.cue(0)
        self.play(FadeIn(ttl), FadeIn(dots), FadeIn(noise_lab), run_time=1.0)
        self.play(FadeIn(data), FadeIn(data_lab), run_time=0.8)
        self.cue(1)
        self.play(FadeIn(arrows), Write(flab), run_time=1.5)
        self.cue(2)
        self.play(FadeIn(tlab), run_time=0.5)
        self.play(tf.animate.set_value(0.7), run_time=2.6, rate_func=smooth)
        self.play(tf.animate.set_value(0.0), run_time=1.6)
        self.cue(3)
        self.play(FadeOut(noise_lab), run_time=0.3)
        self.play(tp.animate.set_value(1), tf.animate.set_value(1), run_time=3.0, rate_func=linear)
        self.cue(4)
        dots.clear_updaters()
        arrows.clear_updaters()
        self.play(FadeOut(arrows), FadeOut(tlab), FadeOut(dots), FadeOut(data),
                  FadeOut(data_lab), FadeOut(flab), run_time=0.8)
        self.cue(5)
        loss = MathTex(r"\min_\theta\ \mathbb{E}\,\big\|\,", r"v_\theta(x_t,t)", r"-", r"(x_1-x_0)", r"\,\big\|^2", r"\;>\;0",
                       font_size=46).move_to(UP * 0.4)
        loss[1].set_color(C_NET); loss[3].set_color(C_COND)
        tg = Text("per-sample target", font_size=26, color=C_COND).next_to(loss[3], DOWN, buff=0.35)
        self.play(Write(loss[:5]), run_time=1.6)
        self.play(FadeIn(tg), run_time=0.5)
        self.play(Write(loss[5]), run_time=0.6)
        self.cue(6)
        chips = VGroup(*[Text(s, font_size=30) for s in ["1. what it learns", "2. why it works", "3. how to sample"]]
                       ).arrange(RIGHT, buff=0.8).move_to(DOWN * 2.2)
        self.play(LaggedStart(*[FadeIn(c, shift=UP * 0.2) for c in chips], lag_ratio=0.4), run_time=1.8)
        self.finish()


# ======================================================================
class Path(Timed):
    def construct(self):
        ax, base = make_plot()
        o = ax.c2p
        ttl = title("Setup: 1-D, straight paths")
        self.cue(0)
        self.play(FadeIn(ttl), Create(base), run_time=2.0)
        self.cue(1)
        sweeper = Dot(o(0, -3), radius=0.07, color=WHITE)
        self.play(FadeIn(sweeper), run_time=0.3)
        self.play(sweeper.animate.move_to(o(1, -3)), run_time=2.2)
        self.play(FadeOut(sweeper), run_time=0.3)
        self.cue(2)
        nd = noise_density(ax)
        nlab = MathTex(r"x_0\sim\mathcal N(0,1)", font_size=32, color=C_NOISE).next_to(o(0.2, 1.3), RIGHT, buff=0)
        self.play(Create(nd), run_time=1.5)
        self.play(FadeIn(nlab), run_time=0.6)
        self.cue(3)
        dd = data_dots(ax)
        dlab = MathTex(r"x_1\in\{-2,+2\}", font_size=32, color=C_DATA).next_to(o(1, 0), RIGHT, buff=0.3)
        self.play(LaggedStart(*[GrowFromCenter(d) for d in dd], lag_ratio=0.3), FadeIn(dlab), run_time=1.2)
        self.cue(4)
        q = panel(MathTex(r"q", r"=", r"\tfrac12\,\delta_{-2}+\tfrac12\,\delta_{+2}", font_size=38, color=C_DATA), 2.1)
        halves = VGroup(*[MathTex(r"\tfrac12", font_size=30, color=C_DATA).next_to(d, RIGHT, buff=0.15) for d in dd])
        self.play(Write(q), FadeIn(halves), FadeOut(dlab), run_time=1.5)
        self.cue(5)
        x0d = Dot(o(0, -0.8), radius=0.08, color=C_NOISE)
        line = seg(ax, -0.8, 2)
        self.play(FadeOut(nlab), GrowFromCenter(x0d), run_time=0.6)
        self.play(Indicate(dd[1], color=C_DATA, scale_factor=1.6), run_time=0.8)
        self.play(Create(line), run_time=1.4)
        self.cue(6)
        xt = panel(MathTex(r"x_t", r"=", r"(1-t)\,", r"x_0", r"+", r"t\,", r"x_1", font_size=40), 0.9)
        xt[3].set_color(C_NOISE); xt[6].set_color(C_DATA)
        tt = ValueTracker(0)
        mover = always_redraw(lambda: Dot(o(tt.get_value(), -0.8 + 2.8 * tt.get_value()), radius=0.08, color=WHITE))
        mlab = always_redraw(lambda: MathTex("x_t", font_size=32).next_to(mover, DR, buff=0.08))
        self.play(Write(xt), run_time=1.5)
        self.add(mover, mlab)
        self.play(tt.animate.set_value(0.6), run_time=2.4)
        self.cue(7)
        vel = panel(MathTex(r"\frac{dx_t}{dt}", r"=", r"x_1-x_0", r"=", r"2.8", font_size=40), -0.4)
        vel[2].set_color(C_COND); vel[4].set_color(C_COND)
        arr = always_redraw(lambda: slope_arrow(ax, tt.get_value(), -0.8 + 2.8 * tt.get_value(), 2.8, L=1.1))
        self.play(Write(vel[:3]), run_time=1.4)
        self.play(GrowArrow(arr), Write(vel[3:]), run_time=1.0)
        self.cue(8)
        same = panel(Text("same at every t", font_size=28, color=C_COND), -1.6)
        self.play(FadeIn(same), run_time=0.5)
        self.play(tt.animate.set_value(0.95), run_time=1.2)
        self.play(tt.animate.set_value(0.15), run_time=1.8)
        self.finish()


# ======================================================================
class Loss(Timed):
    def construct(self):
        ax, base = make_plot()
        o = ax.c2p
        nd = noise_density(ax); dd = data_dots(ax)
        line = seg(ax, -0.8, 2)
        x0d = Dot(o(0, -0.8), radius=0.08, color=C_NOISE)
        self.add(base, nd, dd, line, x0d)
        ttl = title("Training: conditional flow matching")
        self.cue(0)
        self.play(FadeIn(ttl), run_time=0.8)
        self.play(ShowPassingFlash(line.copy().set_color(WHITE).set_stroke(width=8), time_width=0.5), run_time=1.2)
        self.cue(1)
        samp = VGroup(MathTex(r"t\sim\mathcal U[0,1]", font_size=36),
                      MathTex(r"x_0\sim\mathcal N(0,1)", font_size=36, color=C_NOISE),
                      MathTex(r"x_1\sim q", font_size=36, color=C_DATA)).arrange(RIGHT, buff=0.45)
        panel(samp, 2.2)
        vl = DashedLine(o(0.6, -3), o(0.6, 0.4 * -0.8 + 0.6 * 2), color=GREY_B, stroke_width=2)
        self.play(FadeIn(samp[0]), Create(vl), run_time=0.9)
        self.play(FadeIn(samp[1]), Indicate(x0d, color=C_NOISE), run_time=0.9)
        self.play(FadeIn(samp[2]), Indicate(dd[1], color=C_DATA), run_time=0.9)
        self.cue(2)
        xtv = 0.4 * -0.8 + 0.6 * 2
        xtd = Dot(o(0.6, xtv), radius=0.09, color=WHITE)
        xtl = MathTex("x_t", font_size=32).next_to(xtd, LEFT, buff=0.15)
        self.play(GrowFromCenter(xtd), FadeIn(xtl), run_time=0.8)
        self.cue(3)
        loss = MathTex(r"\mathcal L_{\mathrm{CFM}}(\theta)", r"=", r"\mathbb E\,\big\|\,", r"v_\theta(x_t,t)", r"-",
                       r"(x_1-x_0)", r"\,\big\|^2", font_size=38)
        loss[3].set_color(C_NET); loss[5].set_color(C_COND)
        loss.scale_to_fit_width(min(loss.width, 6.0))
        panel(loss, 1.15)
        pred = slope_arrow(ax, 0.6, xtv, 0.6, L=1.0, color=C_NET)
        targ = slope_arrow(ax, 0.6, xtv, 2.8, L=1.0, color=C_COND)
        plab = MathTex(r"v_\theta", font_size=30, color=C_NET).next_to(pred.get_end(), RIGHT, buff=0.1)
        tlab = MathTex(r"x_1-x_0", font_size=30, color=C_COND).next_to(targ.get_end(), UL, buff=0.2)
        self.play(Write(loss), run_time=2.2)
        self.play(GrowArrow(pred), FadeIn(plab), run_time=0.8)
        self.play(GrowArrow(targ), FadeIn(tlab), run_time=0.8)
        self.cue(4)
        box = SurroundingRectangle(loss[0], color=WHITE, buff=0.08)
        self.play(Create(box), run_time=0.8)
        self.cue(5)
        lines = VGroup(*[seg(ax, a, b, sw=2.5, op=0.75) for a, b in zip(TRAIN_X0, TRAIN_X1)])
        self.play(FadeOut(VGroup(pred, targ, plab, tlab, xtd, xtl, vl, box, x0d)), line.animate.set_stroke(opacity=0.75, width=2.5),
                  run_time=0.5)
        self.play(LaggedStart(*[Create(l) for l in lines], lag_ratio=0.08), run_time=1.3)
        self.cue(6)
        allx = list(zip(TRAIN_X0, TRAIN_X1))
        crosses = []
        for i in range(len(allx)):
            for j in range(i + 1, len(allx)):
                (a0, a1), (b0, b1) = allx[i], allx[j]
                da, db = a1 - a0, b1 - b0
                if abs(da - db) < 1e-6:
                    continue
                t = (b0 - a0) / (da - db)
                if 0.15 < t < 0.85:
                    crosses.append((t, a0 + da * t))
        pick = crosses[::max(1, len(crosses) // 7)][:7]
        circ = VGroup(*[Circle(radius=0.14, color=WHITE, stroke_width=3).move_to(o(t, x)) for t, x in pick])
        self.play(LaggedStart(*[Create(c) for c in circ], lag_ratio=0.15), run_time=1.0)
        self.play(FadeOut(circ), run_time=0.5)
        self.cue(7)
        pt = Dot(o(0.5, 0), radius=0.1, color=WHITE)
        guides = VGroup(DashedLine(o(0.5, -3), o(0.5, 0), color=GREY_B, stroke_width=2),
                        DashedLine(o(0, 0), o(0.5, 0), color=GREY_B, stroke_width=2))
        self.play(lines.animate.set_stroke(opacity=0.18), line.animate.set_stroke(opacity=0.18),
                  Create(guides), GrowFromCenter(pt), run_time=1.2)
        self.cue(8)
        l1 = seg(ax, -2, 2, sw=5); l2 = seg(ax, 2, -2, sw=5)
        a1 = slope_arrow(ax, 0.5, 0, 4, L=1.1); a2 = slope_arrow(ax, 0.5, 0, -4, L=1.1)
        n1 = MathTex("+4", font_size=34, color=C_COND).next_to(a1.get_end(), RIGHT, buff=0.1)
        n2 = MathTex("-4", font_size=34, color=C_COND).next_to(a2.get_end(), RIGHT, buff=0.1)
        self.play(Create(l1), run_time=0.9)
        self.play(GrowArrow(a1), FadeIn(n1), run_time=0.6)
        self.play(Create(l2), run_time=0.9)
        self.play(GrowArrow(a2), FadeIn(n2), run_time=0.6)
        self.add(pt)
        self.cue(9)
        two = panel(MathTex(r"(x{=}0,\ t{=}\tfrac12)", r"\ \to\ ", r"+4", r"\ \text{or}\ ", r"-4", font_size=36), -0.4)
        two[2].set_color(C_COND); two[4].set_color(C_COND)
        self.play(FadeIn(two), run_time=0.9)
        self.cue(10)
        nz = panel(MathTex(r"\Rightarrow\ \min_\theta\ \mathcal L_{\mathrm{CFM}}(\theta)\ >\ 0", font_size=38), -1.5)
        self.play(Write(nz), run_time=1.2)
        self.finish()


# ======================================================================
class Marginal(Timed):
    def construct(self):
        ax, base = make_plot()
        o = ax.c2p
        nd = noise_density(ax); dd = data_dots(ax)
        l1 = seg(ax, -2, 2, sw=4); l2 = seg(ax, 2, -2, sw=4)
        pt = Dot(o(0.5, 0), radius=0.1, color=WHITE)
        a1 = slope_arrow(ax, 0.5, 0, 4, L=1.1); a2 = slope_arrow(ax, 0.5, 0, -4, L=1.1)
        plot = VGroup(base, nd, dd, l1, l2, a1, a2, pt)
        self.add(plot)
        ttl = title("What the network learns")
        self.cue(0)
        self.play(FadeIn(ttl), run_time=0.8)
        self.cue(1)
        am = panel(MathTex(r"\arg\min_c\ \mathbb E\,(Y-c)^2", r"=", r"\mathbb E[Y]", font_size=40), 2.1)
        ga = slope_arrow(ax, 0.5, 0, 0, L=1.1, color=C_MARG, sw=6)
        glab = Text("mean of +4, −4", font_size=24, color=C_MARG).next_to(ga.get_end(), RIGHT, buff=0.1)
        self.play(Write(am), run_time=1.6)
        self.play(GrowArrow(ga), FadeIn(glab), run_time=0.9)
        self.cue(2)
        self.play(ShowPassingFlash(l1.copy().set_stroke(WHITE, 8), time_width=0.6),
                  ShowPassingFlash(l2.copy().set_stroke(WHITE, 8), time_width=0.6), run_time=1.3)
        self.cue(3)
        ud = MathTex(r"u_t(x)", r"=", r"\mathbb E\big[\,", r"x_1-x_0", r"\,\big|\,", r"x_t=x", r"\,\big]", font_size=40)
        ud[0].set_color(C_MARG); ud[3].set_color(C_COND)
        panel(ud, 0.9)
        self.play(Write(ud[0]), am[2].animate.set_color(C_MARG), run_time=1.0)
        self.cue(4)
        self.play(Write(ud[1:]), run_time=2.0)
        # ---- derivation, full width
        self.cue(5)
        self.play(FadeOut(plot), FadeOut(ga), FadeOut(glab), FadeOut(am),
                  ud.animate.scale(0.85).move_to(UP * 2.55), run_time=0.8)
        L0 = MathTex(r"\mathcal L_{\mathrm{CFM}}", r"=", r"\mathbb E\,\big\|\,(", r"v_\theta", r"-", r"u_t", r")+(",
                     r"u_t", r"-", r"(x_1-x_0)", r")\,\big\|^2", font_size=40)
        L0[3].set_color(C_NET); L0[5].set_color(C_MARG); L0[7].set_color(C_MARG); L0[9].set_color(C_COND)
        L0.move_to(UP * 1.55)
        note = MathTex(r"v_\theta\equiv v_\theta(x_t,t),\quad u_t\equiv u_t(x_t)", font_size=28, color=GREY_B).next_to(L0, DOWN, buff=0.2)
        self.play(Write(L0), run_time=1.0)
        self.play(FadeIn(note), run_time=0.3)
        lx = L0[1].get_left()[0]
        self.cue(6)
        B1 = MathTex(r"=", r"\mathbb E\,\|", r"v_\theta", r"-", r"u_t", r"\|^2", font_size=40)
        B1[2].set_color(C_NET); B1[4].set_color(C_MARG)
        B1[1:].shift(RIGHT * 0.2)
        B1.move_to(UP * 0.2); B1.shift(RIGHT * (lx - B1[0].get_left()[0]))
        b1box = SurroundingRectangle(B1[1:], color=C_MARG, buff=0.1)
        b1tag = MathTex(r"\mathcal L_{\mathrm{FM}}(\theta)", r"\text{: the loss we want}", font_size=32, color=C_MARG).next_to(b1box, RIGHT, buff=0.4)
        self.play(Write(B1), run_time=1.2)
        self.play(Create(b1box), FadeIn(b1tag), run_time=0.8)
        self.cue(7)
        B2 = MathTex(r"+", r"\mathbb E\,\|", r"u_t", r"-", r"(x_1-x_0)", r"\|^2", font_size=40)
        B2[2].set_color(C_MARG); B2[4].set_color(C_COND)
        B2[1:].shift(RIGHT * 0.2)
        B2.move_to(DOWN * 0.75); B2.shift(RIGHT * (lx - B2[0].get_left()[0]))
        b2box = SurroundingRectangle(B2[1:], color=GREY_B, buff=0.1)
        b2tag = Text("variance of targets: no θ", font_size=28, color=GREY_B).next_to(b2box, RIGHT, buff=0.4)
        self.play(Write(B2), run_time=1.2)
        self.play(Create(b2box), FadeIn(b2tag), run_time=0.8)
        self.cue(8)
        B3 = MathTex(r"+", r"\underbrace{2\,\mathbb E\,\big\langle\,v_\theta-u_t,\ u_t-(x_1-x_0)\,\big\rangle}_{=\,0}", font_size=40)
        B3[1:].shift(RIGHT * 0.2)
        B3.move_to(DOWN * 1.75); B3.shift(RIGHT * (lx - B3[0].get_left()[0]))
        why = MathTex(r"\text{cross term} = 0\ \text{ since }\ \mathbb E\big[\,x_1-x_0\,\big|\,x_t\,\big]=u_t(x_t)", font_size=30, color=GREY_B
                      ).next_to(B3, DOWN, buff=0.12).align_to(B3[1], LEFT)
        self.play(Write(B3), run_time=1.4)
        self.play(FadeIn(why), run_time=0.6)
        self.play(B3.animate.set_opacity(0.6), run_time=0.6)
        self.cue(9)
        fin = MathTex(r"\nabla_\theta\,\mathcal L_{\mathrm{CFM}}(\theta)", r"=", r"\nabla_\theta\,\mathcal L_{\mathrm{FM}}(\theta)",
                      font_size=40).move_to(DOWN * 3.35)
        fin[2].set_color(C_MARG)
        fbox = SurroundingRectangle(fin, color=WHITE, buff=0.12)
        self.play(Write(fin), run_time=1.5)
        self.play(Create(fbox), run_time=0.6)
        self.finish()


# ======================================================================
class Transport(Timed):
    def construct(self):
        ax, base = make_plot()
        o = ax.c2p
        nd = noise_density(ax); dd = data_dots(ax)
        self.add(base, nd, dd)
        ttl = Tex(r"Why $u_t$ is the right field", font_size=44).move_to(UP * 3.45)
        self.cue(0)
        self.play(FadeIn(ttl), run_time=0.8)
        self.cue(1)
        tt = ValueTracker(0.0)
        prof = always_redraw(lambda: side_density(ax, tt.get_value(), pt_pdf(tt.get_value()), color=WHITE, fill=0.15,
                                                  cap=min(0.32, 0.9 * (1 - tt.get_value()))))
        plab = always_redraw(lambda: MathTex(r"p_t", font_size=32).next_to(o(tt.get_value(), 2.6), RIGHT, buff=0.05))
        self.play(FadeIn(prof), FadeIn(plab), run_time=0.8)
        self.cue(2)
        copies = VGroup()
        for t in [0.25, 0.5, 0.75]:
            self.play(tt.animate.set_value(t), run_time=1.1, rate_func=linear)
            c = side_density(ax, t, pt_pdf(t), color=WHITE, fill=0.08, sw=1.5, cap=0.16).set_stroke(opacity=0.6)
            copies.add(c); self.add(c)
        self.play(tt.animate.set_value(0.95), run_time=1.0, rate_func=linear)
        c = side_density(ax, 0.95, pt_pdf(0.95), color=WHITE, fill=0.08, sw=1.5, cap=0.9 * 0.05).set_stroke(opacity=0.6)
        copies.add(c); self.add(c)
        self.remove(prof); self.play(FadeOut(plab), run_time=0.3)
        self.cue(3)
        comps = VGroup(*[side_density(ax, 0.5, (lambda s: (lambda x: 0.5 * gauss(x, s, 0.5)))(s),
                                      color=C_COND, fill=0.25, sw=3.5, closed=False) for s in (-1, 1)])
        cl = VGroup(*[seg(ax, x0, x1, sw=2, op=0.55) for x1 in (2, -2) for x0 in (-2, -1, 0, 1, 2)])
        clab = VGroup(MathTex(r"p_t(x|x_1{=}{+2})", font_size=28, color=C_COND).next_to(o(0.5 + 0.4 * 0.5 * gauss(1, 1, 0.5), 1.0), RIGHT, buff=0.1),
                      MathTex(r"p_t(x|x_1{=}{-2})", font_size=28, color=C_COND).next_to(o(0.5 + 0.4 * 0.5 * gauss(1, 1, 0.5), -1.0), RIGHT, buff=0.1))
        for m in clab:
            m.add_background_rectangle(opacity=0.8, buff=0.05)
        self.play(FadeOut(copies), run_time=0.5)
        self.play(Create(cl), run_time=1.2)
        self.play(Create(comps), FadeIn(clab), cl.animate.set_stroke(opacity=0.22), run_time=1.2)
        self.cue(4)
        f1 = MathTex(r"u_t(x)", r"=", r"\sum_{x_1}", r"w(x_1\,|\,x,t)", r"\,", r"u_t(x\,|\,x_1)", font_size=38)
        f1[0].set_color(C_MARG); f1[5].set_color(C_COND)
        panel(f1, 2.1)
        f2 = MathTex(r"w(x_1|x,t)=\frac{p_t(x|x_1)\,q(x_1)}{p_t(x)},\quad", r"u_t(x|x_1)=\frac{x_1-x}{1-t}", font_size=32)
        f2[1].set_color(C_COND)
        f2.scale_to_fit_width(min(f2.width, 6.0))
        panel(f2, 1.05)
        self.play(FadeOut(cl), Write(f1), run_time=2.0)
        self.play(FadeIn(f2), run_time=1.2)
        self.cue(5)
        c1 = MathTex(r"\partial_t p_t(x|x_1)+\partial_x\big[p_t(x|x_1)\,", r"u_t(x|x_1)", r"\big]=0", font_size=32)
        c1[1].set_color(C_COND)
        c1.scale_to_fit_width(min(c1.width, 6.0)); panel(c1, -0.15)
        avg = MathTex(r"\Big\downarrow\ \textstyle\sum_{x_1} q(x_1)\,(\cdot)", font_size=30, color=GREY_B)
        panel(avg, -0.9)
        c2 = MathTex(r"\partial_t p_t(x)+\partial_x\big[p_t(x)\,", r"u_t(x)", r"\big]=0", font_size=34)
        c2[1].set_color(C_MARG); panel(c2, -1.65)
        self.play(VGroup(f1, f2).animate.set_opacity(0.4), VGroup(comps, clab).animate.set_opacity(0.3), Write(c1), run_time=1.5)
        self.play(FadeIn(avg), run_time=0.6)
        self.play(Write(c2), run_time=1.3)
        self.cue(6)
        tr = MathTex(r"p_0", r"\ \xrightarrow{\ \ u_t\ \ }\ ", r"p_1", font_size=42)
        tr[0].set_color(C_NOISE); tr[2].set_color(C_DATA); tr[1].set_color(C_MARG)
        panel(tr, -2.65)
        self.play(VGroup(c1, avg).animate.set_opacity(0.4), FadeOut(comps), FadeOut(clab), run_time=0.6)
        self.play(Write(tr), Indicate(nd, color=C_NOISE), run_time=1.4)
        self.play(Indicate(dd, color=C_DATA), run_time=0.8)
        self.cue(7)
        trajs = VGroup(*[curve(ax, *marg_traj(x0), sw=3) for x0 in [-1.5, -0.6, -0.15, 0.3, 1.0, 1.8]])
        self.play(LaggedStart(*[Create(c) for c in trajs], lag_ratio=0.1), run_time=1.8)
        self.finish()


# ======================================================================
class Example(Timed):
    def construct(self):
        ax, base = make_plot()
        o = ax.c2p
        nd = noise_density(ax); dd = data_dots(ax)
        self.add(base, nd, dd)
        ttl = title("Worked example at t = ½")
        vl = DashedLine(o(0.5, -3), o(0.5, 3), color=GREY_B, stroke_width=2)
        self.cue(0)
        self.play(FadeIn(ttl), Create(vl), run_time=1.0)
        self.cue(1)
        pt = Dot(o(0.5, 0), radius=0.1, color=WHITE)
        l1 = seg(ax, -2, 2, sw=4); l2 = seg(ax, 2, -2, sw=4)
        a1 = slope_arrow(ax, 0.5, 0, 4, L=1.0); a2 = slope_arrow(ax, 0.5, 0, -4, L=1.0)
        n1 = MathTex("+4", font_size=32, color=C_COND).next_to(a1.get_end(), RIGHT, buff=0.08)
        n2 = MathTex("-4", font_size=32, color=C_COND).next_to(a2.get_end(), RIGHT, buff=0.08)
        r1 = MathTex(r"x=0:", r"\quad\text{targets}\ ", r"+4,\ -4", font_size=34)
        r1[2].set_color(C_COND)
        r1.move_to([PANEL_X, 2.3, 0])
        self.play(GrowFromCenter(pt), Create(l1), Create(l2), run_time=1.2)
        self.play(GrowArrow(a1), GrowArrow(a2), FadeIn(n1), FadeIn(n2), run_time=0.8)
        self.play(FadeIn(r1), run_time=0.6)
        self.cue(2)
        r2 = MathTex(r"u_{1/2}(0)", r"=", r"\tfrac12(+4)+\tfrac12(-4)", r"=", r"0", font_size=34)
        r2[0].set_color(C_MARG); r2[4].set_color(C_MARG)
        r2.move_to([PANEL_X, 1.6, 0])
        ga = slope_arrow(ax, 0.5, 0, 0, L=1.0, color=C_MARG, sw=6)
        self.play(Write(r2), run_time=1.6)
        self.play(GrowArrow(ga), run_time=0.7)
        self.cue(3)
        nev = Text("never a training target", font_size=26, color=C_MARG).move_to([PANEL_X, 1.0, 0])
        self.play(Indicate(ga, color=C_MARG, scale_factor=1.4), FadeIn(nev), run_time=1.2)
        self.cue(4)
        self.play(FadeOut(VGroup(l1, l2, a1, a2, n1, n2, ga)), VGroup(r1, r2, nev).animate.set_opacity(0.35), run_time=0.6)
        self.play(pt.animate.move_to(o(0.5, 0.5)), run_time=0.9)
        r3 = MathTex(r"x=\tfrac12:", font_size=34).move_to([PANEL_X - 2.3, 0.25, 0])
        self.play(FadeIn(r3), run_time=0.4)
        self.cue(5)
        m1_ = seg(ax, -1, 2, sw=4); b1 = slope_arrow(ax, 0.5, 0.5, 3, L=1.0)
        k1 = MathTex("+3", font_size=32, color=C_COND).next_to(b1.get_end(), RIGHT, buff=0.08)
        t3 = MathTex(r"\to{+2}:\ ", r"+3", font_size=34).next_to(r3, RIGHT, buff=0.3)
        t3[1].set_color(C_COND)
        self.play(Create(m1_), run_time=0.8)
        self.play(GrowArrow(b1), FadeIn(k1), FadeIn(t3), run_time=0.8)
        self.add(pt)
        self.cue(6)
        m2_ = seg(ax, 3, -2, sw=4); b2 = slope_arrow(ax, 0.5, 0.5, -5, L=1.0)
        k2 = MathTex("-5", font_size=32, color=C_COND).next_to(b2.get_end(), RIGHT, buff=0.08)
        t4 = MathTex(r"\to{-2}:\ ", r"-5", font_size=34).next_to(t3, RIGHT, buff=0.4)
        t4[1].set_color(C_COND)
        self.play(Create(m2_), run_time=0.8)
        self.play(GrowArrow(b2), FadeIn(k2), FadeIn(t4), run_time=0.8)
        self.add(pt)
        self.cue(7)
        comps = VGroup(*[side_density(ax, 0.5, (lambda s: (lambda x: 0.5 * gauss(x, s, 0.5)))(s), color=C_COND,
                                      sw=3, width=-0.5, closed=False) for s in (-1, 1)])
        hp = 0.5 * 0.5 * gauss(0.5, 1, 0.5); hm = 0.5 * 0.5 * gauss(0.5, -1, 0.5)
        bars = VGroup(Line(o(0.5, 0.5), o(0.5 - hp, 0.5), color=WHITE, stroke_width=7))
        w1 = MathTex(r"w\ \propto\ \mathcal N(\tfrac12;\,\pm1,\,\tfrac14)", r"\ \Rightarrow\ ", r"e^{-0.5}:e^{-4.5}", font_size=34)
        w1.move_to([PANEL_X, -0.55, 0])
        self.play(FadeIn(comps), VGroup(m1_, m2_, b1, b2, k1, k2).animate.set_opacity(0.3), run_time=0.8)
        self.play(Create(bars), FadeIn(w1), run_time=1.0)
        self.cue(8)
        w2 = MathTex(r"\approx\ 0.982\ :\ 0.018", font_size=36).move_to([PANEL_X, -1.3, 0])
        self.play(Write(w2), VGroup(m2_, b2, k2).animate.set_opacity(0.15), run_time=1.2)
        self.cue(9)
        r4 = MathTex(r"u_{1/2}(\tfrac12)", r"\approx", r"0.982(+3)+0.018(-5)", r"\approx", r"2.86", font_size=34)
        r4[0].set_color(C_MARG); r4[4].set_color(C_MARG)
        r4.scale_to_fit_width(min(r4.width, 6.0)).move_to([PANEL_X, -2.2, 0])
        gb = slope_arrow(ax, 0.5, 0.5, 2.86, L=1.0, color=C_MARG, sw=6)
        gl = MathTex("2.86", font_size=32, color=C_MARG).next_to(gb.get_end(), UP, buff=0.12)
        self.play(FadeOut(comps), FadeOut(bars), FadeOut(b1), FadeOut(k1), m1_.animate.set_opacity(1), Write(r4), run_time=1.6)
        self.play(GrowArrow(gb), FadeIn(gl), run_time=0.8)
        self.finish()


# ======================================================================
class Field(Timed):
    def construct(self):
        ax, base = make_plot()
        o = ax.c2p
        nd = noise_density(ax); dd = data_dots(ax)
        self.add(base, nd, dd)
        ttl = title("The marginal velocity field")
        fld = slope_field(ax)
        self.cue(0)
        self.play(FadeIn(ttl), LaggedStart(*[GrowArrow(a) for a in fld], lag_ratio=0.01), run_time=2.6)
        self.cue(1)
        f1 = MathTex(r"u_t(x)", r"=", r"\frac{\mathbb E[x_1\,|\,x_t=x]-x}{1-t}", font_size=40)
        f1[0].set_color(C_MARG)
        panel(f1, 1.9)
        f2 = MathTex(r"\mathbb E[x_1\,|\,x_t=x]", r"=", r"2\tanh\!\Big(\frac{2tx}{(1-t)^2}\Big)", font_size=34)
        lab = Text("for this data:", font_size=24, color=GREY_B)
        g2 = VGroup(lab, f2).arrange(DOWN, buff=0.15); panel(g2, 0.55)
        self.play(Write(f1), run_time=2.0)
        self.play(FadeIn(g2), run_time=1.2)
        self.cue(2)
        trajs = VGroup(*[curve(ax, *marg_traj(x0), sw=3) for x0 in TRAJ_X0])
        starts = VGroup(*[Dot(o(0, x0), radius=0.06, color=C_NOISE) for x0 in TRAJ_X0])
        self.play(FadeIn(starts), run_time=0.4)
        self.play(LaggedStart(*[Create(c) for c in trajs], lag_ratio=0.05), run_time=2.0)
        self.cue(3)
        self.play(fld.animate.set_opacity(0.18), trajs.animate.set_stroke(width=4.5), run_time=1.0)
        self.cue(4)
        mid = VGroup(trajs[5], trajs[6])
        ell = DashedVMobject(Ellipse(width=2.6, height=0.9, color=WHITE, stroke_width=2.5).move_to(o(0.5, 0)), num_dashes=30)
        hes = Text("hesitate, then split", font_size=26).add_background_rectangle(opacity=0.85, buff=0.08).move_to(o(0.5, -0.62))
        self.play(mid.animate.set_stroke(color=WHITE, width=6), Create(ell), FadeIn(hes), run_time=1.2)
        self.play(mid.animate.set_stroke(color=C_MARG, width=4.5), run_time=0.8)
        self.cue(5)
        tl = VGroup(*[seg(ax, a, b, sw=2.5, op=0.6) for a, b in zip(TRAIN_X0[:10], TRAIN_X1[:10])])
        self.play(FadeOut(ell), FadeOut(hes), trajs.animate.set_stroke(opacity=0.35), FadeIn(tl), run_time=1.0)
        self.cue(6)
        circ = VGroup()
        pairs = list(zip(TRAIN_X0[:10], TRAIN_X1[:10]))
        found = []
        for i in range(len(pairs)):
            for j in range(i + 1, len(pairs)):
                (a0, a1), (b0, b1) = pairs[i], pairs[j]
                da, db = a1 - a0, b1 - b0
                if abs(da - db) < 1e-6:
                    continue
                t = (b0 - a0) / (da - db)
                if 0.2 < t < 0.8:
                    found.append((t, a0 + da * t))
        for t, x in found[::max(1, len(found) // 6)][:6]:
            circ.add(Circle(radius=0.14, color=WHITE, stroke_width=3).move_to(o(t, x)))
        self.play(LaggedStart(*[Create(c) for c in circ], lag_ratio=0.15), run_time=1.0)
        self.play(FadeOut(circ), run_time=0.4)
        self.cue(7)
        mp = MathTex(r"x_0>0\ \mapsto\ +2,\qquad x_0<0\ \mapsto\ -2", font_size=34)
        panel(mp, -1.0)
        dm = Text("deterministic map: noise → data", font_size=26, color=C_MARG)
        panel(dm, -1.75)
        self.play(FadeOut(tl), trajs.animate.set_stroke(opacity=1), FadeIn(mp), FadeIn(dm), run_time=1.2)
        self.finish()


# ======================================================================
class Sampling(Timed):
    def construct(self):
        ax, base = make_plot()
        o = ax.c2p
        nd = noise_density(ax); dd = data_dots(ax)
        fld = slope_field(ax, op=0.18)
        self.add(base, nd, dd, fld)
        ttl = title("Sampling: integrate the ODE")
        x0 = 0.4
        d0 = Dot(o(0, x0), radius=0.09, color=C_NOISE)
        self.cue(0)
        self.play(FadeIn(ttl), run_time=0.8)
        self.play(GrowFromCenter(d0), Indicate(nd, color=C_NOISE), run_time=1.0)
        self.cue(1)
        ode = MathTex(r"\frac{dx}{dt}", r"=", r"v_\theta(x,t)", r",\quad x(0)=x_0\sim\mathcal N(0,1)", font_size=36)
        ode[2].set_color(C_NET)
        ode.scale_to_fit_width(min(ode.width, 5.6)); panel(ode, 2.2)
        rng = MathTex(r"t:\ 0\ \to\ 1", font_size=34); panel(rng, 1.45)
        ex = curve(ax, *marg_traj(x0), sw=3, op=0.45)
        self.play(Write(ode), run_time=2.0)
        self.play(FadeIn(rng), Create(ex), run_time=1.6)
        self.cue(2)
        eu = MathTex(r"x_{k+1}", r"=", r"x_k", r"+", r"h\,", r"v_\theta(x_k,t_k)", font_size=38)
        eu[5].set_color(C_NET); panel(eu, 0.65)
        asm = Tex(r"(trained network: $v_\theta\approx u_t$)", font_size=30, color=GREY_B).next_to(eu, DOWN, buff=0.15)
        self.play(FadeOut(rng), Write(eu), FadeIn(asm), run_time=1.6)
        self.cue(3)
        ticks = VGroup(*[DashedLine(o(k / 4, -3), o(k / 4, 3), color=GREY_D, stroke_width=1.5) for k in (1, 2, 3)])
        br = BraceBetweenPoints(o(0, -2.75), o(0.25, -2.75), direction=UP, color=GREY_B)
        bl = MathTex("h", font_size=32, color=GREY_B).next_to(br, UP, buff=0.08)
        self.play(Create(ticks), FadeIn(br), FadeIn(bl), run_time=1.2)
        self.play(Indicate(eu[4:], color=C_NET), run_time=1.0)
        self.cue(4)
        xs = euler(x0, 4)
        hdr = VGroup(MathTex("k", font_size=32), MathTex("t_k", font_size=32), MathTex("x_k", font_size=32))
        cols = [PANEL_X - 1.5, PANEL_X, PANEL_X + 1.5]
        for m, cx in zip(hdr, cols):
            m.move_to([cx, -0.55, 0])
        hl = Line([PANEL_X - 2.1, -0.8, 0], [PANEL_X + 2.1, -0.8, 0], color=GREY_B, stroke_width=1.5)

        def row(k):
            y = -1.15 - 0.46 * k
            vals = [str(k), ["0", r"\tfrac14", r"\tfrac12", r"\tfrac34", "1"][k], f"{xs[k]:.2f}"]
            r = VGroup(*[MathTex(v, font_size=32).move_to([cx, y, 0]) for v, cx in zip(vals, cols)])
            r[2].set_color(C_NOISE if k == 0 else (C_DATA if k == 4 else C_NET))
            return r
        rows = [row(k) for k in range(5)]
        self.play(FadeIn(hdr), Create(hl), FadeIn(rows[0]), run_time=1.2)
        self.cue(5)
        cur = d0
        for k in range(4):
            a = Arrow(o(k / 4, xs[k]), o((k + 1) / 4, xs[k + 1]), buff=0, color=C_NET, stroke_width=5,
                      max_tip_length_to_length_ratio=0.15)
            nd_ = Dot(o((k + 1) / 4, xs[k + 1]), radius=0.08, color=C_NET if k < 3 else C_DATA)
            self.play(GrowArrow(a), FadeIn(rows[k + 1]), run_time=1.0)
            self.play(FadeIn(nd_), run_time=0.3)
        self.cue(6)
        self.play(Flash(o(1, 2), color=WHITE, line_length=0.3, flash_radius=0.3), Indicate(rows[4][2], color=C_DATA), run_time=1.2)
        self.finish()


# ======================================================================
class OneStep(Timed):
    def construct(self):
        ax, base = make_plot()
        o = ax.c2p
        nd = noise_density(ax); dd = data_dots(ax)
        self.add(base, nd, dd)
        ttl = title("Why one step is not enough")
        self.cue(0)
        self.play(FadeIn(ttl), run_time=0.8)
        self.cue(1)
        y0 = Line(o(0, -3), o(0, 3), color=WHITE, stroke_width=5)
        f0 = MathTex(r"x_{t=0}=x_0", r"\ \text{ is independent of }\ ", r"x_1", font_size=34)
        f0[0].set_color(C_NOISE); f0[2].set_color(C_DATA)
        panel(f0, 2.2)
        self.play(ShowPassingFlash(y0, time_width=0.6), FadeIn(f0), run_time=1.5)
        self.cue(2)
        f1 = MathTex(r"u_0(x)", r"=", r"\mathbb E[x_1]", r"-x", font_size=40)
        f1[0].set_color(C_MARG); panel(f1, 1.3)
        self.play(Write(f1), run_time=1.5)
        self.cue(3)
        f1b = MathTex(r"u_0(x)", r"=", r"0", r"-x", font_size=40)
        f1b[0].set_color(C_MARG); f1b.move_to(f1, aligned_edge=LEFT)
        X0S = [-2.2, -1.2, -0.5, 0.4, 1.0, 1.6, 2.2]
        ga = VGroup(*[slope_arrow(ax, 0, x, -x, L=0.7, color=C_MARG, sw=5) for x in X0S if abs(x) > 0.3])
        self.play(TransformMatchingTex(f1, f1b), run_time=1.0)
        self.play(LaggedStart(*[GrowArrow(a) for a in ga], lag_ratio=0.1), run_time=1.2)
        self.cue(4)
        one = VGroup(*[Line(o(0, x), o(1, 0), color=C_NET, stroke_width=3.5) for x in X0S])
        f2 = MathTex(r"x_0", r"+", r"1\cdot(-x_0)", r"=", r"0", font_size=40)
        f2[0].set_color(C_NOISE); f2[2].set_color(C_NET)
        panel(f2, 0.35)
        lab = Text("one Euler step, h = 1", font_size=24, color=C_NET); panel(lab, -0.35).shift(RIGHT * 1.0)
        end = Dot(o(1, 0), radius=0.1, color=WHITE)
        self.play(FadeOut(ga), LaggedStart(*[Create(l) for l in one], lag_ratio=0.08), run_time=1.6)
        self.play(GrowFromCenter(end), Write(f2), FadeIn(lab), run_time=1.4)
        self.cue(5)
        cx = Cross(scale_factor=0.18, stroke_color=WHITE, stroke_width=6).move_to(o(1, 0))
        nl = Text("data mean, not data", font_size=24).next_to(o(1, 0), RIGHT, buff=0.3).shift(UP * 0.3)
        self.play(Create(cx), FadeIn(nl), run_time=0.9)
        self.cue(6)
        tl = VGroup(*[seg(ax, a, b, sw=2.5, op=0.55) for a, b in zip(TRAIN_X0[:8], TRAIN_X1[:8])])
        tr = VGroup(*[curve(ax, *marg_traj(x0), sw=3.5) for x0 in TRAJ_X0])
        self.play(FadeOut(one), FadeOut(f2), FadeOut(lab), FadeIn(tl), run_time=0.7)
        self.play(LaggedStart(*[Create(c) for c in tr], lag_ratio=0.05), run_time=1.8)
        self.cue(7)
        xs = euler(0.4, 4)
        four = VGroup(*[Line(o(k / 4, xs[k]), o((k + 1) / 4, xs[k + 1]), color=C_NET, stroke_width=5) for k in range(4)])
        fl = Text("4 steps: lands on +2", font_size=24, color=C_NET); panel(fl, -1.2)
        cv = Text("curved paths → several steps", font_size=28); panel(cv, -2.0)
        self.play(FadeOut(tl), tr.animate.set_stroke(opacity=0.4), run_time=0.6)
        self.play(Create(four), FadeIn(fl), run_time=1.4)
        self.play(FadeIn(cv), run_time=0.6)
        self.finish()


# ======================================================================
class Recap(Timed):
    def construct(self):
        ttl = title("Recap")
        items = [
            Tex(r"1.\ learns a velocity field ", r"$v_\theta(x,t)$", font_size=40),
            Tex(r"2.\ regresses on ", r"$x_1-x_0$", r" along ", r"$x_t=(1-t)\,x_0+t\,x_1$", font_size=40),
            Tex(r"3.\ optimum: ", r"$v^*=u_t(x)=\mathbb E[x_1-x_0\mid x_t=x]$", font_size=40),
            Tex(r"4.\ ", r"$u_t$", r" moves ", r"$p_0$", r" to ", r"$p_1$", r" (continuity equation)", font_size=40),
            Tex(r"5.\ ", r"$\min_\theta \mathcal L_{\mathrm{CFM}}=\mathbb E\,\|x_1-x_0-u_t(x_t)\|^2>0$", font_size=40),
            Tex(r"6.\ sample: ", r"$\dot x=v_\theta(x,t)$", r" from $t=0$ (noise) to $t=1$ (data)", font_size=40),
        ]
        items[0][1].set_color(C_NET)
        items[1][1].set_color(C_COND)
        items[2][1].set_color(C_MARG)
        items[3][1].set_color(C_MARG); items[3][3].set_color(C_NOISE); items[3][5].set_color(C_DATA)
        items[5][1].set_color(C_NET)
        g = VGroup(*items).arrange(DOWN, aligned_edge=LEFT, buff=0.42)
        g.move_to(DOWN * 0.25).to_edge(LEFT, buff=0.8)
        self.cue(0)
        self.play(FadeIn(ttl), run_time=0.7)
        for i, it in enumerate(items):
            self.cue(i + 1)
            self.play(FadeIn(it, shift=RIGHT * 0.2), run_time=0.9)
        self.finish()
