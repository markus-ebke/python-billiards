#!/usr/bin/env python3
from math import cos, pi, sin, sqrt

import numpy as np
import pytest
from numpy.testing import assert_allclose
from pytest import approx

from billiards.obstacles import Disk, InfiniteWall, LineSegment

INF = float("inf")


def test_disk():
    d = Disk((0, 0), 1)

    # check properties
    assert tuple(d.center) == (0, 0)
    assert d.radius == 1

    # check time of impact, velocity after collision and new time of impact
    pos, vel, r = (-10, 0), (1, 0), 1
    t, args = d.detect_collision(pos, vel, r)
    assert (t, args) == (8.0, ()), (pos, vel, r)
    upos = (pos[0] + t * vel[0], pos[1] + t * vel[1])
    uvel = d.resolve_collision(upos, vel, r)
    assert tuple(uvel) == (-1, 0)
    assert d.detect_collision(upos, uvel, 1) == (INF, ())

    pos, vel, r = (-10, 0), (1, 1 / 11), 1
    t_ref = -2 * sqrt(1 - 24 * vel[1] ** 2) / (vel[1] ** 2 + 1) + 10 / (vel[1] ** 2 + 1)
    t, args = d.detect_collision(pos, vel, r)
    assert (t, args) == (t_ref, ()), (pos, vel, r)
    upos = (pos[0] + t * vel[0], pos[1] + t * vel[1])
    uvel = d.resolve_collision(upos, vel, r)
    assert tuple(uvel) == approx((-0.663553336824114, 0.753632159610709), abs=1e-15)
    assert d.detect_collision(upos, uvel, 1) == (INF, ())


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
    assert w.detect_collision((0, 10), (0, -1), 1) == (9, (1.0,))
    assert w.detect_collision((-100, 10), (0, -1), 1) == (9, (1.0,))
    assert w.detect_collision((0, 10), (100, -1), 1) == (9, (1.0,))

    # check problematic cases
    assert w.detect_collision((0, -10), (0, 1), 1)[0] == INF  # coming from the outside
    assert w.detect_collision((0, 10), (0, -1), 10) == (
        0,
        (1.0,),
    )  # touching and colliding
    assert (
        w.detect_collision((0, 10), (0, 1), 10)[0] == INF
    )  # touching but no colliding
    assert (
        w.detect_collision((0, 10), (0, -1), 11)[0] == INF
    )  # overlap but no colliding
    assert w.detect_collision((0, 10), (0, 1), 11)[0] == INF

    # check point particles
    assert w.detect_collision((0, 1), (0, -1), 0) == (1, (1.0,))
    assert w.detect_collision((0, 0), (0, -1), 0) == (INF, ())  # too close
    assert w.detect_collision((0, 1e-8), (1, -1e-3), 0) == (1e-5, (1e-3,))
    assert w.detect_collision((0, 0), (0, 1), 0)[0] == INF

    # check collision
    assert tuple(w.resolve_collision((0, 10), (0, -1), 1, 1.0)) == (0, 1)
    assert tuple(w.resolve_collision((0, 10), (10, -1), 1, 1.0)) == (10, 1)

    assert w.detect_collision((0, -10), (10, 1), 1)[0] == INF  # wrong side
    with pytest.raises(AssertionError):
        w.resolve_collision((0, -10), (10, 1), 1, -np.dot((10, 1), w._normal))

    # use wall as ceiling
    w = InfiniteWall((-1, 0), (1, 0), no_go="right")
    assert w.detect_collision((0, -10), (10, 1), 1) == (9, (1.0,))
    assert tuple(w.resolve_collision((0, -10), (10, 1), 1, 1.0)) == (10, -1)


