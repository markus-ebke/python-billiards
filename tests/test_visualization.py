#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys

import pytest

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
