import json
from manim import *

DUR = json.load(open("audio/durations.json"))
CUES = {k: [c["t"] for c in v] for k, v in json.load(open("audio/cues.json")).items()}

EPS = 0.2
# Fixed color meaning across all scenes
C_UNCLIP = BLUE      # unclipped term  r * A
C_CLIP = YELLOW      # clipped term    clip(r) * A
C_MIN = GREEN        # L^CLIP = min(...)
C_ZERO = RED         # zero-gradient region
C_BAND = GREY_B      # trust interval [1-eps, 1+eps]


def clipr(r):
    return max(1 - EPS, min(r, 1 + EPS))


class Timed(Scene):
    """Scene whose beats are placed at sentence start times of its narration."""

    def setup(self):
        self.sid = type(self).__name__
        self.T = DUR[self.sid]
        self.C = CUES[self.sid]

    def until(self, t):
        dt = t - self.renderer.time
        if dt > 1 / 60:
            self.wait(dt)

    def cue(self, i, delay=0.0):
        self.until(self.C[i] + delay)

    def finish(self, extra=0.0):
        self.until(self.T + extra)


def heading(text):
    return Text(text, font_size=36, weight=BOLD).to_edge(UP, buff=0.4)


def lclip_formula():
    m = MathTex(
        r"L^{\mathrm{CLIP}}(\theta)", r"=", r"\hat{\mathbb{E}}_t\Big[", r"\min", r"\Big(",
        r"r_t(\theta)", r"\hat{A}_t", r",\;",
        r"\mathrm{clip}\big(", r"r_t(\theta)", r",\,1-\epsilon,\,1+\epsilon\big)", r"\hat{A}_t",
        r"\Big)\Big]",
    )
    m[3].set_color(C_MIN)
    m[5].set_color(C_UNCLIP)
    m[6].set_color(C_UNCLIP)
    for i in (8, 9, 10, 11):
        m[i].set_color(C_CLIP)
    return m


def make_axes(ylo, yhi, x_len=8.0, y_len=5.0, xmax=2.0):
    ax = Axes(
        x_range=[0, xmax, 0.2], y_range=[ylo, yhi, 0.5],
        x_length=x_len, y_length=y_len,
        axis_config={"include_tip": False, "stroke_width": 2, "tick_size": 0.05},
    )
    return ax


def tick_labels(ax, values, above=False, size=26):
    g = VGroup()
    for v in values:
        lab = MathTex(f"{v:g}", font_size=size)
        p = ax.c2p(v, 0)
        lab.next_to(p, UP if above else DOWN, buff=0.15)
        g.add(lab)
    return g


def r_label(ax, above=False):
    lab = MathTex(r"r_t(\theta)", font_size=32)
    lab.next_to(ax.c2p(ax.x_range[1], 0), RIGHT, buff=0.25)
    return lab


def band(ax, ylo, yhi):
    return Rectangle(
        width=ax.c2p(1 + EPS, 0)[0] - ax.c2p(1 - EPS, 0)[0],
        height=ax.c2p(0, yhi)[1] - ax.c2p(0, ylo)[1],
        stroke_width=0, fill_color=C_BAND, fill_opacity=0.18,
    ).move_to(ax.c2p(1, (ylo + yhi) / 2))


def region(ax, x0, x1, ylo, yhi, color=C_ZERO, opacity=0.18):
    return Rectangle(
        width=ax.c2p(x1, 0)[0] - ax.c2p(x0, 0)[0],
        height=ax.c2p(0, yhi)[1] - ax.c2p(0, ylo)[1],
        stroke_width=0, fill_color=color, fill_opacity=opacity,
    ).move_to(ax.c2p((x0 + x1) / 2, (ylo + yhi) / 2))


def poly(ax, pts, color, width=5):
    return VMobject().set_points_as_corners([ax.c2p(x, y) for x, y in pts]).set_stroke(color, width)


def unclip_pts(A, xmax=2.0):
    return [(0, 0), (xmax, xmax * A)]


def clip_pts(A, xmax=2.0):
    return [(0, (1 - EPS) * A), (1 - EPS, (1 - EPS) * A), (1 + EPS, (1 + EPS) * A), (xmax, (1 + EPS) * A)]


def min_pts(A, xmax=2.0):
    if A > 0:
        return [(0, 0), (1 + EPS, (1 + EPS) * A), (xmax, (1 + EPS) * A)]
    return [(0, (1 - EPS) * A), (1 - EPS, (1 - EPS) * A), (xmax, xmax * A)]


# ---------------------------------------------------------------- scenes


