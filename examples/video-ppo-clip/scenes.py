import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("EXPLAINER_SCRIPTS", os.path.join(_HERE, "..", "..", "explainer", "scripts")))
from timed import Timed
from manim import *

EPS = 0.2
# Color legend (one meaning each; see storyboard.md). Chosen to stay apart under red-green and
# blue-yellow color blindness, and every color has a second cue (line style, width, hatching, label).
C_UNCLIP = "#3D7EFF"   # unclipped term  r * A         thin solid blue line
C_CLIP = "#E69F00"     # clipped term    clip(r) * A   dashed orange line
C_MIN = WHITE          # L^CLIP = min(...)              thick solid white line
C_ZERO = "#9AA0A6"     # zero-gradient region           grey diagonal hatching + "∇ = 0" label
C_ZERO_TXT = "#C4C8CC" # text that names a zero gradient
C_BAND = GREY_B        # interval [1-eps, 1+eps]        light grey fill


def clipr(r):
    return max(1 - EPS, min(r, 1 + EPS))


def heading(text):
    return Text(text, font_size=36, weight=BOLD).to_edge(UP, buff=0.4)


def lclip_formula():
    m = MathTex(
        r"L^{\mathrm{CLIP}}(\theta)", r"=", r"\hat{\mathbb{E}}_t\Big[\,", r"\min", r"\,\Big(\,",
        r"r_t(\theta)", r"\hat{A}_t", r",\;",
        r"\mathrm{clip}\big(\,", r"r_t(\theta)", r"\,,\,1-\epsilon,\,1+\epsilon\big)", r"\hat{A}_t",
        r"\,\Big)\Big]",
    )
    m[5].set_color(C_UNCLIP)
    m[6].set_color(C_UNCLIP)
    for i in (8, 9, 10, 11):
        m[i].set_color(C_CLIP)
    return m


def make_axes(ylo, yhi, x_len=8.0, y_len=5.0, xmax=2.0):
    return Axes(
        x_range=[0, xmax, 0.2], y_range=[ylo, yhi, 0.5],
        x_length=x_len, y_length=y_len,
        axis_config={"include_tip": False, "stroke_width": 2, "tick_size": 0.05},
    )


def tick_labels(ax, values, above=False, size=26):
    g = VGroup()
    for v in values:
        lab = MathTex(f"{v:g}", font_size=size).add_background_rectangle(opacity=0.85, buff=0.03)
        lab.next_to(ax.c2p(v, 0), UP if above else DOWN, buff=0.15)
        g.add(lab)
    return g


def r_label(ax):
    return MathTex(r"r_t(\theta)", font_size=32).next_to(ax.c2p(ax.x_range[1], 0), RIGHT, buff=0.25)


def rect(ax, x0, x1, ylo, yhi, color, opacity):
    return Rectangle(
        width=ax.c2p(x1, 0)[0] - ax.c2p(x0, 0)[0],
        height=ax.c2p(0, yhi)[1] - ax.c2p(0, ylo)[1],
        stroke_width=0, fill_color=color, fill_opacity=opacity,
    ).move_to(ax.c2p((x0 + x1) / 2, (ylo + yhi) / 2))


def band(ax, ylo, yhi):
    return rect(ax, 1 - EPS, 1 + EPS, ylo, yhi, C_BAND, 0.18)


def hatch_rect(x0, y0, x1, y1, gap=0.2, color=C_ZERO, width=1.6, opacity=0.75):
    """45° hatching inside the screen rectangle [x0, x1] x [y0, y1]."""
    g = VGroup()
    c, step = y0 - x1 + gap, gap * np.sqrt(2)
    while c < y1 - x0:
        xs, xe = max(x0, y0 - c), min(x1, y1 - c)
        if xe - xs > 0.02:
            g.add(Line([xs, xs + c, 0], [xe, xe + c, 0], stroke_width=width, color=color, stroke_opacity=opacity))
        c += step
    return g


def zero_region(ax, x0, x1, ylo, yhi, **kw):
    """Zero-gradient region: a faint grey fill plus diagonal hatching (readable without color)."""
    p, q = ax.c2p(x0, ylo), ax.c2p(x1, yhi)
    return VGroup(rect(ax, x0, x1, ylo, yhi, C_ZERO, 0.08), hatch_rect(p[0], p[1], q[0], q[1], **kw))


def zero_tag(tex, size=30):
    return MathTex(tex, font_size=size, color=C_ZERO_TXT).add_background_rectangle(opacity=0.9, buff=0.06)


def poly(ax, pts, color, width=5):
    return VMobject().set_points_as_corners([ax.c2p(x, y) for x, y in pts]).set_stroke(color, width)


def dashed(ax, pts, color=C_CLIP, width=5, n=44):
    return DashedVMobject(poly(ax, pts, color, width), num_dashes=n, dashed_ratio=0.6)


def unclip_pts(A, xmax=2.0):
    return [(0, 0), (xmax, xmax * A)]