def test_line_segment():
    # test invalid construction
    with pytest.raises(ValueError):
        LineSegment((-1, 0), (-1, 0))  # not a line

    # check properties
    line = LineSegment((-1, 0), (1, 0))
    assert_allclose(line.start_point, (-1, 0))
    assert_allclose(line.end_point, (1, 0))
    assert_allclose(line._covector, (1 / 2, 0))
    assert_allclose(line._normal, (0, 1))

    # collision at left endpoint
    for a in [0, 1 / 6, 1 / 4, -1 / 2, pi / 2 - 1e-6]:
        pos = np.asarray([-cos(a) - 1, sin(a)])
        vel = np.asarray([cos(a), -sin(a)])
        assert line.detect_collision(pos, vel, 1 / 2) == (approx(0.5), (0,)), a

        cvel = line.resolve_collision(pos + 0.5 * vel, vel, 1 / 2, 0)
        assert_allclose(cvel, (-vel[0], -vel[1]), atol=1e-14)

    pos = np.asarray([-sqrt(1 / 2) - 2, sqrt(1 / 2) - 1])
    vel = np.asarray([1, 1])
    assert line.detect_collision(pos, vel, 1 + 1e-14) == (approx(1.0), (0,))

    pos = np.asarray([-sqrt(1 / 2), sqrt(1 / 2) + 1])
    vel = np.asarray([-1, -1])
    assert line.detect_collision(pos, vel, 1 + 1e-14) == (approx(1.0), (0,))

    pos = np.asarray([-2, 1 - 1e-14])
    vel = np.asarray([1, 0])
    assert line.detect_collision(pos, vel, 1) == (approx(1.0), (0,))

    cvel = line.resolve_collision(pos + 1.0 * vel, vel, 1, 0)
    assert_allclose(cvel, vel, atol=1e-14)

    # collision along the line
    for a in [pi / 2, pi / 2 + 1e-10, pi / 2 + 1e-6, 5 / 6 * pi - 1e-15]:
        pos = np.asarray([-cos(a) - 1, sin(a)])
        vel = np.asarray([cos(a), -sin(a)])
        t, (u,) = line.detect_collision(pos, vel, 1 / 2)
        t_ref = (pos[1] - 1 / 2) / (-vel[1])
        assert t == approx(t_ref), a
        assert u is not None and u > 0, a

        cvel = line.resolve_collision(pos + t * vel, vel, 1 / 2, u)
        assert_allclose(cvel, (vel[0], -vel[1]), atol=1e-14)

    # collision at right endpoint
    for a in [0, 1 / 6, 1 / 4, -1 / 2, pi / 2 - 1e-6]:
        pos = np.asarray([-cos(a + pi) + 1, sin(a + pi)])
        vel = np.asarray([cos(a + pi), -sin(a + pi)])
        assert line.detect_collision(pos, vel, 1 / 2) == (approx(0.5), (1,)), a

        cvel = line.resolve_collision(pos + 0.5 * vel, vel, 1 / 2, 1)
        assert_allclose(cvel, (-vel[0], -vel[1]), atol=1e-14)

    pos = np.asarray([1 + sqrt(1 / 2) + 1, sqrt(1 / 2) - 1])
    vel = np.asarray([-1, 1])
    assert line.detect_collision(pos, vel, 1 + 1e-14) == (approx(1.0), (1,))

    pos = np.asarray([1 + sqrt(1 / 2) - 1, sqrt(1 / 2) + 1])
    vel = np.asarray([1, -1])
    assert line.detect_collision(pos, vel, 1 + 1e-14) == (approx(1.0), (1,))

    pos = np.asarray([2, 1 - 1e-14])
    vel = np.asarray([-1, 0])
    assert line.detect_collision(pos, vel, 1) == (approx(1.0), (1,))

    # check time of impact, velocity after collision and new time of impact
    angle = 0.5
    line = LineSegment((0, 0), (cos(angle), sin(angle)))

    # particle starts from x axis and moves upwards
    for x in [2e-10, 1e-3, 0.1, cos(angle) - 1e-3, cos(angle) - 1e-10]:
        t_ref, u = sin(angle) / cos(angle) * x, x / cos(angle)
        t, args = line.detect_collision((x, 0), (0, 1), 0)
        assert (t, args[0]) == (approx(t_ref), approx(u)), (angle, x)

    # particle starts close to the line and moves upwards
    for dy in [0.1, 1e-3, 1.1e-10]:
        for x in [1e-10, 1e-3, 0.1, cos(angle) - 1e-3, cos(angle) - 1e-10]:
            y = sin(angle) / cos(angle) * x - dy
            t_ref, u = dy, x / cos(angle)
            t, args = line.detect_collision((x, y), (0, 1), 0)
            assert (t, args[0]) == (approx(t), approx(u)), (angle, x, y, dy)


if __name__ == "__main__":
    pytest.main()