class Intro(Timed):
    def construct(self):
        title = Text("PPO: the clipped surrogate objective", font_size=40, weight=BOLD).to_edge(UP, buff=0.5)
        self.play(Write(title), run_time=1.5)

        # collect a batch with the current (old) policy
        pol = VGroup(RoundedRectangle(width=2.6, height=1.1, corner_radius=0.15, color=WHITE),
                     MathTex(r"\pi_{\theta_{\mathrm{old}}}", font_size=44))
        pol[1].move_to(pol[0])
        pol.move_to(LEFT * 4.5 + UP * 0.6)
        batch = VGroup(RoundedRectangle(width=3.6, height=1.1, corner_radius=0.15, color=WHITE),
                       MathTex(r"\{(s_t, a_t, \hat{A}_t)\}", font_size=38))
        batch[1].move_to(batch[0])
        batch.move_to(RIGHT * 0.2 + UP * 0.6)
        a1 = Arrow(pol.get_right(), batch.get_left(), buff=0.15)
        lab1 = Text("collect a batch", font_size=22).next_to(a1, UP, buff=0.7)
        self.play(FadeIn(pol), GrowArrow(a1), FadeIn(lab1), FadeIn(batch), run_time=2.0)

        self.cue(1)
        upd = VGroup(RoundedRectangle(width=2.8, height=1.1, corner_radius=0.15, color=WHITE),
                     MathTex(r"\theta \leftarrow \theta + \alpha \nabla_\theta L", font_size=34))
        upd[1].move_to(upd[0])
        upd.move_to(RIGHT * 4.9 + UP * 0.6)
        a2 = CurvedArrow(batch.get_top() + RIGHT * 0.6, upd.get_top() + LEFT * 0.3, angle=-PI / 2.2)
        a3 = CurvedArrow(upd.get_bottom() + LEFT * 0.3, batch.get_bottom() + RIGHT * 0.6, angle=-PI / 2.2)
        lab2 = Text("K epochs on the same batch", font_size=24).next_to(a3, DOWN, buff=0.15)
        self.play(FadeIn(upd), Create(a2), Create(a3), FadeIn(lab2), run_time=2.5)

        # the policy drifts away from the one that collected the data
        self.cue(3)
        line = NumberLine(x_range=[0, 10, 1], length=9, include_ticks=False).move_to(DOWN * 2.6)
        d_old = Dot(line.n2p(1), color=GREY_B, radius=0.11)
        l_old = MathTex(r"\theta_{\mathrm{old}}", font_size=34, color=GREY_B).next_to(d_old, UP)
        d_new = Dot(line.n2p(1), color=WHITE, radius=0.11)
        l_new = always_redraw(lambda: MathTex(r"\theta", font_size=34).next_to(d_new, UP))
        self.play(Create(line), FadeIn(d_old), FadeIn(l_old), FadeIn(d_new), run_time=1.0)
        self.add(l_new)
        self.play(d_new.animate.move_to(line.n2p(6.5)), run_time=3.0, rate_func=smooth)
        brace = BraceBetweenPoints(d_old.get_center(), d_new.get_center(), DOWN, buff=0.15)
        self.play(GrowFromCenter(brace), run_time=0.6)

        self.cue(4)
        q = Text("how far before the old data lies?", font_size=28, color=YELLOW).next_to(brace, DOWN, buff=0.1)
        self.play(FadeIn(q, shift=UP * 0.2), run_time=0.8)

        self.cue(5)
        everything = VGroup(pol, batch, a1, a2, a3, lab1, lab2, upd, line, d_old, l_old, d_new, l_new, brace, q)
        self.play(FadeOut(everything), run_time=0.8)
        f = lclip_formula().scale(0.95).move_to(UP * 0.2)
        self.play(Write(f), run_time=2.5)

        self.cue(6, 1.4)
        b_ratio = VGroup(SurroundingRectangle(f[5], buff=0.03, color=WHITE),
                         SurroundingRectangle(f[9], buff=0.03, color=WHITE))
        t_ratio = Text("ratio", font_size=26).next_to(b_ratio[0], DOWN, buff=0.25)
        self.play(Create(b_ratio), FadeIn(t_ratio), run_time=0.6)
        self.until(self.C[6] + 2.3)
        b_clip = SurroundingRectangle(VGroup(f[8], f[10]), buff=0.08, color=C_CLIP)
        t_clip = Text("clip", font_size=26, color=C_CLIP).next_to(b_clip, UP, buff=0.2)
        self.play(Create(b_clip), FadeIn(t_clip), run_time=0.6)
        self.until(self.C[6] + 3.2)
        b_min = SurroundingRectangle(f[3], buff=0.08, color=C_MIN)
        t_min = Text("min", font_size=26, color=C_MIN).next_to(b_min, UP, buff=0.2)
        self.play(Create(b_min), FadeIn(t_min), run_time=0.6)
        self.finish()


