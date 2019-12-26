#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys

import numpy as np
import pytest
from pytest import approx

import billiards
from billiards import visualization

try:
    import matplotlib as mpl
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

    fig = mpl.pyplot.figure(figsize=(8, 6), dpi=100)
    fig.set_tight_layout(True)
    ax = fig.add_subplot(1, 1, 1, aspect="equal", adjustable="datalim")

    # test BallCollection
    balls = visualization.BallCollection(
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
    balls_patches = visualization.BallPatchCollection(
        centers=pos, radii=radii, edgecolor="black", linewidth=1, zorder=0,
    )
    ax.add_collection(balls_patches)
    patches_bbox = balls_patches.get_datalim(ax.transData).get_points()
    assert patches_bbox[0] == approx(box_min)
    assert patches_bbox[1] == approx(box_max)


@hasmpl
def test_plot():
    # custom Newton's cradle
    sim = billiards.Billiard()
    sim.add_ball((-3, 0), (1, 1 / 2), 1)
    sim.add_ball((0, 0), (0, 0), 1)
    sim.add_ball((3, 0), (0, 0), 1)
    sim.add_ball((5, 0), (0, 0), 1)
    sim.add_ball((7, 3), (0, -1 / 2), 0)

    sim.evolve(4)

    fig = visualization.plot(sim, show=False)
    assert isinstance(fig, mpl.figure.Figure)


@hasmpl
def test_animate():
    # custom Newton's cradle
    sim = billiards.Billiard()
    sim.add_ball((-3, 0), (1, 1 / 2), 1)
    sim.add_ball((0, 0), (0, 0), 1)
    sim.add_ball((3, 0), (0, 0), 1)
    sim.add_ball((5, 0), (0, 0), 1)
    sim.add_ball((7, 3), (0, -1 / 2), 0)

    anim = visualization.animate(sim, end_time=1, fps=60, show=False)
    assert isinstance(anim, mpl.animation.FuncAnimation)

    drawn_artists = anim._func(1)
    assert len(drawn_artists) == 4


if __name__ == "__main__":
    pytest.main()
