#!/usr/bin/env python3
import numpy as np
import pytest
from pytest import approx

import billiards

try:
    import matplotlib as mpl
    import matplotlib.pyplot as plt
except ImportError:
    has_mpl = has_mpl_with_alpha = False
else:
    has_mpl = True
    has_mpl_with_alpha = mpl.__version_info__ >= (3, 8)

    # close all figures after running each test, matplotlib will generate a warning
    # if there are more than 20 figures open
    @pytest.fixture(autouse=True)
    def auto_close_all_figures():
        yield
        plt.close("all")


with_mpl = pytest.mark.skipif(not has_mpl, reason="requires matplotlib")

if not has_mpl:
    with pytest.raises(ImportError) as exc_info:
        import billiards.visualize_matplotlib as visualize
    assert exc_info.value.args[0] == "No module named 'matplotlib'"
else:
    import billiards.visualize_matplotlib as visualize


@with_mpl
def test_circle_collection():
    pos = np.asarray([[0.0, 0.0], [4.0, 1.0], [10.0, 8.0]])
    radii = [1.0, 4.0, 0.0]

    box_min = [-1.0, -3.0]
    box_max = [10.0, 8.0]

    fig = plt.figure(figsize=(8, 6), dpi=100)
    fig.set_layout_engine("tight")
    ax = fig.add_subplot(1, 1, 1, aspect="equal", adjustable="datalim")

    # test datalimit (used by ax.autoscale)
    balls = visualize.CircleCollection(pos, radii, transOffset=ax.transData)
    ball_bbox = balls.get_datalim(ax.transData).get_points()
    print(ball_bbox)
    assert ball_bbox[0] == approx(box_min, rel=1e-3, abs=1e-3)
    assert ball_bbox[1] == approx(box_max, rel=1e-3, abs=1e-3)


@with_mpl
def test_default_fig_and_ax():
    fig, ax = visualize.default_fig_and_ax()
    assert isinstance(fig, mpl.figure.Figure)
    assert isinstance(ax, mpl.axes.Axes)


@with_mpl
def test_plot_obstacles():
    obs = [
        billiards.obstacles.Disk((0, 0), 10),
        billiards.obstacles.InfiniteWall((-1, -20), (1, -20)),
        billiards.obstacles.LineSegment((-1, -20), (1, -20)),
    ]
    bld = billiards.Billiard(obstacles=obs)

    fig, ax = visualize.default_fig_and_ax()
    visualize.plot_obstacles(bld, ax)
    assert len(ax.lines) == 2
    assert len(ax.patches) == 2
    assert len(ax._children) == 4


@with_mpl
def test_plot_balls(create_newtons_cradle):
    bld = create_newtons_cradle(5)
    bld.add_ball((0, 0), (0, 0), radius=0)

    fig, ax = visualize.default_fig_and_ax()
    circles = visualize.plot_balls(bld, ax)
    assert isinstance(circles, visualize.CircleCollection)

    points = visualize.plot_particles(bld, ax)
    assert isinstance(points, mpl.collections.PathCollection)


@with_mpl
def test_plot_velocities(create_newtons_cradle):
    bld = create_newtons_cradle(5)

    fig, ax = visualize.default_fig_and_ax()
    arrows = visualize.plot_velocities(bld, ax)
    assert isinstance(arrows, mpl.quiver.Quiver)


@with_mpl
def test_plot(create_newtons_cradle):
    bld = create_newtons_cradle(5)

    fig, ax = visualize.plot(bld)
    assert isinstance(fig, mpl.figure.Figure)
    assert isinstance(ax, mpl.axes.Axes)


@with_mpl
def test_animate(create_newtons_cradle):
    bld = create_newtons_cradle(5)

    anim, fig, ax = visualize.animate(bld, end_time=1, dt=1 / 60, fps=30)
    assert bld.time == 1
    assert isinstance(anim, mpl.animation.FuncAnimation)
    assert isinstance(fig, mpl.figure.Figure)
    assert isinstance(ax, mpl.axes.Axes)
    assert anim._save_count == 61  # determined by bld.time, end_time and dt, not fps

    animated_artists = anim._func(1)
    assert len(animated_artists) == 3  # text, circles, quiver

    # clear frame to prevent this warning from matplotlib:
    # UserWarning: Animation was deleted without rendering anything.
    anim._init_draw()

    # from time = 1 to time = 2 in steps of 1/30 => 31 frames (endpoints included)
    anim, fig, ax = visualize.animate(bld, end_time=2, dt=1 / 30)
    assert bld.time == 2
    assert anim._save_count == 31

    anim._init_draw()  # prevent warning from matplotlib


@with_mpl
def test_color_scheme():
    bld = billiards.Billiard()
    bld.add_ball((0, 0), (0, 0), radius=4.2)
    bld.add_ball((5, 0), (0, 0), radius=0)

    with pytest.raises(TypeError):
        visualize.plot(bld, color_scheme=("balls", "red"))

    # TODO check axes children: were the colors correctly applied?
    visualize.plot(bld, color_scheme={"balls": "red"})
    visualize.plot(bld, color_scheme={"balls": ("red", None)})
    visualize.plot(bld, color_scheme={"balls": (None, "blue")})
    visualize.plot(bld, color_scheme={"balls": ("red", "blue")})

    visualize.plot(bld, color_scheme={0: "red", 1: "orange"})
    visualize.plot(bld, color_scheme={0: ("red", None), 1: (None, "yellow")})
    visualize.plot(bld, color_scheme={0: (None, "blue"), 1: ("orange", None)})
    visualize.plot(bld, color_scheme={0: ("red", "blue"), 1: ("orange", "yellow")})

    anim, fig, ax = visualize.animate(
        bld, 1, color_scheme={0: ("red", "blue"), 1: ("orange", "yellow")}
    )
    anim._init_draw()


@pytest.mark.skipif(not has_mpl_with_alpha, reason="requires matplotlib>=3.8")
def test_color_scheme_with_alpha():
    bld = billiards.Billiard()
    bld.add_ball((0, 0), (0, 0), radius=4.2)
    bld.add_ball((5, 0), (0, 0), radius=0)

    # TODO check axes children: were the colors correctly applied?
    visualize.plot(bld, color_scheme={"balls": ("red", 0.5)})
    visualize.plot(bld, color_scheme={"balls": ("red", ("blue", 0.3))})
    visualize.plot(bld, color_scheme={"balls": (("red", 0.6), ("blue", 0.3))})

    visualize.plot(bld, color_scheme={0: ("red", 0.5)})
    visualize.plot(bld, color_scheme={0: ("red", ("blue", 0.3))})
    visualize.plot(bld, color_scheme={0: (("red", 0.6), ("blue", 0.3))})

    anim, fig, ax = visualize.animate(
        bld, 1, color_scheme={0: (("red", 0.6), ("blue", 0.3))}
    )
    anim._init_draw()


if __name__ == "__main__":
    pytest.main()