def clip_pts(A, xmax=2.0):
    return [(0, (1 - EPS) * A), (1 - EPS, (1 - EPS) * A), (1 + EPS, (1 + EPS) * A), (xmax, (1 + EPS) * A)]


def min_pts(A, xmax=2.0):
    if A > 0:
        return [(0, 0), (1 + EPS, (1 + EPS) * A), (xmax, (1 + EPS) * A)]
    return [(0, (1 - EPS) * A), (1 - EPS, (1 - EPS) * A), (xmax, xmax * A)]


def pt_un(p):
    """A value of the unclipped term: blue round dot."""
    return Dot(p, radius=0.09, color=C_UNCLIP)


def pt_cl(p):
    """A value of the clipped term: orange square (shape tells it apart without color)."""
    return Square(side_length=0.17, color=C_CLIP, fill_opacity=1, stroke_width=0).move_to(p)


def now_dot(p):
    """Where r is now: a white dot with a black rim, so it stays visible on the white min line."""
    return Dot(p, radius=0.12, color=WHITE).set_stroke(BLACK, 4, background=True)


def y_label(ax, tex=r"\text{objective}"):
    return MathTex(tex, font_size=26, color=GREY_B).next_to(ax.y_axis.get_end(), UP, buff=0.12)


def term_labels(ax, A):
    un_lab = MathTex(r"r_t\hat{A}_t", font_size=34, color=C_UNCLIP).next_to(ax.c2p(2, 2 * A), RIGHT, buff=0.15)
    cl_lab = MathTex(r"\mathrm{clip}(r_t)\hat{A}_t", font_size=34, color=C_CLIP).next_to(ax.c2p(2, 1.2 * A), RIGHT, buff=0.15)
    return un_lab, cl_lab


# ---------------------------------------------------------------- scenes


class Intro(Timed):
    def construct(self):
        title = Text("PPO: the clipped surrogate objective", font_size=40, weight=BOLD).to_edge(UP, buff=0.5)
        self.cue(0)
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
        self.play(d_new.animate.move_to(line.n2p(6.5)), run_time=2.6, rate_func=smooth)
        brace = BraceBetweenPoints(d_old.get_center(), d_new.get_center(), DOWN, buff=0.15)
        self.play(GrowFromCenter(brace), run_time=0.6)

        self.cue(4)
        q = Text("how far before the old data lies?", font_size=28, slant=ITALIC).next_to(brace, DOWN, buff=0.1)
        self.play(FadeIn(q, shift=UP * 0.2), run_time=0.8)

        self.cue(5)
        everything = VGroup(pol, batch, a1, a2, a3, lab1, lab2, upd, line, d_old, l_old, d_new, l_new, brace, q)
        self.play(FadeOut(everything), run_time=0.8)
        f = lclip_formula().scale(0.95).move_to(UP * 0.2)
        self.play(Write(f), run_time=2.5)

        self.cue(6, 1.4)
        b_ratio = VGroup(SurroundingRectangle(f[5], buff=0.07, color=C_UNCLIP),
                         SurroundingRectangle(f[9], buff=0.07, color=C_CLIP))
        t_ratio = VGroup(Text("ratio", font_size=26).next_to(b_ratio[0], DOWN, buff=0.25),
                         Text("ratio", font_size=26).next_to(b_ratio[1], DOWN, buff=0.25))
        self.play(Create(b_ratio), FadeIn(t_ratio), run_time=0.6)
        self.until(self.C[6] + 2.3)
        b_clip = SurroundingRectangle(VGroup(f[8], f[10]), buff=0.14, color=C_CLIP)
        t_clip = Text("clip", font_size=26, color=C_CLIP).next_to(b_clip, UP, buff=0.2)
        self.play(Create(b_clip), FadeIn(t_clip), run_time=0.6)
        self.until(self.C[6] + 3.2)
        b_min = SurroundingRectangle(f[3], buff=0.1, color=C_MIN, stroke_width=6)
        t_min = Text("min", font_size=26, weight=BOLD).next_to(b_min, UP, buff=0.2)
        self.play(Create(b_min), FadeIn(t_min), run_time=0.6)
        self.finish()


