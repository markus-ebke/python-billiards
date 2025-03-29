#!/usr/bin/env python3
from math import cos, pi, sin, sqrt

import numpy as np
import pytest
from numpy.testing import assert_allclose
from pytest import approx

from billiards.obstacles import Circle, Disk, InfiniteWall, LineSegment
from billiards.physics import set_pos_accuracy

INF = float("inf")

# To compute the exact results: use sympy
# from sympy import *

# def toi(pos, vel, r, center, radius):
#     """Compute the time(s) at which the moving ball touches the circle."""
#     t = symbols("t")
#     dx = pos[0] + t * vel[0] - center[0]
#     dy = pos[1] + t * vel[1] - center[1]
#     return solveset(Eq(dx**2 + dy**2, (r + radius) ** 2), t)

# center, radius = (Rational("1.7"), Rational("2.3")), 1
# sol = toi((0, 0), (1, 1), 1 / sqrt(2), center, radius)
# print(min(sol))  # exact formula
# print(min(sol).evalf())  # numeric approximation


# For Circle.resolve_collision use:
# def vadd(v, w):
#     return (v[0] + w[0], v[1] + w[1])
#
# def vmul(scalar, vec):
#     return (scalar * vec[0], scalar * vec[1])
#
# def vdot(v, w):
#     return v[0] * w[0] + v[1] * w[1]
#
# def circle_resolve(collpos, vel, center):
#     dpos = vadd(collpos, vmul(-1, center))
#     return vadd(vel, vmul(-2 * vdot(dpos, vel) / vdot(dpos, dpos), dpos))
#
# collvel = circle_resolve(vadd(pos, mul(min(sol), vel)), vel, center)
# print(collvel)  # exact formulas
# print(collvel[0].evalf(), colvel[1].evalf())  # numeric approximation


def test_disk():
    d = Disk((0, 0), 1)

    # check properties
    assert tuple(d.center) == (0, 0)
    assert d.radius == 1
    assert d.no_go == "inside"

    # check invalid argument for no_go
    with pytest.raises(ValueError):
        Disk((0, 0), 1, no_go="outer")

    # check time of impact, velocity after collision and new time of impact
    pos, vel, r = (-10, 0), (1, 0), 1
    t, args = d.detect_collision(pos, vel, r)
    assert (t, args) == (8.0, ()), (pos, vel, r)

    upos = (pos[0] + t * vel[0], pos[1] + t * vel[1])
    assert upos[0] ** 2 + upos[1] ** 2 == approx((d.radius + r) ** 2), upos

    uvel = d.resolve_collision(upos, vel, r)
    assert tuple(uvel) == (-1, 0)
    assert d.detect_collision(upos, uvel, 1) == (INF, ())

    pos, vel, r = (-10, 0), (1, 1 / 11), 1
    t_ref = -2 * sqrt(1 - 24 * vel[1] ** 2) / (vel[1] ** 2 + 1) + 10 / (vel[1] ** 2 + 1)
    t, args = d.detect_collision(pos, vel, r)
    assert (t, args) == (t_ref, ()), (pos, vel, r)

    upos = (pos[0] + t * vel[0], pos[1] + t * vel[1])
    assert upos[0] ** 2 + upos[1] ** 2 == approx((d.radius + r) ** 2), upos

    uvel = d.resolve_collision(upos, vel, r)
    assert tuple(uvel) == approx((-0.663553336824114, 0.753632159610709), abs=1e-15)
    assert d.detect_collision(upos, uvel, 1) == (INF, ())


def test_disk_exterior():
    d = Disk((1.7, 2.3), 3, no_go="outside")

    # check properties
    assert tuple(d.center) == (1.7, 2.3)
    assert d.radius == 3
    assert d.no_go == "outside"

    # check time of impact, velocity after collision and new time of impact
    pos, vel, r = (0, 0), (1, 1), 1
    t, args = d.detect_collision(pos, vel, r)
    assert (t, args) == (approx(2 + sqrt(191) / 10), ()), (pos, vel, r)

    upos = (pos[0] + t * vel[0], pos[1] + t * vel[1])
    assert (upos[0] - 1.7) ** 2 + (upos[1] - 2.3) ** 2 == approx((3 - r) ** 2)

    uvel = d.resolve_collision(upos, vel, r)
    assert tuple(uvel) == approx((-0.91 - 0.03 * sqrt(191), -0.91 + 0.03 * sqrt(191)))
    assert d.detect_collision(upos, uvel, 1) == (approx(sqrt(191) / 5), ())

    # "slide" along the inner boundary
    pos, vel, r = (1.7, 2.3 - 3 + 2e-8), (1, 0), 1e-8
    for i in range(100):
        t, args = d.detect_collision(pos, vel, r)
        if i == 0:
            assert t == approx(sqrt(599999997) / 100000000)
        else:
            assert t == approx(2 * sqrt(599999997) / 100000000)

        upos = (pos[0] + t * vel[0], pos[1] + t * vel[1])
        assert (upos[0] - 1.7) ** 2 + (upos[1] - 2.3) ** 2 == approx((3 - r) ** 2)

        uvel = d.resolve_collision(upos, vel, r)
        assert uvel[0] ** 2 + uvel[1] ** 2 == approx(1.0), uvel

        pos, vel = upos, uvel


