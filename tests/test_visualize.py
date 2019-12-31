#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import pytest
from pytest import approx

import billiards
from billiards import visualize

try:
    import matplotlib as mpl
    import matplotlib.pyplot as plt
except ImportError:
    has_mpl = False
else:
    has_mpl = True

with_mpl = pytest.mark.skipif(not has_mpl, reason="requires matplotlib")

"""
try:
    from pyglet import gl
except ImportError:
    has_pyglet = False
else:
    has_pyglet = True

with_pyglet = pytest.mark.skipif(not has_pyglet, reason="requires pyglet")
"""


@with_mpl
def test_collection():
    pos = np.asarray([[0.0, 0.0], [4.0, 1.0], [10.0, 8.0]])
    radii = [1.0, 4.0, 0.0]

    box_min = [-1.0, -3.0]
    box_max = [10.0, 8.0]

    fig = plt.figure(figsize=(8, 6), dpi=100)
    fig.set_tight_layout(True)
    ax = fig.add_subplot(1, 1, 1, aspect="equal", adjustable="datalim")

    # test BallCollection
    balls = visualize.BallCollection(pos, radii, transOffset=ax.transData)
    ball_bbox = balls.get_datalim(ax.transData).get_points()
    assert ball_bbox[0] == approx(box_min)
    assert ball_bbox[1] == approx(box_max)

    # test BallPatchCollection
    balls_patches = visualize.BallPatchCollection(pos, radii)
    ax.add_collection(balls_patches)
    patches_bbox = balls_patches.get_datalim(ax.transData).get_points()
    assert patches_bbox[0] == approx(box_min)
    assert patches_bbox[1] == approx(box_max)


@with_mpl
def test_plot_frame(create_newtons_cradle):
    bld = create_newtons_cradle(5)

    ret = visualize._plot_frame(bld, None, None)
    fig, ax, balls, scatter, quiver, time_text = ret
    assert isinstance(fig, mpl.figure.Figure)


@with_mpl
def test_plot(create_newtons_cradle):
    bld = create_newtons_cradle(5)

    fig = visualize.plot(bld, show=False)
    assert isinstance(fig, mpl.figure.Figure)


@with_mpl
def test_plot_obstacles():
    obs = [
        billiards.obstacles.Disk((0, 0), 10),
        billiards.obstacles.InfiniteWall((-1, -20), (1, -20)),
    ]
    bld = billiards.Billiard(obstacles=obs)

    fig = visualize.plot(bld, show=False)
    assert isinstance(fig, mpl.figure.Figure)


@with_mpl
def test_animate(create_newtons_cradle):
    bld = create_newtons_cradle(5)

    fig, anim = visualize.animate(bld, end_time=1, fps=60, show=False)
    assert isinstance(fig, mpl.figure.Figure)
    assert isinstance(anim, mpl.animation.FuncAnimation)

    animated_artists = anim._func(1)
    assert len(animated_artists) == 4


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