class Ratio(Timed):
    def construct(self):
        # open on the formula the intro ended with; the ratio stays lit
        f = lclip_formula().scale(0.95).move_to(UP * 0.2)
        self.add(f)
        h = heading("1.  The probability ratio")
        rest = [f[i] for i in range(len(f)) if i not in (5, 9)]
        self.cue(0)
        self.play(FadeIn(h), *[m.animate.set_opacity(0.25) for m in rest], run_time=1.0)

        self.cue(1)
        rdef = MathTex(r"r_t(\theta)", r"=",
                       r"{\pi_\theta(a_t\mid s_t)", r"\over", r"\pi_{\theta_{\mathrm{old}}}(a_t\mid s_t)}",
                       font_size=52).move_to(UP * 1.5 + LEFT * 1.5)
        n_lab = Text("new policy", font_size=24).next_to(rdef[2], RIGHT, buff=1.0)
        d_lab = Text("old policy (collected the data)", font_size=24, color=GREY_B).next_to(rdef[4], RIGHT, buff=0.7)
        n_arr = Arrow(n_lab.get_left(), rdef[2].get_right(), buff=0.1, stroke_width=3, max_tip_length_to_length_ratio=0.15)
        d_arr = Arrow(d_lab.get_left(), rdef[4].get_right(), buff=0.1, stroke_width=3, max_tip_length_to_length_ratio=0.15, color=GREY_B)
        self.play(ReplacementTransform(f[5], rdef[0]), FadeOut(VGroup(*rest, f[9])), run_time=1.0)
        self.play(Write(rdef[1]), run_time=0.4)
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
        cpi_lab = Text("conservative policy\niteration surrogate", font_size=24, color=GREY_B,
                       line_spacing=0.8).next_to(lcpi, RIGHT, buff=0.5)
        self.play(FadeIn(cpi_lab), run_time=0.8)

        self.cue(5)
        is_lab = Text("importance-sampled estimate of\nthe improvement of new over old", font_size=24, color=GREY_B,
                      line_spacing=0.8).next_to(lcpi, RIGHT, buff=0.5)
        self.play(FadeTransform(cpi_lab, is_lab), run_time=0.8)

        self.cue(6)
        grad = MathTex(r"\nabla_\theta L^{\mathrm{CPI}}\Big|_{\theta=\theta_{\mathrm{old}}}", r"=",
                       r"\hat{\mathbb{E}}_t\big[\nabla_\theta \log \pi_\theta(a_t\mid s_t)\,\hat{A}_t\big]",
                       font_size=40).next_to(lcpi, DOWN, buff=0.6).align_to(rdef, LEFT)
        pg = Text("= the standard policy gradient", font_size=24, color=GREY_B).next_to(grad, DOWN, buff=0.2).align_to(grad[2], LEFT)
        self.play(VGroup(rdef, n_lab, d_lab, n_arr, d_arr, eq1, is_lab).animate.set_opacity(0.3), Write(grad), run_time=2.0)
        self.play(FadeIn(pg), run_time=0.6)

        # switch to the 1-D picture: objective as a function of r
        self.cue(7)
        self.play(FadeOut(VGroup(rdef, n_lab, d_lab, n_arr, d_arr, eq1, is_lab, grad, pg)),
                  lcpi.animate.scale(0.8).to_corner(UR, buff=0.5).shift(DOWN * 0.6), run_time=1.0)
        ax = make_axes(-0.3, 2.6, x_len=8, y_len=4.8, xmax=2.4).move_to(DOWN * 0.6 + LEFT * 1.2)
        ticks = tick_labels(ax, [0.5, 1, 1.5, 2])
        rl = r_label(ax)
        fuzz = VGroup(*[rect(ax, 1 - w, 1 + w, -0.3, 2.6, WHITE, 0.05) for w in (0.1, 0.18, 0.26, 0.34)])
        rel = Text("estimate reliable", font_size=22).next_to(ax.c2p(1, 2.6), UP, buff=0.1)
        self.play(Create(ax), FadeIn(ticks), FadeIn(rl), FadeIn(y_label(ax, r"L^{\mathrm{CPI}}_t")), run_time=1.0)
        self.play(FadeIn(fuzz), FadeIn(rel), run_time=0.8)

        self.cue(8)
        line = poly(ax, unclip_pts(1, 2.4), C_UNCLIP)
        llab = MathTex(r"r_t\hat{A}_t\;\;(\hat{A}_t>0)", font_size=32, color=C_UNCLIP).next_to(ax.c2p(2.4, 2.4), RIGHT, buff=0.15)
        self.play(Create(line), FadeIn(llab), run_time=1.5)

        self.cue(9)
        rt = ValueTracker(1.0)
        dot = always_redraw(lambda: now_dot(ax.c2p(rt.get_value(), rt.get_value())))
        self.add(dot)
        up = Arrow(ax.c2p(1.6, 1.15), ax.c2p(2.25, 1.8), buff=0, color=WHITE, stroke_width=4)
        up_lab = Text("push r up", font_size=24).next_to(up, RIGHT, buff=0.1)
        self.play(rt.animate.set_value(2.35), GrowArrow(up), FadeIn(up_lab), run_time=3.0, rate_func=smooth)

        self.cue(10)
        stop = Text("nothing says stop", font_size=30, weight=BOLD).next_to(ax.c2p(2.35, 2.35), LEFT, buff=0.35).shift(UP * 0.3)
        self.play(FadeIn(stop, scale=1.1), FadeOut(rel), run_time=0.6)
        self.finish()


