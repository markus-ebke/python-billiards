#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import pytest
from pytest import approx

from billiards.obstacles import Disk, InfiniteWall, circle_model

INF = float("inf")


def test_circle_model():
    r, n = 5.0, 16
    vertices, indices = circle_model(r, num_points=n)

    assert isinstance(vertices, np.ndarray)
    assert vertices.shape == (n, 2)
    assert np.hypot(vertices[:, 0], vertices[:, 1]) == approx(r)

    assert len(indices) == 2 * n


def test_disk():
    d = Disk((0, 0), 1)

    # check properties
    assert tuple(d.center) == (0, 0)
    assert d.radius == 1

    # time of impact and collision (same as for balls)
    assert d.calc_toi((-10, 0), (1, 0), 1) == 8.0
    assert tuple(d.collide((-2, 0), (1, 0), 1)) == (-1, 0)


def test_infinite_wall():
    # test invalid construction
    with pytest.raises(ValueError):
        InfiniteWall((-1, 0), (-1, 0))  # not a line

    with pytest.raises(ValueError):
        InfiniteWall((-1, 0), (1, 0), "Left")  # side must be lowercase

    # use wall as ground floor
    w = InfiniteWall((-1, 0), (1, 0))

    # check properties
    assert tuple(w.start_point) == (-1.0, 0.0)
    assert tuple(w.end_point) == (1.0, 0.0)
    assert tuple(w._normal) == (0.0, 1.0)

    # check time of impact from inside
    assert w.calc_toi((0, 10), (0, -1), 1) == 9
    assert w.calc_toi((-100, 10), (0, -1), 1) == 9
    assert w.calc_toi((0, 10), (100, -1), 1) == 9

    # check problematic cases
    assert w.calc_toi((0, -10), (0, 1), 1) == INF  # coming from the outside
    assert w.calc_toi((0, 10), (0, -1), 10) == 0  # touching and colliding
    assert w.calc_toi((0, 10), (0, 1), 10) == INF  # touching but no colliding
    assert w.calc_toi((0, 10), (0, -1), 11) == INF  # overlap but no colliding
    assert w.calc_toi((0, 10), (0, 1), 11) == INF

    # check point particles
    assert w.calc_toi((0, 1), (0, -1), 0) == 1
    assert w.calc_toi((0, 0), (0, -1), 0) == 0
    assert w.calc_toi((0, 0), (0, 1), 0) == INF

    # check collision
    assert tuple(w.collide((0, 10), (0, -1), 1)) == (0, 1)
    assert tuple(w.collide((0, 10), (10, -1), 1)) == (10, 1)
    with pytest.raises(AssertionError):
        w.collide((0, -10), (10, 1), 1)

    # use wall as ceiling
    w = InfiniteWall((-1, 0), (1, 0), inside="right")
    w.calc_toi((0, -10), (10, 1), 1) == 9
    assert tuple(w.collide((0, -10), (10, 1), 1)) == (10, -1)


if __name__ == "__main__":
    pytest.main()
