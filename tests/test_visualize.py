#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys

import numpy as np
import pytest
from pytest import approx

import billiards
from billiards import visualize

try:
    import matplotlib as mpl
    import matplotlib.pyplot as plt
except ImportError:
    pass


hasmpl = pytest.mark.skipif(
    "matplotlib" not in sys.modules, reason="requires the Matplotlib library"
)


@hasmpl
def test_collection():
    pos = np.asarray([[0.0, 0.0], [4.0, 1.0], [10.0, 8.0]])
    radii = [1.0, 4.0, 0.0]

    box_min = [-1.0, -3.0]
    box_max = [10.0, 8.0]

    fig = plt.figure(figsize=(8, 6), dpi=100)
    fig.set_tight_layout(True)
    ax = fig.add_subplot(1, 1, 1, aspect="equal", adjustable="datalim")

    # test BallCollection
    balls = visualize.BallCollection(
        centers=pos,
        radii=radii,
        transOffset=ax.transData,
        edgecolor="black",
        linewidth=1,
        zorder=0,
    )
    ball_bbox = balls.get_datalim(ax.transData).get_points()
    assert ball_bbox[0] == approx(box_min)
    assert ball_bbox[1] == approx(box_max)

    # test BallPatchCollection
    balls_patches = visualize.BallPatchCollection(
        centers=pos, radii=radii, edgecolor="black", linewidth=1, zorder=0,
    )
    ax.add_collection(balls_patches)
    patches_bbox = balls_patches.get_datalim(ax.transData).get_points()
    assert patches_bbox[0] == approx(box_min)
    assert patches_bbox[1] == approx(box_max)


@pytest.fixture
def newtons_cradle(num_balls=5):
    bld = billiards.Billiard()

    bld.add_ball((-2, 0), (1, 0), 1)
    for i in range(1, num_balls):
        bld.add_ball((2 * i, 0), (0, 0), radius=1)

    return bld


@hasmpl
def test_plot_frame(newtons_cradle):
    bld = newtons_cradle

    ret = visualize._plot_frame(bld, None, None)
    fig, ax, balls, scatter, quiver, time_text = ret
    assert isinstance(fig, mpl.figure.Figure)


@hasmpl
def test_plot(newtons_cradle):
    bld = newtons_cradle

    fig = visualize.plot(bld, show=False)
    assert isinstance(fig, mpl.figure.Figure)


@hasmpl
def test_animate(newtons_cradle):
    bld = newtons_cradle

    fig, anim = visualize.animate(bld, end_time=1, fps=60, show=False)
    assert isinstance(fig, mpl.figure.Figure)
    assert isinstance(anim, mpl.animation.FuncAnimation)

    drawn_artists = anim._func(1)
    assert len(drawn_artists) == 4


def test_circle_model():
    n = 16
    vertices, indices = visualize._circle_model(5, num_points=n)
    assert isinstance(vertices, np.ndarray)
    assert vertices.shape == (n, 2)
    assert np.hypot(vertices[:, 0], vertices[:, 1]) == approx(5)

    assert len(indices) == 2 * n


if __name__ == "__main__":
    pytest.main()