class Clip(Timed):
    def construct(self):
        h = heading("2.  Clip the ratio")
        rr = MathTex(r"r_t(\theta)", font_size=64, color=C_UNCLIP)
        self.cue(0)
        self.play(FadeIn(h), FadeIn(rr, scale=1.2), run_time=1.0)

        self.cue(1)
        cdef = MathTex(r"\mathrm{clip}(", r"r", r",\,1-\epsilon,\,1+\epsilon)", r"=",
                       r"\max\big(1-\epsilon,\ \min(r,\,1+\epsilon)\big)", font_size=40).next_to(h, DOWN, buff=0.4)
        cdef[0:3].set_color(C_CLIP)
        self.play(ReplacementTransform(rr, cdef[1]), FadeIn(cdef[0]), FadeIn(cdef[2]), run_time=1.0)
        self.play(Write(cdef[3:]), run_time=1.0)
        ax = make_axes(0, 2.0, x_len=7.5, y_len=4.2).move_to(DOWN * 1.1 + LEFT * 0.8)
        ticks = tick_labels(ax, [0.5, 1, 1.5, 2])
        rl = r_label(ax)
        ident = poly(ax, [(0, 0), (2, 2)], GREY_B, 2)
        cl = dashed(ax, clip_pts(1))
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
        flat_l = dashed(ax, [(0, 0.8), (0.8, 0.8)], width=10, n=9)
        flat_r = dashed(ax, [(1.2, 1.2), (2, 1.2)], width=10, n=9)
        self.play(Create(flat_l), Create(flat_r), run_time=1.0)

        self.cue(4)
        zl = zero_region(ax, 0, 0.8, 0, 2.0)
        zr = zero_region(ax, 1.2, 2.0, 0, 2.0)
        g0l = zero_tag(r"\nabla = 0").move_to(ax.c2p(0.4, 1.5))
        g0r = zero_tag(r"\nabla = 0").move_to(ax.c2p(1.6, 0.6))
        self.play(FadeIn(zl), FadeIn(zr), FadeIn(g0l), FadeIn(g0r), run_time=1.0)
        self.bring_to_front(ticks, ident, id_lab, cl, flat_l, flat_r, g0l, g0r)

        self.cue(5)
        rt = ValueTracker(1.0)
        dot = always_redraw(lambda: now_dot(ax.c2p(rt.get_value(), clipr(rt.get_value()))))
        read = always_redraw(lambda: MathTex(
            rf"r = {rt.get_value():.2f},\quad \mathrm{{clip}}(r) = {clipr(rt.get_value()):.2f}", font_size=30
        ).next_to(btxt, UP, buff=0.15))
        self.play(FadeIn(dot), FadeIn(read), run_time=0.5)
        self.play(rt.animate.set_value(1.85), run_time=3.5, rate_func=smooth)

        # keep the picture: shrink it aside while the full objective comes in
        self.cue(6)
        dot.clear_updaters()
        read.clear_updaters()
        small_text = VGroup(rl, id_lab, cl_lab, btxt, g0l, g0r, ticks, dot)   # unreadable once shrunk
        plot = VGroup(ax, ident, zl, zr, bd, cl, flat_l, flat_r)
        alone = Text("the clipped term alone", font_size=24, color=C_CLIP)
        self.play(FadeOut(cdef), FadeOut(read), FadeOut(etxt), FadeOut(small_text), run_time=0.5)
        self.play(plot.animate.scale(0.6).to_corner(DL, buff=0.5), run_time=0.8)
        alone.next_to(plot, RIGHT, buff=0.5).align_to(plot, DOWN).shift(UP * 0.4)
        self.play(FadeIn(alone), run_time=0.5)

        self.cue(7)
        f = lclip_formula().scale(0.95).move_to(UP * 1.2)
        self.play(Write(f), run_time=2.0)
        u = Text("unclipped", font_size=24, color=C_UNCLIP).next_to(VGroup(f[5], f[6]), DOWN, buff=0.35)
        c = Text("clipped", font_size=24, color=C_CLIP).next_to(VGroup(f[8], f[11]), DOWN, buff=0.35)
        bm = SurroundingRectangle(f[3], buff=0.08, color=C_MIN, stroke_width=6)
        self.play(FadeIn(u), FadeIn(c), Create(bm), run_time=1.0)
        self.finish()


def adv_setup(A):
    """Shared axes for the positive / negative advantage scenes (mirror images of each other)."""
    ylo, yhi = (-0.4, 2.2) if A > 0 else (-2.2, 0.4)
    ax = make_axes(ylo, yhi, x_len=8, y_len=5.0).move_to(DOWN * 0.45 + LEFT * 1.0)
    ticks = tick_labels(ax, [0.5, 0.8, 1.2, 1.5, 2], above=A < 0, size=24)
    rl = r_label(ax)
    bd = band(ax, ylo, yhi)
    return ax, ticks, rl, bd, ylo, yhi