class Ratio(Timed):
    def construct(self):
        h = heading("1.  The probability ratio")
        self.play(FadeIn(h), run_time=1.0)

        self.cue(1)
        rdef = MathTex(r"r_t(\theta)", r"=",
                       r"{\pi_\theta(a_t\mid s_t)", r"\over", r"\pi_{\theta_{\mathrm{old}}}(a_t\mid s_t)}",
                       font_size=52).move_to(UP * 1.5 + LEFT * 1.5)
        n_lab = Text("new policy", font_size=24).next_to(rdef[2], RIGHT, buff=1.0)
        d_lab = Text("old policy (collected the data)", font_size=24, color=GREY_B).next_to(rdef[4], RIGHT, buff=0.7)
        n_arr = Arrow(n_lab.get_left(), rdef[2].get_right(), buff=0.1, stroke_width=3, max_tip_length_to_length_ratio=0.15)
        d_arr = Arrow(d_lab.get_left(), rdef[4].get_right(), buff=0.1, stroke_width=3, max_tip_length_to_length_ratio=0.15, color=GREY_B)
        self.play(Write(rdef[:2]), run_time=1.0)
        self.play(Write(rdef[2]), FadeIn(n_lab), GrowArrow(n_arr), run_time=1.5)
        self.play(Write(rdef[3:]), FadeIn(d_lab), GrowArrow(d_arr), run_time=1.5)

        self.cue(2)
        eq1 = MathTex(r"\theta = \theta_{\mathrm{old}} \;\Longrightarrow\; r_t(\theta) = 1", font_size=40).next_to(rdef, DOWN, buff=0.6).align_to(rdef, LEFT)
        self.play(Write(eq1), run_time=1.5)

        self.cue(3)
        lcpi = MathTex(r"L^{\mathrm{CPI}}(\theta)", r"=", r"\hat{\mathbb{E}}_t\big[", r"r_t(\theta)\,\hat{A}_t", r"\big]", font_size=46)
        lcpi[3].set_color(C_UNCLIP)
        lcpi.next_to(eq1, DOWN, buff=0.6).align_to(rdef, LEFT)
        self.play(Write(lcpi), run_time=2.0)

        self.cue(4)
        cpi_lab = Text("conservative policy iteration surrogate", font_size=24, color=GREY_B).next_to(lcpi, RIGHT, buff=0.5)
        self.play(FadeIn(cpi_lab), run_time=0.8)

        self.cue(5)
        is_lab = Text("importance-sampled estimate of\nthe improvement of new over old", font_size=24, color=GREY_B,
                      line_spacing=0.8).next_to(lcpi, RIGHT, buff=0.5)
        self.play(FadeTransform(cpi_lab, is_lab), run_time=0.8)

        self.cue(6)
        grad = MathTex(r"\nabla_\theta L^{\mathrm{CPI}}\Big|_{\theta=\theta_{\mathrm{old}}}", r"=",
                       r"\hat{\mathbb{E}}_t\big[\nabla_\theta \log \pi_\theta(a_t\mid s_t)\,\hat{A}_t\big]",
                       font_size=40).next_to(lcpi, DOWN, buff=0.6).align_to(rdef, LEFT)
        pg = Text("= vanilla policy gradient", font_size=24, color=GREY_B).next_to(grad, RIGHT, buff=0.4)
        self.play(Write(grad), run_time=2.0)
        self.play(FadeIn(pg), run_time=0.6)

        # switch to the 1-D picture: objective as a function of r
        self.cue(7)
        self.play(FadeOut(VGroup(rdef, n_lab, d_lab, n_arr, d_arr, eq1, is_lab, grad, pg)),
                  lcpi.animate.scale(0.8).to_corner(UR, buff=0.5).shift(DOWN * 0.6), run_time=1.0)
        ax = make_axes(-0.3, 2.6, x_len=8, y_len=4.8, xmax=2.4).move_to(DOWN * 0.6 + LEFT * 1.2)
        ticks = tick_labels(ax, [0.5, 1, 1.5, 2])
        rl = r_label(ax)
        fuzz = VGroup(*[region(ax, 1 - w, 1 + w, -0.3, 2.6, color=WHITE, opacity=0.05) for w in (0.1, 0.18, 0.26, 0.34)])
        rel = Text("estimate reliable", font_size=22).next_to(ax.c2p(1, 2.6), UP, buff=0.1)
        self.play(Create(ax), FadeIn(ticks), FadeIn(rl), run_time=1.0)
        self.play(FadeIn(fuzz), FadeIn(rel), run_time=0.8)

        self.cue(8)
        line = poly(ax, unclip_pts(1, 2.4), C_UNCLIP)
        llab = MathTex(r"r_t\hat{A}_t\;\;(\hat{A}_t>0)", font_size=32, color=C_UNCLIP).next_to(ax.c2p(2.4, 2.4), RIGHT, buff=0.15)
        self.play(Create(line), FadeIn(llab), run_time=1.5)

        self.cue(9)
        rt = ValueTracker(1.0)
        dot = always_redraw(lambda: Dot(ax.c2p(rt.get_value(), rt.get_value()), color=WHITE, radius=0.09))
        self.add(dot)
        up = Arrow(ax.c2p(1.6, 1.15), ax.c2p(2.25, 1.8), buff=0, color=WHITE, stroke_width=4)
        up_lab = Text("push r up", font_size=24).next_to(up, RIGHT, buff=0.1)
        self.play(rt.animate.set_value(2.35), GrowArrow(up), FadeIn(up_lab), run_time=3.0, rate_func=smooth)

        self.cue(10)
        stop = Text("nothing says stop", font_size=30, color=ORANGE).next_to(ax.c2p(0.3, 2.3), RIGHT, buff=0)
        self.play(FadeIn(stop, scale=1.1), run_time=0.6)
        self.finish()