def test_circle():
    c = Circle((0, 0), 1)

    # check properties
    assert tuple(c.center) == (0, 0)
    assert c.radius == 1

    # check time of impact, velocity after collision and new time of impact
    pos, vel, r = (-10, 0), (1, 0), 1
    t, args = c.detect_collision(pos, vel, r)
    assert (t, args) == (8.0, ()), (pos, vel, r)

    collpos = (pos[0] + t * vel[0], pos[1] + t * vel[1])
    assert collpos[0] ** 2 + collpos[1] ** 2 == approx((c.radius + r) ** 2), collpos

    collvel = c.resolve_collision(collpos, vel, r)
    assert tuple(collvel) == (-1, 0)
    assert c.detect_collision(collpos, collvel, 1) == (INF, ())

    pos, vel, r = (-10, 0), (1, 1 / 11), 1
    t_ref = -2 * sqrt(1 - 24 * vel[1] ** 2) / (vel[1] ** 2 + 1) + 10 / (vel[1] ** 2 + 1)
    t, args = c.detect_collision(pos, vel, r)
    assert (t, args) == (t_ref, ()), (pos, vel, r)

    collpos = (pos[0] + t * vel[0], pos[1] + t * vel[1])
    assert collpos[0] ** 2 + collpos[1] ** 2 == approx((c.radius + r) ** 2), collpos

    collvel = c.resolve_collision(collpos, vel, r)
    assert tuple(collvel) == approx((-0.663553336824114, 0.753632159610709), abs=1e-15)
    assert c.detect_collision(collpos, collvel, 1) == (INF, ())

    c = Circle((1.7, 2.3), 3)

    # check properties
    assert tuple(c.center) == (1.7, 2.3)
    assert c.radius == 3

    # check time of impact, velocity after collision and new time of impact
    pos, vel, r = (0, 0), (1, 1), 1
    t, args = c.detect_collision(pos, vel, r)
    assert (t, args) == (approx(2 + sqrt(191) / 10), ()), (pos, vel, r)

    collpos = (pos[0] + t * vel[0], pos[1] + t * vel[1])
    assert (collpos[0] - 1.7) ** 2 + (collpos[1] - 2.3) ** 2 == approx((3 - r) ** 2)

    collvel = c.resolve_collision(collpos, vel, r)
    assert tuple(collvel) == approx(
        (-0.91 - 0.03 * sqrt(191), -0.91 + 0.03 * sqrt(191))
    )
    assert c.detect_collision(collpos, collvel, 1) == (approx(sqrt(191) / 5), ())

    # "slide" along the inner boundary
    pos, vel, r = (1.7, 2.3 - 3 + 2e-8), (1, 0), 1e-8
    for i in range(100):
        t, args = c.detect_collision(pos, vel, r)
        if i == 0:
            assert t == approx(sqrt(599999997) / 100000000)
        else:
            assert t == approx(2 * sqrt(599999997) / 100000000)

        collpos = (pos[0] + t * vel[0], pos[1] + t * vel[1])
        assert (collpos[0] - 1.7) ** 2 + (collpos[1] - 2.3) ** 2 == approx((3 - r) ** 2)

        collvel = c.resolve_collision(collpos, vel, r)
        assert collvel[0] ** 2 + collvel[1] ** 2 == approx(1.0), collvel

        pos, vel = collpos, collvel

    # check very small balls
    for rexp in range(2, 20):
        pos, vel, r = (-1, -1), (1 - 1e-8, 1 + 1e5), 2 ** (-rexp)
        t, args = c.detect_collision(pos, vel, r)
        assert t < 1, (rexp, pos, vel, r)

        collpos = (pos[0] + t * vel[0], pos[1] + t * vel[1])
        collvel = c.resolve_collision(collpos, vel, r)
        t, args = c.detect_collision(collpos, collvel, r)
        assert t == float("inf"), (rexp, collpos, collvel, r)

    # check point particle
    c = Circle((1, 0), 1)

    pos, vel = (-1e-3, 0), (2.5, 0)
    t, args = c.detect_collision(pos, vel, 0.0)
    assert t == approx(1e-3 / 2.5)

    collpos = (pos[0] + t * vel[0], pos[1] + t * vel[1])
    collvel = c.resolve_collision(collpos, vel, 0.0, args)
    assert tuple(collvel) == (-2.5, 0.0)

    assert c.detect_collision(collpos, collvel, 0.0)[0] == INF

    set_pos_accuracy(52 - 1)
    for dx in [1e-3, 1e-6, 1e-9, 1e-12, 2**-40, 2**-50, 2**-51]:
        for vx in [2.5, 1e-3, 1e-6, 1e-9, 1e-12, 1e-15]:
            pos, vel = ((1 - sqrt(1 / 2) - dx), sqrt(1 / 2)), (vx, 0)
            abserr = abs((pos[0] - 1 + sqrt(1 / 2)) / vx) * 8
            t, args = c.detect_collision(pos, vel, 0.0)
            assert t == approx(dx / vx, abs=abserr), (dx, vx)

            collpos = (pos[0] + t * vel[0], pos[1] + t * vel[1])
            collvel = c.resolve_collision(collpos, vel, 0.0, args)
            assert c.detect_collision(collpos, collvel, 0.0)[0] == INF, (dx, vx)


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

    # check time of impact from outside going in
    assert w.detect_collision((0, 10), (0, -1), 1) == (9, (-1.0,))
    assert w.detect_collision((-100, 10), (0, -1), 1) == (9, (-1.0,))
    assert w.detect_collision((0, 10), (100, -1), 1) == (9, (-1.0,))

    # check that time of impact for inside going out is infinite
    assert w.detect_collision((0, -10), (0, 1), 1)[0] == INF
    assert w.detect_collision((0, -10), (1, 0), 1)[0] == INF
    assert w.detect_collision((0, -10), (0, -1), 1)[0] == INF

    # check problematic cases
    assert w.detect_collision((0, 10), (0, -1), 10) == (
        0,
        (-1.0,),
    )  # touching and colliding
    assert (
        w.detect_collision((0, 10), (0, 1), 10)[0] == INF
    )  # touching but no colliding
    assert (
        w.detect_collision((0, 10), (0, -1), 11)[0] == INF
    )  # overlap but no colliding
    assert w.detect_collision((0, 10), (0, 1), 11)[0] == INF

    # check point particles
    assert w.detect_collision((0, 1), (0, -1), 0) == (1, (-1.0,))
    assert w.detect_collision((0, 0), (0, -1), 0) == (0.0, (-1.0,))
    assert w.detect_collision((0, 1e-8), (1, -1e-3), 0) == (1e-5, (-1e-3,))
    assert w.detect_collision((0, 0), (0, 1), 0)[0] == INF

    # check collision
    assert tuple(w.resolve_collision((0, 10), (0, -1), 1, -1.0)) == (0, 1)
    assert tuple(w.resolve_collision((0, 10), (10, -1), 1, -1.0)) == (10, 1)

    assert w.detect_collision((0, -10), (10, 1), 1)[0] == INF  # wrong side
    with pytest.raises(AssertionError):
        w.resolve_collision((0, -10), (10, 1), 1, w._normal.dot((10, 1)))

    # use wall as ceiling
    w = InfiniteWall((-1, 0), (1, 0), no_go="left")
    assert w.detect_collision((0, -10), (10, 1), 1) == (9, (-1.0,))
    assert tuple(w.resolve_collision((0, -10), (10, 1), 1, -1.0)) == (10, -1)

    # test repeated collision for decreasing distances
    w = InfiniteWall((-1, 0), (1, 0), no_go="right")
    for dy in [10 ** (-e) for e in range(15)] + [0.0]:
        for vy in [10 ** (-e) for e in range(-2, 15)]:
            for r in [10 ** (-e) for e in range(15)] + [0.0]:
                pos, vel = (0, r + dy), (0, -vy)
                t, args = w.detect_collision(pos, vel, r)
                relerr = max(1e-6, 1e-16 * (r + dy) / max(1e-16, dy))
                assert t == approx(dy / vy, rel=relerr), (dy, vy, r, pos, vel)

                collpos = (pos[0] + t * vel[0], pos[1] + t * vel[1])
                collvel = w.resolve_collision(collpos, vel, r, *args)
                assert tuple(collvel) == (0, vy), (dy, vy, r, collpos, vel)

                assert w.detect_collision(collpos, collvel, r)[0] == INF


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