class PositiveAdv(Timed):
    def construct(self):
        A = 1.0
        # open on the formula the previous scene ended with
        f = lclip_formula().scale(0.95).move_to(UP * 1.2)
        self.add(f)
        h = heading("3.  Positive advantage")
        sign = MathTex(r"\hat{A}_t > 0", font_size=40).to_corner(UR, buff=0.5)
        self.cue(0)
        self.play(FadeOut(f, shift=UP * 0.4), FadeIn(h), FadeIn(sign), run_time=1.0)
        ax, ticks, rl, bd, ylo, yhi = adv_setup(A)

        self.cue(1)
        goal = Text("better than expected: make it more likely", font_size=26).next_to(h, DOWN, buff=0.2)
        self.play(FadeIn(goal), Create(ax), FadeIn(ticks), FadeIn(rl), FadeIn(bd), FadeIn(y_label(ax)), run_time=1.5)

        self.cue(2)
        un = poly(ax, unclip_pts(A), C_UNCLIP)
        un_lab, cl_lab = term_labels(ax, A)
        self.play(Create(un), FadeIn(un_lab), run_time=1.5)

        self.cue(3)
        cl = dashed(ax, clip_pts(A))
        self.play(Create(cl), FadeIn(cl_lab), run_time=1.5)

        self.cue(4)
        fl = VGroup(dashed(ax, clip_pts(A)[:2], width=9, n=8), dashed(ax, clip_pts(A)[2:], width=9, n=8))
        self.play(Indicate(cl_lab, color=C_CLIP), Create(fl), run_time=1.0)

        self.cue(5)
        mn = poly(ax, min_pts(A), C_MIN, 9)
        mn_lab = MathTex(r"L^{\mathrm{CLIP}}_t = \min(\cdot,\cdot)", font_size=34, color=C_MIN).move_to(ax.c2p(0.42, 1.75))
        self.play(FadeOut(fl), un.animate.set_stroke(opacity=0.65), cl.animate.set_stroke(opacity=0.65), run_time=0.4)
        self.play(Create(mn), FadeIn(mn_lab), run_time=1.5)

        # region r > 1 + eps: clipped term is smaller
        self.cue(6)
        p_u = pt_un(ax.c2p(1.7, 1.7 * A))
        p_c = pt_cl(ax.c2p(1.7, 1.2 * A))
        arr = Arrow(p_u.get_center(), p_c.get_center(), buff=0.1, color=WHITE, stroke_width=4)
        arr_lab = Text("smaller", font_size=22).next_to(arr, RIGHT, buff=0.1)
        self.play(FadeIn(p_u), FadeIn(p_c), GrowArrow(arr), FadeIn(arr_lab), run_time=1.2)

        self.cue(7)
        zr = zero_region(ax, 1 + EPS, 2.0, ylo, yhi)
        g0 = zero_tag(r"\nabla_\theta L^{\mathrm{CLIP}}_t = 0").move_to(ax.c2p(1.6, 0.35))
        self.play(FadeIn(zr), FadeIn(g0), FadeOut(arr), FadeOut(arr_lab), run_time=1.0)
        self.bring_to_front(ticks, un, cl, mn, p_u, p_c, g0)

        self.cue(8)
        stop = Text("already > 20% more likely: stop pushing", font_size=24, color=C_ZERO_TXT).next_to(ax, DOWN, buff=0.25)
        self.play(FadeIn(stop), FadeOut(p_u), FadeOut(p_c), run_time=0.8)

        # region r < 1 - eps: unclipped term is smaller
        self.cue(9)
        q_u = pt_un(ax.c2p(0.45, 0.45 * A))
        q_c = pt_cl(ax.c2p(0.45, 0.8 * A))
        arr2 = Arrow(q_c.get_center(), q_u.get_center(), buff=0.1, color=WHITE, stroke_width=4)
        arr2_lab = Text("smaller", font_size=22).next_to(arr2, LEFT, buff=0.1)
        self.play(FadeOut(stop), FadeIn(q_u), FadeIn(q_c), GrowArrow(arr2), FadeIn(arr2_lab), run_time=1.2)

        self.cue(10)
        slope = MathTex(r"\text{slope} = \hat{A}_t > 0", font_size=30, color=C_MIN).move_to(ax.c2p(0.55, 1.15))
        self.play(FadeOut(arr2), FadeOut(arr2_lab), FadeOut(q_c), FadeIn(slope), run_time=0.8)

        self.cue(11)
        rt = ValueTracker(0.45)
        dot = always_redraw(lambda: now_dot(ax.c2p(rt.get_value(), rt.get_value() * A)))
        self.remove(q_u)
        self.add(dot)
        pull = Text("gradient pulls r back up", font_size=24, color=C_MIN).next_to(ax, DOWN, buff=0.25)
        self.play(FadeIn(pull), run_time=0.5)
        self.play(rt.animate.set_value(0.95), run_time=2.5, rate_func=smooth)
        self.finish()