class Clip(Timed):
    def construct(self):
        h = heading("2.  Clip the ratio")
        self.play(FadeIn(h), run_time=1.0)

        self.cue(1)
        cdef = MathTex(r"\mathrm{clip}(r,\,1-\epsilon,\,1+\epsilon)", r"=",
                       r"\max\big(1-\epsilon,\ \min(r,\,1+\epsilon)\big)", font_size=40).next_to(h, DOWN, buff=0.4)
        cdef[0].set_color(C_CLIP)
        self.play(Write(cdef), run_time=2.0)
        ax = make_axes(0, 2.0, x_len=7.5, y_len=4.2).move_to(DOWN * 1.1 + LEFT * 0.8)
        ticks = tick_labels(ax, [0.5, 1, 1.5, 2])
        rl = r_label(ax)
        ident = DashedVMobject(poly(ax, [(0, 0), (2, 2)], GREY_B, 2), num_dashes=40)
        cl = poly(ax, clip_pts(1), C_CLIP)
        cl_lab = MathTex(r"\mathrm{clip}(r)", font_size=32, color=C_CLIP).next_to(ax.c2p(2, 1.2), RIGHT, buff=0.15)
        id_lab = MathTex(r"r", font_size=32, color=GREY_B).next_to(ax.c2p(2, 2), RIGHT, buff=0.15)
        self.play(Create(ax), FadeIn(ticks), FadeIn(rl), Create(ident), FadeIn(id_lab), run_time=1.0)
        self.play(Create(cl), FadeIn(cl_lab), run_time=1.5)

        self.cue(2)
        bd = band(ax, 0, 2.0)
        btxt = MathTex(r"[1-\epsilon,\ 1+\epsilon] = [0.8,\ 1.2]", font_size=30).next_to(ax.c2p(1, 2.0), UP, buff=0.1)
        etxt = MathTex(r"\epsilon = 0.2", font_size=34).to_corner(UR, buff=0.6).shift(DOWN * 1.4)
        self.play(FadeIn(bd), FadeIn(etxt), run_time=1.0)
        self.play(FadeIn(btxt), run_time=1.0)

        self.cue(3)
        flat_l = poly(ax, [(0, 0.8), (0.8, 0.8)], C_CLIP, 10)
        flat_r = poly(ax, [(1.2, 1.2), (2, 1.2)], C_CLIP, 10)
        self.play(Create(flat_l), Create(flat_r), run_time=1.0)

        self.cue(4)
        zl = region(ax, 0, 0.8, 0, 2.0)
        zr = region(ax, 1.2, 2.0, 0, 2.0)
        g0l = MathTex(r"\nabla = 0", font_size=30, color=C_ZERO).move_to(ax.c2p(0.4, 1.5))
        g0r = MathTex(r"\nabla = 0", font_size=30, color=C_ZERO).move_to(ax.c2p(1.6, 0.6))
        self.play(FadeIn(zl), FadeIn(zr), FadeIn(g0l), FadeIn(g0r), run_time=1.0)

        self.cue(5)
        rt = ValueTracker(1.0)
        dot = always_redraw(lambda: Dot(ax.c2p(rt.get_value(), clipr(rt.get_value())), color=WHITE, radius=0.09))
        read = always_redraw(lambda: MathTex(
            rf"r = {rt.get_value():.2f},\quad \mathrm{{clip}}(r) = {clipr(rt.get_value()):.2f}", font_size=30
        ).next_to(btxt, UP, buff=0.15))
        self.play(FadeIn(dot), FadeIn(read), run_time=0.5)
        self.play(rt.animate.set_value(1.85), run_time=3.5, rate_func=smooth)
        self.wait(0.5)

        self.cue(6)
        plot = VGroup(ax, rl, ident, id_lab, cl, cl_lab, bd, btxt, flat_l, flat_r, zl, zr, g0l, g0r, dot, read, etxt, ticks)
        self.play(FadeOut(plot), FadeOut(cdef), run_time=1.0)

        self.cue(7)
        f = lclip_formula().scale(0.95).move_to(UP * 0.3)
        self.play(Write(f), run_time=2.0)
        u = Text("unclipped", font_size=24, color=C_UNCLIP).next_to(VGroup(f[5], f[6]), DOWN, buff=0.35)
        c = Text("clipped", font_size=24, color=C_CLIP).next_to(VGroup(f[8], f[11]), DOWN, buff=0.35)
        bm = SurroundingRectangle(f[3], buff=0.08, color=C_MIN)
        self.play(FadeIn(u), FadeIn(c), Create(bm), run_time=1.0)
        self.finish()


def adv_setup(scene, A):
    """Shared axes for the positive / negative advantage scenes."""
    if A > 0:
        ylo, yhi = -0.4, 2.2
    else:
        ylo, yhi = -2.2, 0.4
    ax = make_axes(ylo, yhi, x_len=8, y_len=5.0).move_to(DOWN * 0.45 + LEFT * 1.0)
    ticks = tick_labels(ax, [0.5, 0.8, 1.2, 1.5, 2], above=A < 0, size=24)
    rl = r_label(ax, above=A < 0)
    bd = band(ax, ylo, yhi)
    return ax, ticks, rl, bd, ylo, yhi


