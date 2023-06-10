#!/usr/bin/env python3
import warnings

import numpy as np
import pytest
from pytest import approx

import billiards

try:
    import matplotlib as mpl
    import matplotlib.pyplot as plt
except ImportError:
    has_mpl = False
else:
    has_mpl = True

with_mpl = pytest.mark.skipif(not has_mpl, reason="requires matplotlib")

try:
    import tqdm
except ImportError:
    has_tqdm = False
else:
    tqdm.trange  # try to access trange
    has_tqdm = True

try:
    from pyglet import gl
    from pyglet.window import Window
except ImportError:
    has_pyglet = False
except Exception:
    # with tox: pyglet.canvas.xlib.NoSuchDisplayException
    has_pyglet = False
    Window = object
else:
    has_pyglet = True
    gl.gl  # try to access some OpenGL subpackage
    Window.WINDOW_STYLE_DEFAULT  # try to access some Window class property

with_pyglet = pytest.mark.skipif(not has_pyglet, reason="requires pyglet")

with warnings.catch_warnings(record=True) as captured_warning:
    from billiards import visualize

if not has_mpl or not has_tqdm or not has_pyglet:
    if not captured_warning:
        pytest.fail(
            "Expected a warning because"
            f"mpl: {has_mpl}, tqdm: {has_tqdm}, pyglet: {has_pyglet}"
        )
elif captured_warning:
    pytest.fail(
        "Expected no warning because"
        f"mpl: {has_mpl}, tqdm: {has_tqdm}, pyglet: {has_pyglet}"
    )


@with_mpl
def test_collection():
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
    ]
    bld = billiards.Billiard(obstacles=obs)

    fig, ax = visualize.default_fig_and_ax()
    artists = visualize.plot_obstacles(bld, ax)
    assert len(artists) == len(bld.obstacles)


@with_mpl
def test_plot_balls(create_newtons_cradle):
    bld = create_newtons_cradle(5)

    fig, ax = visualize.default_fig_and_ax()
    ret = visualize.plot_balls(bld, ax)
    assert len(ret) == 2
    circles, points = ret
    assert isinstance(circles, visualize.CircleCollection)
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

    fig = visualize.plot(bld)
    assert isinstance(fig, mpl.figure.Figure)


@with_mpl
def test_animate(create_newtons_cradle):
    bld = create_newtons_cradle(5)

    anim = visualize.animate(bld, end_time=1, fps=60)
    assert bld.time == 1
    assert isinstance(anim, mpl.animation.FuncAnimation)
    assert anim._save_count == 61

    animated_artists = anim._func(1)
    assert len(animated_artists) == 4

    # clear frame to prevent this warning from matplotlib:
    # UserWarning: Animation was deleted without rendering anything.
    anim._init_draw()

    # from time = 1 to time = 2 at 30 fps => 31 frames (endpoints included)
    anim = visualize.animate(bld, end_time=2, fps=30)
    assert bld.time == 2
    assert anim._save_count == 31

    anim._init_draw()  # prevent warning from matplotlib


# when running the test with tox, pyglet will raise an exception:
# pyglet.canvas.xlib.NoSuchDisplayException: Cannot connect to "None"
"""
@with_pyglet
def test_model():
    # check disk
    d = billiards.obstacles.Disk((0, 0), 42)
    vertices, indices, mode = d.model()

    assert isinstance(vertices, np.ndarray)
    assert vertices.shape[1] == 2

    assert isinstance(indices, list)
    assert len(indices) == 2 * vertices.shape[0]

    assert isinstance(mode, int)
    assert mode == gl.GL_LINES

    # check infinite wall
    w = billiards.obstacles.InfiniteWall((0, 0), (0, 10))
    vertices, indices, mode = w.model()

    assert isinstance(vertices, np.ndarray)
    assert vertices.shape == (2, 2)

    assert isinstance(indices, list)
    assert len(indices) == 2

    assert isinstance(mode, int)
    assert mode == gl.GL_LINES
"""


if __name__ == "__main__":
    pytest.main()
