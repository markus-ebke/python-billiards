#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pytest

import billiards
from billiards import visualization


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


def test_animate():
    # custom Newton's cradle
    sim = billiards.Billiard()
    sim.add_ball((-3, 0), (1, 1 / 2), 1)
    sim.add_ball((0, 0), (0, 0), 1)
    sim.add_ball((3, 0), (0, 0), 1)
    sim.add_ball((5, 0), (0, 0), 1)
    sim.add_ball((7, 3), (0, -1 / 2), 0)

    anim = visualization.animate(sim, end_time=1, fps=60, show=False)


if __name__ == "__main__":
    pytest.main()