class PositiveAdv(Timed):
    def construct(self):
        A = 1.0
        h = heading("3.  Positive advantage")
        sign = MathTex(r"\hat{A}_t > 0", font_size=40).to_corner(UR, buff=0.5)
        self.play(FadeIn(h), FadeIn(sign), run_time=1.0)
        ax, ticks, rl, bd, ylo, yhi = adv_setup(self, A)

        self.cue(1)
        goal = Text("better than expected: make it more likely", font_size=26).next_to(h, DOWN, buff=0.2)
        self.play(FadeIn(goal), Create(ax), FadeIn(ticks), FadeIn(rl), FadeIn(bd), run_time=1.5)

        self.cue(2)
        un = poly(ax, unclip_pts(A), C_UNCLIP)
        un_lab = MathTex(r"r_t\hat{A}_t", font_size=34, color=C_UNCLIP).next_to(ax.c2p(2, 2 * A), RIGHT, buff=0.15)
        self.play(Create(un), FadeIn(un_lab), run_time=1.5)

        self.cue(3)
        cl = poly(ax, clip_pts(A), C_CLIP)
        cl_lab = MathTex(r"\mathrm{clip}(r_t)\hat{A}_t", font_size=34, color=C_CLIP).next_to(ax.c2p(2, 1.2 * A), RIGHT, buff=0.15)
        self.play(Create(cl), FadeIn(cl_lab), run_time=1.5)

        self.cue(4)
        self.play(Indicate(cl, color=C_CLIP, scale_factor=1.03), run_time=1.0)

        self.cue(5)
        mn = poly(ax, min_pts(A), C_MIN, 9)
        mn_lab = MathTex(r"L^{\mathrm{CLIP}}_t = \min(\cdot,\cdot)", font_size=34, color=C_MIN).move_to(ax.c2p(0.42, 1.75))
        self.play(un.animate.set_stroke(opacity=0.45), cl.animate.set_stroke(opacity=0.45), run_time=0.4)
        self.add(un, cl)
        self.play(Create(mn), FadeIn(mn_lab), run_time=1.5)

        # region r > 1 + eps: clipped term is smaller
        self.cue(6)
        p_u = Dot(ax.c2p(1.7, 1.7 * A), color=C_UNCLIP)
        p_c = Dot(ax.c2p(1.7, 1.2 * A), color=C_CLIP)
        arr = Arrow(p_u.get_center(), p_c.get_center(), buff=0.1, color=WHITE, stroke_width=4)
        arr_lab = Text("smaller", font_size=22).next_to(arr, RIGHT, buff=0.1)
        self.play(FadeIn(p_u), FadeIn(p_c), GrowArrow(arr), FadeIn(arr_lab), run_time=1.2)

        self.cue(7)
        zr = region(ax, 1 + EPS, 2.0, ylo, yhi)
        g0 = MathTex(r"\nabla_\theta L^{\mathrm{CLIP}}_t = 0", font_size=30, color=C_ZERO).move_to(ax.c2p(1.6, 0.35))
        self.play(FadeIn(zr), FadeIn(g0), FadeOut(arr), FadeOut(arr_lab), run_time=1.0)

        self.cue(8)
        stop = Text("already > 20% more likely: stop pushing", font_size=24, color=C_ZERO).next_to(ax, DOWN, buff=0.25)
        self.play(FadeIn(stop), FadeOut(p_u), FadeOut(p_c), run_time=0.8)

        # region r < 1 - eps: unclipped term is smaller
        self.cue(9)
        q_u = Dot(ax.c2p(0.45, 0.45 * A), color=C_UNCLIP)
        q_c = Dot(ax.c2p(0.45, 0.8 * A), color=C_CLIP)
        arr2 = Arrow(q_c.get_center(), q_u.get_center(), buff=0.1, color=WHITE, stroke_width=4)
        arr2_lab = Text("smaller", font_size=22).next_to(arr2, LEFT, buff=0.1)
        self.play(FadeOut(stop), FadeIn(q_u), FadeIn(q_c), GrowArrow(arr2), FadeIn(arr2_lab), run_time=1.2)

        self.cue(10)
        slope = MathTex(r"\text{slope} = \hat{A}_t > 0", font_size=30, color=C_MIN).move_to(ax.c2p(0.55, 1.15))
        self.play(FadeOut(arr2), FadeOut(arr2_lab), FadeOut(q_c), FadeIn(slope), run_time=0.8)

        self.cue(11)
        rt = ValueTracker(0.45)
        dot = always_redraw(lambda: Dot(ax.c2p(rt.get_value(), rt.get_value() * A), color=WHITE, radius=0.1))
        self.remove(q_u)
        self.add(dot)
        pull = Text("gradient pulls r back up", font_size=24, color=C_MIN).next_to(ax, DOWN, buff=0.25)
        self.play(FadeIn(pull), rt.animate.set_value(0.95), run_time=3.0, rate_func=smooth)
        self.finish()