class NegativeAdv(Timed):
    def construct(self):
        # open on the positive-advantage picture, dimmed; it flips when the narration says so
        axp, ticksp, rlp, bdp, _, _ = adv_setup(1.0)
        unp = poly(axp, unclip_pts(1.0), C_UNCLIP).set_stroke(opacity=0.35)
        clp = dashed(axp, clip_pts(1.0)).set_stroke(opacity=0.35)
        ylp = y_label(axp)
        signp = MathTex(r"\hat{A}_t > 0", font_size=40).to_corner(UR, buff=0.5).set_opacity(0.5)
        old = VGroup(axp, ticksp, rlp, bdp, ylp)
        self.add(old, unp, clp, signp)
        A = -1.0
        h = heading("4.  Negative advantage")
        sign = MathTex(r"\hat{A}_t < 0", font_size=40).to_corner(UR, buff=0.5)
        self.cue(0)
        self.play(FadeIn(h), run_time=1.0)
        ax, ticks, rl, bd, ylo, yhi = adv_setup(A)

        self.cue(1)
        goal = Text("worse than expected: make it less likely", font_size=26).next_to(h, DOWN, buff=0.2)
        self.play(FadeIn(goal), run_time=0.8)

        self.cue(2)
        un = poly(ax, unclip_pts(A), C_UNCLIP)
        cl = dashed(ax, clip_pts(A))
        un_lab, cl_lab = term_labels(ax, A)
        self.play(ReplacementTransform(axp, ax), ReplacementTransform(ticksp, ticks), ReplacementTransform(rlp, rl),
                  ReplacementTransform(signp, sign), ReplacementTransform(ylp, y_label(ax)),
                  ReplacementTransform(bdp, bd), ReplacementTransform(unp, un), ReplacementTransform(clp, cl), run_time=0.9)
        self.play(FadeIn(un_lab), FadeIn(cl_lab), run_time=0.3)

        self.cue(3)
        self.play(Indicate(un, color=C_UNCLIP, scale_factor=1.03), Indicate(un_lab, color=C_UNCLIP), run_time=1.2)

        # r < 1 - eps: clipped (flat) term is smaller
        self.cue(4)
        mn = poly(ax, min_pts(A), C_MIN, 9)
        mn_lab = MathTex(r"L^{\mathrm{CLIP}}_t = \min(\cdot,\cdot)", font_size=34, color=C_MIN).move_to(ax.c2p(0.42, -1.75))
        self.play(un.animate.set_stroke(opacity=0.65), cl.animate.set_stroke(opacity=0.65), run_time=0.4)
        self.play(Create(mn), FadeIn(mn_lab), run_time=1.0)
        p_u = pt_un(ax.c2p(0.45, 0.45 * A))
        p_c = pt_cl(ax.c2p(0.45, 0.8 * A))
        arr = Arrow(p_u.get_center(), p_c.get_center(), buff=0.1, color=WHITE, stroke_width=4)
        arr_lab = Text("smaller", font_size=22).next_to(arr, RIGHT, buff=0.1)
        self.play(FadeIn(p_u), FadeIn(p_c), GrowArrow(arr), FadeIn(arr_lab), run_time=1.2)

        self.cue(5)
        zl = zero_region(ax, 0, 1 - EPS, ylo, yhi)
        g0 = zero_tag(r"\nabla_\theta L^{\mathrm{CLIP}}_t = 0").move_to(ax.c2p(0.4, -1.2))
        self.play(FadeIn(zl), FadeIn(g0), FadeOut(arr), FadeOut(arr_lab), FadeOut(p_u), FadeOut(p_c),
                  mn_lab.animate.move_to(ax.c2p(1.3, -1.95)), run_time=1.0)
        self.bring_to_front(ticks, un, cl, mn, g0)

        self.cue(6)
        stop = Text("already > 20% less likely: stop pushing", font_size=24, color=C_ZERO_TXT).next_to(ax, DOWN, buff=0.25)
        self.play(FadeIn(stop), run_time=0.8)

        # r > 1 + eps: unclipped term is smaller -> unbounded penalty
        self.cue(7)
        q_u = pt_un(ax.c2p(1.7, 1.7 * A))
        q_c = pt_cl(ax.c2p(1.7, 1.2 * A))
        arr2 = Arrow(q_c.get_center(), q_u.get_center(), buff=0.1, color=WHITE, stroke_width=4)
        arr2_lab = Text("smaller", font_size=22).next_to(arr2, RIGHT, buff=0.1)
        self.play(FadeOut(stop), FadeIn(q_u), FadeIn(q_c), GrowArrow(arr2), FadeIn(arr2_lab), run_time=1.2)

        self.cue(8)
        unb = Text("keeps falling: no bound", font_size=24, color=C_MIN).next_to(ax, DOWN, buff=0.25)
        self.play(FadeOut(arr2), FadeOut(arr2_lab), FadeOut(q_c), FadeIn(unb),
                  Indicate(VGroup(mn), color=C_MIN, scale_factor=1.02), run_time=1.2)

        self.cue(9)
        rt = ValueTracker(1.7)
        dot = always_redraw(lambda: now_dot(ax.c2p(rt.get_value(), rt.get_value() * A)))
        self.remove(q_u)
        self.add(dot)
        push = Text("full penalty: gradient pushes r back down", font_size=24, color=C_MIN).next_to(ax, DOWN, buff=0.25)
        self.play(FadeOut(unb), run_time=0.3)
        self.play(FadeIn(push), run_time=0.5)
        self.play(rt.animate.set_value(1.1), run_time=4.2, rate_func=smooth)
        self.finish()