class NegativeAdv(Timed):
    def construct(self):
        A = -1.0
        h = heading("4.  Negative advantage")
        sign = MathTex(r"\hat{A}_t < 0", font_size=40).to_corner(UR, buff=0.5)
        self.play(FadeIn(h), FadeIn(sign), run_time=1.0)
        ax, ticks, rl, bd, ylo, yhi = adv_setup(self, A)

        self.cue(1)
        goal = Text("worse than expected: make it less likely", font_size=26).next_to(h, DOWN, buff=0.2)
        self.play(FadeIn(goal), Create(ax), FadeIn(ticks), FadeIn(rl), FadeIn(bd), run_time=1.5)

        self.cue(2)
        un = poly(ax, unclip_pts(A), C_UNCLIP)
        un_lab = MathTex(r"r_t\hat{A}_t", font_size=34, color=C_UNCLIP).next_to(ax.c2p(2, 2 * A), RIGHT, buff=0.15)
        cl = poly(ax, clip_pts(A), C_CLIP)
        cl_lab = MathTex(r"\mathrm{clip}(r_t)\hat{A}_t", font_size=34, color=C_CLIP).next_to(ax.c2p(2, 1.2 * A), RIGHT, buff=0.15)
        self.play(Create(un), FadeIn(un_lab), Create(cl), FadeIn(cl_lab), run_time=1.8)

        self.cue(3)
        self.play(Indicate(un, color=C_UNCLIP, scale_factor=1.03), run_time=1.2)

        # r < 1 - eps: clipped (flat) term is smaller
        self.cue(4)
        mn = poly(ax, min_pts(A), C_MIN, 9)
        mn_lab = MathTex(r"L^{\mathrm{CLIP}}_t = \min(\cdot,\cdot)", font_size=34, color=C_MIN).move_to(ax.c2p(0.42, -1.75))
        self.play(un.animate.set_stroke(opacity=0.45), cl.animate.set_stroke(opacity=0.45), run_time=0.4)
        self.play(Create(mn), FadeIn(mn_lab), run_time=1.0)
        p_u = Dot(ax.c2p(0.45, 0.45 * A), color=C_UNCLIP)
        p_c = Dot(ax.c2p(0.45, 0.8 * A), color=C_CLIP)
        arr = Arrow(p_u.get_center(), p_c.get_center(), buff=0.1, color=WHITE, stroke_width=4)
        arr_lab = Text("smaller", font_size=22).next_to(arr, RIGHT, buff=0.1)
        self.play(FadeIn(p_u), FadeIn(p_c), GrowArrow(arr), FadeIn(arr_lab), run_time=1.2)

        self.cue(5)
        zl = region(ax, 0, 1 - EPS, ylo, yhi)
        g0 = MathTex(r"\nabla_\theta L^{\mathrm{CLIP}}_t = 0", font_size=30, color=C_ZERO).move_to(ax.c2p(0.4, -1.2))
        self.play(FadeIn(zl), FadeIn(g0), FadeOut(arr), FadeOut(arr_lab), FadeOut(p_u), FadeOut(p_c),
                  mn_lab.animate.move_to(ax.c2p(1.62, -0.5)), run_time=1.0)

        self.cue(6)
        stop = Text("already > 20% less likely: stop pushing", font_size=24, color=C_ZERO).next_to(ax, DOWN, buff=0.25)
        self.play(FadeIn(stop), run_time=0.8)

        # r > 1 + eps: unclipped term is smaller -> unbounded penalty
        self.cue(7)
        q_u = Dot(ax.c2p(1.7, 1.7 * A), color=C_UNCLIP)
        q_c = Dot(ax.c2p(1.7, 1.2 * A), color=C_CLIP)
        arr2 = Arrow(q_c.get_center(), q_u.get_center(), buff=0.1, color=WHITE, stroke_width=4)
        arr2_lab = Text("smaller", font_size=22).next_to(arr2, RIGHT, buff=0.1)
        self.play(FadeOut(stop), FadeIn(q_u), FadeIn(q_c), GrowArrow(arr2), FadeIn(arr2_lab), run_time=1.2)

        self.cue(8)
        unb = Text("keeps falling: no bound", font_size=24, color=C_MIN).next_to(ax, DOWN, buff=0.25)
        self.play(FadeOut(arr2), FadeOut(arr2_lab), FadeOut(q_c), FadeIn(unb),
                  Indicate(VGroup(mn), color=C_MIN, scale_factor=1.02), run_time=1.2)

        self.cue(9)
        rt = ValueTracker(1.7)
        dot = always_redraw(lambda: Dot(ax.c2p(rt.get_value(), rt.get_value() * A), color=WHITE, radius=0.1))
        self.remove(q_u)
        self.add(dot)
        push = Text("full penalty: gradient pushes r back down", font_size=24, color=C_MIN).next_to(ax, DOWN, buff=0.25)
        self.play(FadeOut(unb), run_time=0.3)
        self.play(FadeIn(push), rt.animate.set_value(1.1), run_time=3.2, rate_func=smooth)
        self.finish()


class Numbers(Timed):
    def construct(self):
        h = heading("5.  Worked example")
        self.play(FadeIn(h), run_time=0.8)

        xs = [-5.9, -4.6, -3.3, -1.7, 0.7, 3.0, 5.3]
        ys = [1.35, 0.35, -0.75, -1.85, -2.95]
        hdr_tex = [r"\text{case}", r"\hat{A}_t", r"r_t", r"r_t\hat{A}_t", r"\mathrm{clip}(r_t)\hat{A}_t",
                   r"\min", r"\nabla_\theta L^{\mathrm{CLIP}}_t"]
        hdr_col = [GREY_B, WHITE, WHITE, C_UNCLIP, C_CLIP, C_MIN, WHITE]

        def cell(tex, col, row, color=WHITE):
            return MathTex(tex, font_size=36, color=color).move_to([xs[col], ys[row], 0])

        self.cue(1)
        eps = MathTex(r"\epsilon = 0.2 \qquad 1-\epsilon = 0.8,\ \ 1+\epsilon = 1.2", font_size=34).next_to(h, DOWN, buff=0.3)
        hdr = VGroup(*[cell(t, i, 0, c) for i, (t, c) in enumerate(zip(hdr_tex, hdr_col))])
        rule = Line([-6.6, ys[0] - 0.5, 0], [6.6, ys[0] - 0.5, 0], stroke_width=2, color=GREY_B)
        self.play(FadeIn(eps), FadeIn(hdr), Create(rule), run_time=1.5)

        rows = [
            # A,   r,     rA,      clip(r)A,                 min,     which,  grad
            ("+2", "1.5", "3.0", r"1.2\times 2 = 2.4", "2.4", "clip", "0"),
            ("+2", "0.6", "1.2", r"0.8\times 2 = 1.6", "1.2", "un", r"\hat{A}_t\nabla_\theta r_t"),
            ("-2", "1.5", "-3.0", r"1.2\times(-2) = -2.4", "-3.0", "un", r"\hat{A}_t\nabla_\theta r_t"),
            ("-2", "0.6", "-1.2", r"0.8\times(-2) = -1.6", "-1.6", "clip", "0"),
        ]
        # cue indices for each row: case, (A, r), values, min
        row_cues = [(2, 3, (4, 5), 6), (7, 8, (9, 9.5), 10), (11, 12, (13, 13.5), 14), (15, 16, (17, 17.5), 18)]

        def at(c):
            if isinstance(c, float):
                i = int(c)
                self.cue(i, 2.0)
            else:
                self.cue(c)

        for k, (row, cues) in enumerate(zip(rows, row_cues)):
            R = k + 1
            a, r, ra, cra, mn, which, g = row
            at(cues[0])
            lab = cell(str(R), 0, R, GREY_B)
            self.play(FadeIn(lab), run_time=0.4)
            at(cues[1])
            self.play(FadeIn(cell(a, 1, R)), FadeIn(cell(r, 2, R)), run_time=0.6)
            at(cues[2][0])
            c_un = cell(ra, 3, R, C_UNCLIP)
            self.play(FadeIn(c_un), run_time=0.5)
            at(cues[2][1])
            c_cl = cell(cra, 4, R, C_CLIP)
            self.play(FadeIn(c_cl), run_time=0.5)
            at(cues[3])
            chosen = c_cl if which == "clip" else c_un
            box = SurroundingRectangle(chosen, color=C_MIN, buff=0.1)
            m = cell(mn, 5, R, C_MIN)
            gcol = C_ZERO if g == "0" else C_MIN
            gc = cell(g, 6, R, gcol)
            self.play(Create(box), FadeIn(m), run_time=0.6)
            self.play(FadeIn(gc), run_time=0.5)
        self.finish()