class Numbers(Timed):
    def construct(self):
        h = heading("5.  Worked example")
        self.cue(0)
        self.play(FadeIn(h), run_time=0.8)

        xs = [-5.9, -4.6, -3.3, -1.7, 0.7, 3.4, 5.6]
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
            ("+2", "0.6", "1.2", r"0.8\times 2 = 1.6", "1.2", "un", "up"),
            ("-2", "1.5", "-3.0", r"1.2\times(-2) = -2.4", "-3.0", "un", "down"),
            ("-2", "0.6", "-1.2", r"0.8\times(-2) = -1.6", "-1.6", "clip", "0"),
        ]
        # cue indices for each row: case, (A, r), values, min
        row_cues = [(2, 3, (4, 5), 6), (7, 8, (9, 9.5), 10), (11, 12, (13, 13.5), 14), (15, 16, (17, 17.5), 18)]

        def at(c):
            if isinstance(c, float):
                self.cue(int(c), 2.0)
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
            # the min: a box around both candidates closes onto the smaller one
            chosen = c_cl if which == "clip" else c_un
            both = SurroundingRectangle(VGroup(c_un, c_cl), color=C_MIN, buff=0.1, stroke_width=3)
            box = SurroundingRectangle(chosen, color=C_MIN, buff=0.1, stroke_width=3)
            m = cell(mn, 5, R, C_MIN)
            if g == "0":
                gc = MathTex(r"0", r"\ \text{(flat)}", font_size=34, color=C_ZERO_TXT).move_to([xs[6], ys[R], 0])
            else:
                arrow = r"\uparrow" if g == "up" else r"\downarrow"
                gc = MathTex(r"\text{flows: } r", arrow, font_size=34, color=C_MIN).move_to([xs[6], ys[R], 0])
            self.play(Create(both), run_time=0.4)
            self.play(ReplacementTransform(both, box), FadeIn(m), run_time=0.6)
            self.play(FadeIn(gc), run_time=0.5)
        self.finish()