class WhyMin(Timed):
    def construct(self):
        h = heading("6.  What the min does")
        self.play(FadeIn(h), run_time=1.0)

        self.cue(1)
        lb = MathTex(r"L^{\mathrm{CLIP}}_t", r"=", r"\min\big(r_t\hat{A}_t,\ \mathrm{clip}(r_t)\hat{A}_t\big)",
                     r"\;\le\;", r"r_t\hat{A}_t", font_size=38).next_to(h, DOWN, buff=0.3)
        lb[0].set_color(C_MIN)
        lb[4].set_color(C_UNCLIP)
        lbt = Text("pessimistic lower bound on the unclipped surrogate", font_size=24, color=GREY_B).next_to(lb, DOWN, buff=0.15)
        self.play(Write(lb), run_time=1.8)
        self.play(FadeIn(lbt), run_time=0.6)

        # two small plots: A>0 (left) and A<0 (right)
        def small(A):
            ylo, yhi = (-0.4, 2.2) if A > 0 else (-2.2, 0.4)
            ax = make_axes(ylo, yhi, x_len=5.2, y_len=3.3)
            bd = band(ax, ylo, yhi)
            un = poly(ax, unclip_pts(A), C_UNCLIP, 3).set_stroke(opacity=0.85)
            mn = poly(ax, min_pts(A), C_MIN, 7)
            t = MathTex(r"\hat{A}_t>0" if A > 0 else r"\hat{A}_t<0", font_size=30)
            return ax, bd, un, mn, t, ylo, yhi

        axL, bdL, unL, mnL, tL, yloL, yhiL = small(1.0)
        axR, bdR, unR, mnR, tR, yloR, yhiR = small(-1.0)
        tkL = tick_labels(axL, [0.8, 1.2], size=20)
        tkR = tick_labels(axR, [0.8, 1.2], above=True, size=20)
        VGroup(axL, bdL, unL, mnL, tkL).shift(LEFT * 3.4 + DOWN * 1.6)
        VGroup(axR, bdR, unR, mnR, tkR).shift(RIGHT * 3.4 + DOWN * 1.6)
        tL.next_to(axL, UP, buff=0.1)
        tR.next_to(axR, UP, buff=0.1)

        self.cue(2)
        self.play(FadeIn(VGroup(axL, bdL, unL, tL, tkL, axR, bdR, unR, tR, tkR)), run_time=0.8)
        self.play(Create(mnL), Create(mnR), run_time=1.2)
        zL = region(axL, 1 + EPS, 2, yloL, yhiL)
        zR = region(axR, 0, 1 - EPS, yloR, yhiR)
        iL = Text("gain ignored", font_size=20, color=C_ZERO).move_to(axL.c2p(1.6, 0.4))
        iR = Text("gain ignored", font_size=20, color=C_ZERO).move_to(axR.c2p(0.4, -1.6))
        self.play(FadeIn(zL), FadeIn(zR), FadeIn(iL), FadeIn(iR), run_time=0.8)

        self.cue(3)
        wL = Text("worse: counted\nin full", font_size=20, color=C_MIN, line_spacing=0.8).move_to(axL.c2p(0.4, 1.3))
        wR = Text("worse: counted\nin full", font_size=20, color=C_MIN, line_spacing=0.8).move_to(axR.c2p(1.6, -0.5))
        self.play(FadeIn(wL), FadeIn(wR), run_time=0.8)

        # without the min: clipped term alone
        self.cue(4)
        no = Text("without the min: clipped term alone", font_size=26, color=C_CLIP).move_to(DOWN * 3.65)
        clL = poly(axL, clip_pts(1.0), C_CLIP, 7)
        clR = poly(axR, clip_pts(-1.0), C_CLIP, 7)
        self.play(FadeIn(no), Transform(mnL, clL), Transform(mnR, clR), FadeOut(wL), FadeOut(wR), run_time=1.5)

        self.cue(5)
        bL = region(axL, 0, 1 - EPS, yloL, yhiL)
        bR = region(axR, 1 + EPS, 2, yloR, yhiR)
        for b in (bL, bR):
            b.set_fill(C_ZERO, opacity=0.45).set_stroke(C_ZERO, 3, opacity=1)
        xL = Text("wrong way:\n∇ = 0", font_size=20, color=WHITE, line_spacing=0.8).move_to(axL.c2p(0.4, 1.7))
        xR = Text("wrong way:\n∇ = 0", font_size=20, color=WHITE, line_spacing=0.8).move_to(axR.c2p(1.6, -0.5))
        self.play(*[z.animate.set_fill(opacity=0.06) for z in (zL, zR)], iL.animate.set_opacity(0.3), iR.animate.set_opacity(0.3),
                  FadeIn(bL), FadeIn(bR), FadeIn(xL), FadeIn(xR), run_time=1.0)

        self.cue(6)
        self.play(FadeOut(VGroup(axL, bdL, unL, mnL, tL, tkL, zL, iL, bL, xL, axR, bdR, unR, mnR, tR, tkR, zR, iR, bR, xR, no, lbt)),
                  run_time=0.8)

        self.cue(7)
        c1 = Text("Clipping is not a hard trust region", font_size=34, weight=BOLD).move_to(UP * 0.4)
        self.play(FadeIn(c1), run_time=0.8)

        self.cue(8)
        c2 = Text("Zero gradient removes the incentive to leave [1-ε, 1+ε].", font_size=26).next_to(c1, DOWN, buff=0.5)
        c3 = Text("shared parameters → r can still drift outside",
                  font_size=24, color=GREY_B, line_spacing=0.9).next_to(c2, DOWN, buff=0.35)
        self.play(FadeIn(c2), run_time=0.8)
        self.play(FadeIn(c3), run_time=0.8)
        self.finish()


class Recap(Timed):
    def construct(self):
        h = heading("Recap")
        f = lclip_formula().scale(0.85).next_to(h, DOWN, buff=0.4)
        self.play(FadeIn(h), FadeIn(f), run_time=0.8)

        def item(label, color, text):
            a = Text(label, font_size=30, color=color, weight=BOLD)
            b = Text(text, font_size=28)
            return VGroup(a, b).arrange(RIGHT, buff=0.4)

        i1 = item("ratio", WHITE, "reuse data from the old policy (importance sampling)")
        i2 = item("clip", C_CLIP, "no incentive to move r past 1 ± ε")
        i3 = item("min", C_MIN, "ignore only gains, never losses (lower bound)")
        items = VGroup(i1, i2, i3).arrange(DOWN, aligned_edge=LEFT, buff=0.4).next_to(f, DOWN, buff=0.6)

        self.cue(1)
        self.play(FadeIn(i1, shift=RIGHT * 0.2), run_time=0.6)
        self.cue(2)
        self.play(FadeIn(i2, shift=RIGHT * 0.2), run_time=0.6)
        self.cue(3)
        self.play(FadeIn(i3, shift=RIGHT * 0.2), run_time=0.6)

        self.cue(3, 3.5)
        g = MathTex(
            r"\nabla_\theta L^{\mathrm{CLIP}}_t = \begin{cases} 0 & \hat{A}_t>0,\ r_t>1+\epsilon \ \text{ or }\ \hat{A}_t<0,\ r_t<1-\epsilon \\"
            r" \hat{A}_t\,\nabla_\theta r_t & \text{otherwise} \end{cases}",
            font_size=34,
        ).next_to(items, DOWN, buff=0.5)
        self.play(Write(g), run_time=2.0)
        self.finish(extra=2.5)