class WhyMin(Timed):
    def construct(self):
        h = heading("6.  What the min does")
        self.cue(0)
        self.play(FadeIn(h), run_time=1.0)

        self.cue(1)
        lb = MathTex(r"L^{\mathrm{CLIP}}_t", r"=", r"\min\big(", r"r_t\hat{A}_t", r",\ ", r"\mathrm{clip}(r_t)\hat{A}_t",
                     r"\big)", r"\;\le\;", r"r_t\hat{A}_t", font_size=38).next_to(h, DOWN, buff=0.3)
        lb[3].set_color(C_UNCLIP)
        lb[5].set_color(C_CLIP)
        lb[8].set_color(C_UNCLIP)
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
        tL.next_to(axL, UP, buff=0.1).align_to(axL, RIGHT)   # sign top-right, room for a label top-left
        tR.next_to(axR, UP, buff=0.1).align_to(axR, LEFT)

        self.cue(2)
        self.play(FadeIn(VGroup(axL, bdL, unL, tL, tkL, axR, bdR, unR, tR, tkR)), run_time=0.8)
        self.play(Create(mnL), Create(mnR), run_time=1.2)
        zL = zero_region(axL, 1 + EPS, 2, yloL, yhiL, gap=0.16)
        zR = zero_region(axR, 0, 1 - EPS, yloR, yhiR, gap=0.16)
        iL = Text("gain ignored", font_size=20, color=C_ZERO_TXT).add_background_rectangle(opacity=0.9, buff=0.05).move_to(axL.c2p(1.6, 0.4))
        iR = Text("gain ignored", font_size=20, color=C_ZERO_TXT).add_background_rectangle(opacity=0.9, buff=0.05).move_to(axR.c2p(0.4, -1.6))
        self.play(FadeIn(zL), FadeIn(zR), FadeIn(iL), FadeIn(iR), run_time=0.8)
        self.bring_to_front(unL, unR, mnL, mnR, iL, iR, tkL, tkR)

        self.cue(3)
        wL = Text("worse: counted\nin full", font_size=20, color=C_MIN, line_spacing=0.8).move_to(axL.c2p(0.5, 1.45))
        wR = Text("worse: counted\nin full", font_size=20, color=C_MIN, line_spacing=0.8).move_to(axR.c2p(1.6, -0.5))
        self.play(FadeIn(wL), FadeIn(wR), run_time=0.8)

        # without the min: clipped term alone
        self.cue(4)
        no = Text("without the min: clipped term alone", font_size=26, color=C_CLIP).move_to(DOWN * 3.65)
        clL = dashed(axL, clip_pts(1.0), width=6, n=30)
        clR = dashed(axR, clip_pts(-1.0), width=6, n=30)
        self.play(FadeIn(no), FadeOut(mnL), FadeOut(mnR), Create(clL), Create(clR), FadeOut(wL), FadeOut(wR), run_time=1.5)

        # the regions where the policy moved the wrong way: also flat now -> outlined, labelled "wrong way"
        self.cue(5)

        def wrong(ax, x0, x1, ylo, yhi):
            z = zero_region(ax, x0, x1, ylo, yhi, gap=0.16, opacity=1.0, width=2.2)
            p, q = ax.c2p(x0, ylo), ax.c2p(x1, yhi)
            edge = DashedVMobject(Rectangle(width=q[0] - p[0], height=q[1] - p[1], color=WHITE, stroke_width=3)
                                  .move_to((p + q) / 2), num_dashes=36)
            return VGroup(z, edge)

        bL = wrong(axL, 0, 1 - EPS, yloL, yhiL)
        bR = wrong(axR, 1 + EPS, 2, yloR, yhiR)
        xL = Text("✗ wrong way: ∇ = 0", font_size=20, weight=BOLD).next_to(axL, UP, buff=0.12).align_to(axL, LEFT)
        xR = Text("✗ wrong way: ∇ = 0", font_size=20, weight=BOLD).next_to(axR, UP, buff=0.12).align_to(axR, RIGHT)
        self.play(zL.animate.set_opacity(0.25), zR.animate.set_opacity(0.25), iL.animate.set_opacity(0.3), iR.animate.set_opacity(0.3),
                  FadeIn(bL), FadeIn(bR), run_time=0.8)
        self.bring_to_front(unL, unR, clL, clR, tkL, tkR)
        self.play(FadeIn(xL), FadeIn(xR), run_time=0.6)

        self.cue(6)
        self.play(FadeOut(VGroup(axL, bdL, unL, clL, tL, tkL, zL, iL, bL, xL, axR, bdR, unR, clR, tR, tkR, zR, iR, bR, xR, no, lbt, lb)),
                  Transform(h, heading("6.  A caution")), run_time=0.8)

        # the caution, shown: one update step leaves the interval, and nothing pulls it back
        self.cue(7)
        c1 = Text("Clipping is not a hard trust region", font_size=34, weight=BOLD).move_to(UP * 1.9)
        nl = NumberLine(x_range=[0.6, 1.6, 0.2], length=9, include_tip=False,
                        numbers_to_include=[0.8, 1.0, 1.2, 1.4], decimal_number_config={"num_decimal_places": 1},
                        font_size=28).move_to(DOWN * 0.6)
        rlab = MathTex(r"r_t", font_size=32).next_to(nl, RIGHT, buff=0.25)
        bnd = Rectangle(width=nl.n2p(1.2)[0] - nl.n2p(0.8)[0], height=1.0, stroke_width=0, fill_color=C_BAND,
                        fill_opacity=0.25).move_to(nl.n2p(1.0))
        p0, p1 = nl.n2p(1.2) + DOWN * 0.5, nl.n2p(1.6) + UP * 0.5
        out = VGroup(hatch_rect(p0[0], p0[1], p1[0], p1[1], gap=0.18, opacity=0.5))
        sgn = MathTex(r"\hat{A}_t > 0", font_size=34).next_to(nl, LEFT, buff=0.5)
        self.play(FadeIn(c1), Create(nl), FadeIn(rlab), FadeIn(bnd), FadeIn(sgn), run_time=1.0)

        self.cue(8)
        dot = Dot(nl.n2p(1.15), radius=0.11, color=WHITE)
        self.play(FadeIn(dot), FadeIn(out), run_time=0.6)
        step = Arrow(nl.n2p(1.15) + UP * 0.35, nl.n2p(1.37) + UP * 0.35, buff=0, stroke_width=4, color=WHITE,
                     max_tip_length_to_length_ratio=0.25)
        slab = Text("one update step", font_size=22).next_to(step, UP, buff=0.15)
        self.play(GrowArrow(step), FadeIn(slab), dot.animate.move_to(nl.n2p(1.37)), run_time=2.2)
        tag = zero_tag(r"\hat{A}_t>0:\ \nabla = 0,\ \text{nothing pulls it back}", size=30).next_to(nl.n2p(1.3), DOWN, buff=0.75)
        self.play(FadeIn(tag), run_time=0.8)
        self.finish()


class Recap(Timed):
    def construct(self):
        h = heading("Recap")
        f = lclip_formula().scale(0.85).next_to(h, DOWN, buff=0.4)
        self.cue(0)
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
        self.play(FadeIn(i1, shift=RIGHT * 0.2), Indicate(VGroup(f[5], f[9])), run_time=0.8)
        self.cue(2)
        self.play(FadeIn(i2, shift=RIGHT * 0.2), Indicate(VGroup(f[8], f[10]), color=C_CLIP), run_time=0.8)
        self.cue(3)
        self.play(FadeIn(i3, shift=RIGHT * 0.2), Indicate(f[3], color=C_MIN, scale_factor=1.4), run_time=0.8)

        self.cue(3, 3.5)
        g = MathTex(
            r"\nabla_\theta L^{\mathrm{CLIP}}_t = \begin{cases} 0 & \hat{A}_t>0,\ r_t>1+\epsilon \ \text{ or }\ \hat{A}_t<0,\ r_t<1-\epsilon \\"
            r" \hat{A}_t\,\nabla_\theta r_t & \text{otherwise} \end{cases}",
            font_size=34,
        ).next_to(items, DOWN, buff=0.5)
        self.play(Write(g), run_time=2.0)
        self.finish(extra=1.4)
