from math import asin, cos, pi, sin, sqrt, ulp

import numpy as np
import pytest
from pytest import approx

from billiards.physics import (
    elastic_collision,
    toi_and_param_ball_segment,
    toi_ball_ball,
    toi_ball_circle,
    toi_ball_disk_exterior,
    toi_ball_point,
)

INF = float("inf")
np.seterr(divide="raise")  # use pytest.raises to catch numpy errors


def test_toi_ball_ball():
    assert toi_ball_ball((0, 0), (0, 0), 1, (5, 0), (-1, 0), 1) == 3

    # check that only relative coordinates are important
    assert toi_ball_ball((0, 42), (42, 0), 1, (5, 42), (41, 0), 1) == 3

    # for convenience
    def toi(pos, vel, radius, ulps=1):
        return toi_ball_ball(pos, vel, radius, (0, 0), (0, 0), 1, ulps)

    # check zero velocity
    assert toi((3, 0), (0, 0), 1) == INF  # outside
    assert toi((2, 0), (0, 0), 1) == INF  # touching
    assert toi((1, 0), (0, 0), 1) == INF  # overlap

    # check one inside the other
    assert toi((0.5, 0), (-42, 0), 0.1) == INF
    assert toi((1, 0), (-42, 0), 1) == INF
    assert toi((1, 0), (-42, 0), 10) == INF

    # check miss
    assert toi((2, 0), (1, 0), 1) == INF
    assert toi((2, 0), (0, 1), 1) == INF
    assert toi((sqrt(2) + 0.5, sqrt(2) - 0.5 + 1e-10), (-1, 1), 1) == INF

    # check sliding past each other
    assert toi((2, 0), (0, 1), 1) == INF
    assert toi((2, 10), (0, -1), 1) == INF
    assert toi((sqrt(2) - 0.5, sqrt(2) + 0.5 + 1e-10), (1, -1), 1) == INF

    # check collision
    assert toi((3, 0), (-1, 0), 1) == 1.0  # head-on collision
    assert toi((3, 0), (-1, 1e-10), 1) == 1.0  # slightly skewed collision
    assert toi((0, 101), (0, -33), 1) == approx(3.0)
    assert toi((1, 2), (0, -1), sqrt(2) - 1) == approx(1.0)  # sideways collision
    assert toi((sqrt(2) - 0.5, sqrt(2) + 0.5 - 1e-10), (1, -1), 1) == approx(
        0.49998810787885, abs=2e-11
    )

    # throw balls from (10, 0) and see which ones collide
    px, r = 10, 2
    for a in np.linspace(-pi / 2, pi / 2):
        vx, vy = -cos(a), sin(a)
        if abs(vy) < (r + 1) / px:  # the critical angle is asin((r1 + r2) / px)
            t = -px * vx - sqrt((r + 1) ** 2 - px**2 * vy**2)
        else:
            t = INF
        assert toi((px, 0), (vx, vy), r) == approx(t, abs=1e-12), a

    # throw balls slightly above the critical angle (no collision)
    for a in [asin((r + 1) / px) + da for da in [1e-5, 1e-10, 1e-11, 1e-13, 1e-15]]:
        vx, vy = -cos(a), sin(a)
        assert abs(vy) >= (r + 1) / px, a
        assert toi((px, 0), (vx, vy), r) == INF, a

    # throw balls slightly below the critical angle (collision)
    for a in [asin((r + 1) / px) - da for da in [1e-5, 1e-10, 1e-11, 1e-13, 1e-15]]:
        vx, vy = -cos(a), sin(a)
        assert abs(vy) < (r + 1) / px, a
        t = -px * vx - sqrt((r + 1) ** 2 - px**2 * vy**2)
        assert toi((px, 0), (vx, vy), r) == approx(t, abs=4e-8), a

    # pos_dot_vel and sqrt(delta_over_4) close => cancellation of significant digits
    assert toi((sqrt(2) + 1e-4, sqrt(2)), (-1e-4, 0), 1) == approx(1.0, abs=1e-11)
    assert toi((sqrt(2) + 1e-6, sqrt(2)), (-1e-6, 0), 1) == approx(1.0, abs=1e-10)
    assert toi((sqrt(2) + 1e-8, sqrt(2)), (-1e-8, 0), 1) == approx(1.0, abs=1e-7)
    assert toi((sqrt(2) + 1e-10, sqrt(2)), (-1e-10, 0), 1) == approx(1.0, abs=1e-5)
    assert toi((sqrt(2) + 1e-12, sqrt(2)), (-1e-12, 0), 1) == approx(1.0, abs=1e-3)
    assert toi((sqrt(2) + 1e-14, sqrt(2)), (-1e-14, 0), 1) == approx(1.0, abs=5e-3)

    # pos_dot_vel + sqrt(delta_over_4) == 0, also cancellation => t1 = 0 * ...
    r = 10
    xy = (r + 1) / sqrt(2)
    assert toi((xy + 1e-15, xy), (-1e-8, 0), r) == 0.0

    # check touching
    assert toi((2, 0), (-1, 0), 1) == 0
    assert toi((1 + 1e-12, 1), (0, -1), sqrt(2) - 1) == approx(1e-12, abs=1e-15)

    # check point particle
    assert toi((2, 0), (-1, 0), 0) == 1.0  # head-on
    assert toi((2, 0), (-1, 1e-15), 0) == approx(1.0, abs=1e-12)  # slightly skewed
    assert toi((1, 0), (0, 1), 0) == INF  # slide
    # cos(60°) == 1/2 => pythagoras: sin(60°) == sqrt(1 - 1/2**2) == sqrt(3/4)
    assert toi((0.5, 1), (0, -1), 0) == approx(1 - sqrt(3 / 4))  # side


def test_toi_ball_ball_ulps():
    # parameters for the first ball
    pos1 = np.asarray((sqrt(1 / 2), sqrt(1 / 2)))
    vel1 = np.asarray((0, 0))
    radius1 = 1.0

    # for convenience
    def toi(pos2, vel2, radius2, ulps=1):
        return toi_ball_ball(pos1, vel1, radius1, pos2, vel2, radius2, ulps)

    # touching
    pos2 = pos1 + (sqrt(2), sqrt(2))
    assert toi(pos2, (-(2**-30), 0), 1, ulps=1) == approx(0.0, abs=3 * 2 ** (-52 + 30))

    # overlap
    pos2 = pos1 + (sqrt(2), sqrt(2))
    pos2[0] -= 2**10 * ulp(pos2[0])
    assert toi(pos2, (-(2**-30), 0), 1, ulps=1) == INF
    assert toi(pos2, (-(2**-30), 0), 1, ulps=9) == INF
    assert toi(pos2, (-(2**-30), 0), 1, ulps=10) == approx(0.0, abs=2 * 2 ** (-42 + 30))

    # gap
    pos2 = pos1 + (sqrt(2), sqrt(2))
    pos2[0] += 2**10 * ulp(pos2[0])
    assert toi(pos2, (-(2**-30), 0), 1, ulps=1) == approx(0.0, abs=3 * 2 ** (-42 + 30))

    # check point particle
    pos2 = pos1 + (radius1, 0)
    assert toi(pos2 + (1, 0), (-1, 0), 0) == approx(1.0, abs=1e-15)  # head-on
    assert toi(pos2, (-1, 0), 0) == approx(0.0, abs=1e-15)  # head-on and touching
    assert toi(pos2 + (1, 0), (-1, 1e-15), 0) == approx(1.0, abs=1e-15)  # skewed
    assert toi(pos2, (-1, 1e-15), 0) == approx(0.0, abs=1e-15)  # skewed and touching
    assert toi(pos2, (-1e-15, 1), 0) == approx(0.0, abs=2e-8)  # slide into ball
    assert toi(pos2, (0, 1), 0) == INF  # slide along ball
    # cos(60°) == 1/2 => pythagoras: sin(60°) == sqrt(1 - 1/2**2) == sqrt(3/4)
    assert toi(pos1 + (0.5, 1), (0, -1), 0) == approx(1 - sqrt(3 / 4))  # side


def test_toi_particle_particle():
    # for convenience
    def toi(pos, vel, ulps=1):
        return toi_ball_ball(pos, vel, 0, (0, 0), (0, 0), 0, ulps)

    # point particles do not collide with each other
    for eps in [1e-5, 1e-10, 1e-15, 0.0]:  # mess up floating point calculations
        for a in range(10):
            x, y = cos(a), sin(a)
            vx, vy = -x, -y * (1 + eps)  # fly towards origin, arrive at time t = 1
            assert toi((x, y), (vx, vy)) == INF, (eps, a)


def test_toi_ball_point():
    assert toi_ball_point((0, 0), (1, 0), 1, (5, 0)) == 4

    # check that only relative coordinates are important
    assert toi_ball_point((0, 42), (1, 0), 1, (5, 42)) == 4

    # for convenience
    def toi(pos, vel, radius, ulps=1):
        return toi_ball_point(pos, vel, radius, (0, 0), ulps)

    # check zero velocity
    assert toi((2, 0), (0, 0), 1) == INF  # outside
    assert toi((1, 0), (0, 0), 1) == INF  # touching
    assert toi((0.5, 0), (0, 0), 1) == INF  # overlap

    # check point inside ball
    assert toi((1 - 1e-12, 0), (-42, 0), 1) == INF

    # check miss
    assert toi((2, 0), (1, 0), 1) == INF
    assert toi((2, 0), (0, 1), 1) == INF
    assert toi((sqrt(1 / 2) + 0.5, sqrt(1 / 2) - 0.5 + 1e-10), (-1, 1), 1) == INF

    # check sliding past the point
    assert toi((1, 0), (0, 1), 1) == INF
    assert toi((1, 10), (0, -1), 1) == INF
    assert toi((sqrt(1 / 2), sqrt(1 / 2)), (1 + 1e-10, -1), 1) == INF

    # check collision
    assert toi((2, 0), (-1, 0), 1) == 1.0  # head-on collision
    assert toi((2, 0), (-1, 1e-10), 1) == 1.0  # slightly skewed collision
    assert toi((0, 100), (0, -33), 1) == approx(3.0)
    assert toi((1, 2), (0, -1), sqrt(2)) == approx(1.0)  # sideways collision
    assert toi((sqrt(1 / 2) - 0.5, sqrt(1 / 2) + 0.5 - 1e-10), (1, -1), 1) == approx(
        0.499991590985848, abs=3e-12
    )

    # cos(60°) == 1/2 => pythagoras: sin(60°) == sqrt(1 - 1/2**2) == sqrt(3/4)
    assert toi((0.5, 1), (0, -1), 1) == approx(1 - sqrt(3 / 4))

    # throw balls from (10, 0) and see which ones collide
    px, r = 10, 2
    for a in np.linspace(-pi / 2, pi / 2):
        vx, vy = -cos(a), sin(a)
        if abs(vy) < (r + 0) / px:  # the critical angle is asin((r1 + r2) / px)
            t = -px * vx - sqrt((r + 0) ** 2 - px**2 * vy**2)
        else:
            t = INF
        assert toi((px, 0), (vx, vy), r) == approx(t, abs=1e-8), a

    # throw balls slightly above the critical angle (no collision)
    for a in [asin((r + 0) / px) + da for da in [1e-5, 1e-10, 1e-11, 1e-13, 1e-15]]:
        vx, vy = -cos(a), sin(a)
        assert abs(vy) >= (r + 0) / px, a
        assert toi((px, 0), (vx, vy), r) == INF, a

    # throw balls slightly below the critical angle (collision)
    for a in [asin((r + 0) / px) - da for da in [1e-5, 1e-10, 1e-11, 1e-13, 1e-15]]:
        vx, vy = -cos(a), sin(a)
        assert abs(vy) < (r + 1) / px, a
        t = -px * vx - sqrt((r + 0) ** 2 - px**2 * vy**2)
        assert toi((px, 0), (vx, vy), r) == approx(t, abs=1e-7), a

    # check touching
    assert toi((1, 0), (-1, 0), 1) == 0
    assert toi((1 + 1e-12, 1), (0, -1), sqrt(2)) == approx(0.0)


def test_toi_ball_point_ulps():
    # parameters for the point
    point = np.asarray((sqrt(1 / 2), sqrt(1 / 2)))

    # for convenience
    def toi(pos, vel, radius, ulps=1):
        return toi_ball_point(pos, vel, radius, point, ulps)

    # touching
    pos = point + (sqrt(2), sqrt(2))
    assert toi(pos, (-(2**-30), 0), 2, ulps=1) == approx(0.0, abs=3 * 2 ** (-52 + 30))

    # overlap
    pos = point + (sqrt(2), sqrt(2))
    pos[0] -= 2**10 * ulp(pos[0])
    assert toi(pos, (-(2**-30), 0), 2, ulps=1) == INF
    assert toi(pos, (-(2**-30), 0), 2, ulps=9) == INF
    assert toi(pos, (-(2**-30), 0), 2, ulps=10) == approx(0.0, abs=2 * 2 ** (-42 + 30))

    # gap
    pos = point + (sqrt(2), sqrt(2))
    pos[0] += 2**10 * ulp(pos[0])
    assert toi(pos, (-(2**-30), 0), 2, ulps=1) == approx(0.0, abs=3 * 2 ** (-42 + 30))

    # touching, change the ball radius
    pos = point + (sqrt(1 / 2), sqrt(1 / 2))
    assert toi(pos, (-(2**-30), 0), 1 + 2**-30) == INF
    assert toi(pos, (-(2**-30), 0), 1 + 2**-30, ulps=53 - 31) == INF
    assert toi(pos, (-(2**-30), 0), 1 + 2**-30, ulps=53 - 30) == approx(0.0, abs=2**2)
    assert toi(pos, (-(2**-30), 0), 1, ulps=1) == approx(0.0, abs=2 ** (-52 + 30))

    # check point particle (never collide)
    assert toi(point + (1, 0), (-1, 0), 0) == INF
    assert toi(point + (1, 1e-15), (-1, 0), 0) == INF
    assert toi(point + (1, 0), (-1, 1e-15), 0) == INF


def test_toi_ball_disk_exterior():
    assert toi_ball_disk_exterior((1, 0), (1, 0), 1, (0, 0), 5) == 3

    # check that only relative coordinates are important
    assert toi_ball_disk_exterior((1, 42), (1, 0), 1, (0, 42), 5) == 3

    # for convenience
    def toi(pos, vel, radius, ulps=1):
        return toi_ball_disk_exterior(pos, vel, radius, (0, 0), 5, ulps)

    # check zero velocity
    assert toi((1, 0), (0, 0), 1) == INF  # inside
    assert toi((4, 0), (0, 0), 1) == INF  # touching
    assert toi((4.5, 0), (0, 0), 1) == INF  # overlap

    # check ball too large
    assert toi((1, 2), (0, -1), 5) == INF

    # check miss (outside and moving away)
    assert toi((6, 0), (1, 0), 1) == INF
    assert toi((6, 0), (0, 1), 1) == INF

    # always a bit overlapping with the outside
    for eps in [1e-3, 1e-8, 1e-10, 1e-15]:
        x = 4 / sqrt(2) * (1 + eps)
        assert toi((x + 10, x - 10), (-1, 1), 1) == INF

    # check head-on impact
    assert toi((3, 0), (-1, 0), 1) == 7.0
    assert toi((0, 95), (0, -33), 1) == approx(3.0)

    # check sliding along the boundary
    assert toi((4, 0), (0, 1), 1) == INF
    assert toi((4, 10), (0, -1), 1) == INF
    assert toi((sqrt(8) - 1e-12, sqrt(8)), (1, -1), 1) < 0.1
    assert toi((1, 2), (0, -1), 4) == INF
    assert toi((4 - 2**-50, 0), (0, 1), 1) < 0.1
    assert toi((4, 0), (0, 1), 1 - 2**-50) < 0.1

    # check collision
    assert toi((1, 2), (0, -1), 1) == approx(2 + sqrt((5 - 1) ** 2 - 1))
    assert toi((1, 2), (0, -1), 2) == approx(2 + sqrt((5 - 2) ** 2 - 1))
    assert toi((1, 2), (0, -1), 3) == approx(2 + sqrt((5 - 3) ** 2 - 1))

    # ball just a bit smaller than disk
    for eps in [1e-3, 1e-5, 1e-10, 1e-12]:
        for v in [0.01, 1.0, 1.0000001, 1000.01]:
            assert toi((0, 0), (0, -v), 5 - eps) == approx(eps / v, abs=1e-13)

    # throw balls
    px, r = 2, 2
    for a in np.linspace(-pi / 2, pi / 2):
        vx, vy = cos(a), sin(a)
        t = -px * vx + sqrt((5 - r) ** 2 - px**2 * vy**2)
        assert toi((px, 0), (vx, vy), r) == approx(t, abs=1e-12), a

    # check touching
    assert toi((4, 0), (1, 0), 1) == 0
    assert toi((sqrt(8), sqrt(8)), (1 - 1e-7, -1), 1) == approx(0.0, abs=3e-7)
    assert toi((sqrt(8) - 1e-12, sqrt(8)), (0, 1), 1) == approx(0.0)

    # check next collision when we start at the boundary
    vx = vy = -sqrt(1 / 2)
    for eps in [1e-3, 1e-6, 1e-9, 1e-12, 1e-13, 1e-14, 1e-15, 1e-16, 0.0]:
        t = -(4 * sqrt(2) - eps + sqrt(32 - eps**2)) / (2 * vx)
        assert toi((sqrt(8) - eps, sqrt(8)), (vx, vy), 1) == approx(t, abs=1e-14), eps

    # check small speed
    vx, vy = -1e-14, 1e-8
    assert toi((4, 0), (vx, vy), radius=1) == approx(-8 * vx / (vx**2 + vy**2))


def test_toi_ball_disk_exterior_ulps():
    # parameters for the disk
    disk_center = np.asarray((sqrt(1 / 2), sqrt(1 / 2)))
    disk_radius = 5

    # for convenience
    def toi(pos, vel, radius, ulps=1):
        return toi_ball_disk_exterior(pos, vel, radius, disk_center, disk_radius, ulps)

    # touching
    pos = disk_center + (4 * sqrt(1 / 2), 4 * sqrt(1 / 2))
    assert toi(pos, (2**-30, 0), 1, ulps=1) == approx(0.0, abs=3 * 2 ** (-52 + 30))

    # overlap
    pos = disk_center + (4 * sqrt(1 / 2), 4 * sqrt(1 / 2))
    pos[0] += 2**10 * ulp(pos[0])
    assert toi(pos, (2**-30, 0), 1, ulps=1) == INF
    assert toi(pos, (2**-30, 0), 1, ulps=9) == INF
    # because of rounding errors, toi(..., ulp=10) is infinite
    assert toi(pos, (2**-30, 0), 1, ulps=11) == approx(0.0, abs=3 * 2 ** (-42 + 30))

    # gap
    pos = disk_center + (4 * sqrt(1 / 2), 4 * sqrt(1 / 2))
    pos[0] -= 2**10 * ulp(pos[0])
    assert toi(pos, (2**-30, 0), 1, ulps=1) == approx(0.0, abs=2 * 2 ** (-42 + 30))

    # touching, change the ball radius
    pos, radius = disk_center + (sqrt(8), sqrt(8)), 1 + 2**-30
    assert toi(pos, (2**-29, 0), radius) == INF
    assert toi(pos, (2**-29, 0), radius, ulps=53 - 32) == INF
    assert toi(pos, (2**-29, 0), radius, ulps=53 - 31) == approx(0.0, abs=2**0)
    assert toi(pos, (2**-29, 0), radius=1, ulps=1) == approx(0.0, abs=2 ** -(52 - 31))

    # check point particle
    assert toi(disk_center + (2, 0), (-1, 0), 0) == 7  # head-on
    assert toi(disk_center + (5, 0), (0, 1), 0) == INF  # slide
    assert toi(disk_center + (1, 2), (0, -1), 0) == approx(2 + sqrt((5 - 0) ** 2 - 1))

    for eps in [1e-3, 1e-5, 1e-8, 1e-11, 1e-14, 1e-15]:
        pos, vel = disk_center + (5 - eps, 0), (0, 1)
        t = sqrt(-eps * (eps - 10))
        assert toi(pos, vel, 0) == approx(t, abs=2e-8), eps  # slide inside


def test_toi_ball_circle():
    assert toi_ball_circle((1, 0), (1, 0), 1, (0, 0), 5) == 3

    # check that only relative coordinates are important
    assert toi_ball_circle((1, 42), (1, 0), 1, (0, 42), 5) == 3

    # for convenience
    def toi(pos, vel, radius, t_eps=-0.0):
        return toi_ball_circle(pos, vel, radius, (0, 0), 5, t_eps)

    # check zero velocity
    assert toi((1, 0), (0, 0), 1) == INF  # inside
    assert toi((4, 0), (0, 0), 1) == INF  # touching
    assert toi((4.5, 0), (0, 0), 1) == INF  # overlap

    # check ball too large
    assert toi((1, 2), (0, -1), 5) == INF

    # check miss (outside and moving away)
    assert toi((6, 0), (1, 0), 1) == INF
    assert toi((6, 0), (0, 1), 1) == INF

    # check head-on impact
    assert toi((3, 0), (-1, 0), 1) == 7.0
    assert toi((0, 6 + 99), (0, -33), 1) == approx(3.0)

    # check sliding along the boundary
    assert toi((4, 0), (0, 1), 1) == INF
    assert toi((4 - 2**-50, 0), (0, 1), 1) < 0.1
    assert toi((4, 0), (0, 1), 1 - 2**-50) < 0.1

    # check collision
    assert toi((1, 2), (0, -1), 1) == approx(2 + sqrt((5 - 1) ** 2 - 1))
    assert toi((1, 2), (0, -1), 2) == approx(2 + sqrt((5 - 2) ** 2 - 1))
    assert toi((1, 2), (0, -1), 3) == approx(2 + sqrt((5 - 3) ** 2 - 1))

    # ball just a bit smaller than disk
    for eps in [1e-3, 1e-5, 1e-10, 1e-12]:
        for v in [0.01, 1.0, 1.0000001, 1000.01]:
            assert toi((0, 0), (0, -v), 5 - eps) == approx(eps / v, abs=1e-13)

    # throw balls
    px, r = 2, 2
    for a in np.linspace(-pi / 2, pi / 2):
        vx, vy = cos(a), sin(a)
        t = -px * vx + sqrt((5 - r) ** 2 - px**2 * vy**2)
        assert toi((px, 0), (vx, vy), r) == approx(t, abs=1e-12), a

    # check touching
    assert toi((4, 0), (1, 0), 1) == INF
    assert toi((sqrt(2.5), sqrt(2.5)), (-1, 0), 1) == approx(sqrt(2.5) + sqrt(13.5))
    assert toi((sqrt(8), sqrt(8)), (1 - 1e-7, -1), 1) == approx(0.0, abs=3e-7)
    assert toi((sqrt(8) - 1e-12, sqrt(8)), (0, 1), 1) == approx(0.0)

    # check next collision when we start at the boundary
    vx = vy = -sqrt(1 / 2)
    for eps in [1e-3, 1e-6, 1e-9, 1e-12, 1e-13, 1e-14, 1e-15, 1e-16, 0.0]:
        t = -(4 * sqrt(2) - eps + sqrt(32 - eps**2)) / (2 * vx)
        assert toi((sqrt(8) - eps, sqrt(8)), (vx, vy), 1) == approx(t, abs=1e-14), eps

    # check small speed
    vx, vy = -1e-14, 1e-8
    assert toi((4, 0), (vx, vy), radius=1) == approx(-8 * vx / (vx**2 + vy**2))

    # test touching balls and t_eps
    diag = (sqrt(8), sqrt(8))
    assert toi(diag, (1, 0), radius=1 + 1e-5) == INF

    # using t_eps to detect collision
    x, y = 4 * cos(5 / 13), 4 * sin(5 / 13)
    assert (x**2 + y**2) > (5 - 1) ** 2  # rounding error => not zero
    assert toi((x, y), (1, 0), 1) == INF  # fails to detect collision

    # check point particle
    assert toi((2, 0), (-1, 0), 0) == 7  # head-on
    assert toi((5, 0), (0, 1), 0) == INF  # slide
    assert toi((1, 2), (0, -1), 0) == approx(2 + sqrt((5 - 0) ** 2 - 1))

    for eps in [1e-3, 1e-5, 1e-8, 1e-11, 1e-14, 1e-15]:
        t = sqrt(-eps * (eps - 10))
        assert toi((5 - eps, 0), (0, 1), 0) == approx(t, abs=2e-8), eps  # slide inside


def test_toi_ball_segment():
    start, end = np.asarray([0, 0]), np.asarray([1, 0])
    direction = end - start
    length_sqrd = direction.dot(direction)
    covector = direction / length_sqrd
    normal = np.asarray([-direction[1], direction[0]]) / sqrt(length_sqrd)

    line = (start, covector, normal)
    assert toi_and_param_ball_segment((1 / 2, 2), (0, -1), 1, *line) == (1, 1 / 2)

    # check that only relative coordinates are important
    line = (start + (42, 0), covector, normal)
    assert toi_and_param_ball_segment((1 / 2 + 42, 2), (0, -1), 1, *line) == (1, 1 / 2)

    # check that scale doesn't matter
    line = (10 * start, covector / 10, normal)
    assert toi_and_param_ball_segment((5, 20), (0, -10), 10, *line) == (1, 1 / 2)

    # for convenience
    def toi(pos, vel, radius, t_eps=-0.0):
        return toi_and_param_ball_segment(
            pos, vel, radius, start, covector, normal, t_eps
        )

    # no collision from left endpoint
    for a in [0, 1 / 6, 1 / 4, -1 / 2, pi / 2 - 1e-6, pi / 2]:
        pos, vel = (-cos(a), sin(a)), (cos(a), -sin(a))
        # assert toi(pos, vel, 1 / 2) == (approx(0.5), 0), a  # with endpoints
        assert toi(pos, vel, 1 / 2) == (INF, 0), a

    pos, vel = (-sqrt(1 / 2) - 1, sqrt(1 / 2) - 1), (1, 1)
    # assert toi(pos, vel, 1 + 1e-14) == (approx(1.0), 0)  # with endpoints
    assert toi(pos, vel, 1 + 1e-14) == (INF, 0)

    pos, vel = (-sqrt(1 / 2) + 1, sqrt(1 / 2) + 1), (-1, -1)
    # assert toi(pos, vel, 1 + 1e-14) == (approx(1.0), 0)  # with endpoints
    assert toi(pos, vel, 1 + 1e-14) == (INF, 0)

    # assert toi((-1, 1 - 1e-14), (1, 0), 1) == (approx(1.0), 0)  # with endpoints
    assert toi((-1, 1 - 1e-14), (1, 0), 1) == (INF, 0)

    # collision along the line
    for a in [pi / 2 + 1e-6, 5 / 6 * pi - 1e-15]:
        pos, vel = (-cos(a), sin(a)), (cos(a), -sin(a))
        t, u = toi(pos, vel, 1 / 2)
        t_ref = (pos[1] - 1 / 2) / (-vel[1])
        assert t == approx(t_ref), a
        assert u is not None and 0 < u < 1, a

        ball_pos = np.asarray(pos) + t * np.asarray(vel)
        line_pos = start + u * direction
        assert np.linalg.norm(ball_pos - line_pos) == approx(1 / 2), a

    # no collision at right endpoint
    for a in [0, 1 / 6, 1 / 4, -1 / 2, pi / 2 - 1e-6, pi / 2]:
        pos, vel = (-cos(a + pi) + 1, sin(a + pi)), (cos(a + pi), -sin(a + pi))
        # assert toi(pos, vel, 1 / 2) == (approx(0.5), 1), a  # with endpoints
        assert toi(pos, vel, 1 / 2) == (INF, 1), a

    pos, vel = (1 + sqrt(1 / 2) + 1, sqrt(1 / 2) - 1), (-1, 1)
    # assert toi(pos, vel, 1 + 1e-14) == (approx(1.0), 1)  # with endpoints
    assert toi(pos, vel, 1 + 1e-14) == (INF, 1)

    pos, vel = (1 + sqrt(1 / 2) - 1, sqrt(1 / 2) + 1), (1, -1)
    # assert toi(pos, vel, 1 + 1e-14) == (approx(1.0), 1)  # with endpoints
    assert toi(pos, vel, 1 + 1e-14) == (INF, 1)

    # assert toi((2, 1 - 1e-14), (-1, 0), 1) == (approx(1.0), 1)  # with endpoints
    assert toi((2, 1 - 1e-14), (-1, 0), 1) == (INF, 1)

    # collision along the line before collision with endpoint
    assert toi((1, 1), (-1, -1), 1 / 2) == (approx(0.5), approx(1 / 2))
    assert toi((1, 1), (-1, -1), 1 / 2) == (approx(0.5), approx(1 / 2))

    # miss
    assert toi((-1, 0), (0, 1), 1) == (INF, 0)
    assert toi((-1, -1), (0, 1), 1) == (INF, 0)
    assert toi((-sqrt(1 / 2) - 1, sqrt(1 / 2) - 1), (1, 1), 1 - 1e-10) == (INF, 0)
    assert toi((0.1, 1), (1, 0), 1) == (INF, None)  # slide
    assert toi((-1, 1 + 1e-14), (1, 0), 1) == (INF, None)  # move parallel too far away

    # overlap is a miss
    assert toi((-1, 0), (0, 1), 1.1) == (INF, 0)
    assert toi((-0.1, 0), (0, 1), 1) == (INF, 0)
    assert toi((0.1, 0), (0, 1), 1) == (INF, None)
    assert toi((0.1, -0.5), (0, 1), 1) == (INF, None)
    assert toi((0.1, 0), (0, 1), 10) == (INF, None)
    assert toi((1 / 2, 0), (-1, 0), 1 / 4) == (INF, None)
    assert toi((1 / 2, 1 / 3), (-1, -1), 1 / 2) == (INF, None)
    assert toi((1, 1 / 3), (-1, -1), 1 / 2) == (INF, None)
    assert toi((1.1, 1 / 3), (-1, -1), 1 / 2) == (INF, 1)

    # test almost touching
    # assert toi((-1.1 - 1e-12, 0), (0, 1), 1.1) == (1e-12, 0)  # with endpoints
    assert toi((-1.1 - 1e-12, 0), (0, 1), 1.1) == (INF, 0)
    # assert toi((-1e-10, -1), (0, 1), 1) == (1 - sqrt(-(1e-10 - 1) * (1e-10 + 1)), 0)
    assert toi((-1e-10, -1), (0, 1), 1) == (INF, 0)
    assert toi((0.3, -1 - 1e-10), (0, 1), 1) == (approx(1e-10, abs=1e-16), 0.3)

    # toi was in the past
    assert toi((2, 2), (1, 1), 1) == (INF, None)

    # toi was in the past, use t_eps
    pos, vel, radius = (0.1, 1), (0, -1), 1 + 1e-5
    assert toi(pos, vel, radius) == (INF, None)
    assert toi(pos, vel, radius, t_eps=-1e-4) == (approx(-1e-5, abs=1e-14), 0.1)


def test_toi_particle_segment():
    angle = 0.5

    start, end = np.asarray([0, 0]), np.asarray([cos(angle), sin(angle)])
    direction = end - start
    length_sqrd = direction.dot(direction)
    covector = direction / length_sqrd
    normal = np.asarray([-direction[1], direction[0]]) / sqrt(length_sqrd)

    # for convenience
    def toi(pos, vel, t_eps=-0.0):
        return toi_and_param_ball_segment(pos, vel, 0, start, covector, normal, t_eps)

    # particle starts from x axis and moves upwards
    for x in [1e-10, 1e-3, 0.1, cos(angle) - 1e-3, cos(angle) - 1e-10]:
        t, u = sin(angle) / cos(angle) * x, x / cos(angle)
        assert toi((x, 0), (0, 1)) == (approx(t), approx(u)), (angle, x)

    # particle starts close to the line and moves upwards
    for dy in [0.1, 1e-3, 1e-10]:
        for x in [1e-10, 1e-3, 0.1, cos(angle) - 1e-3, cos(angle) - 1e-10]:
            y = sin(angle) / cos(angle) * x - dy
            t, u = dy, x / cos(angle)
            assert toi((x, y), (0, 1)) == (approx(t), approx(u)), (angle, x, y, dy)


def test_elastic_collision():
    pos1, pos2 = (0, 0), (2, 0)

    def ec(vel1, vel2, mass2=1):
        v1, v2 = elastic_collision(pos1, vel1, 1, pos2, vel2, mass2)
        return (tuple(v1), tuple(v2))

    # head-on collision
    assert ec((0, 0), (-1, 0)) == ((-1, 0), (0, 0))
    assert ec((1, 0), (-1, 0)) == ((-1, 0), (1, 0))
    assert ec((1, 0), (0, 0)) == ((0, 0), (1, 0))

    # sideways collsion
    assert ec((0, 0), (-1, 1)) == ((-1, 0), (0, 1))
    assert ec((0, 0), (-0.5, 1)) == ((-0.5, 0), (0, 1))
    assert ec((0, 0), (-42, 1 / 42)) == ((-42, 0), (0, 1 / 42))

    # zero mass collision
    assert ec((-1, 0), (-20, 0), mass2=0) == ((-1, 0), (18, 0))

    # sliding past each other is possible
    assert ec((0, 0), (0, 1)) == ((0, 0), (0, 1))

    # When the balls are moving slightly apart, we *should* get an exception. But to
    # avoid false positives when balls are slightly moving towards each other, we allow
    # it.
    assert ec((0, 0), (5e-16, 1)) == ((5e-16, 0), (0, 1))

    # check exceptions
    with pytest.raises(ValueError):
        ec((0, 0), (6e-16, 1))

    # collision of two massless particles makes no sense
    with pytest.raises(FloatingPointError):
        elastic_collision(pos1, (1, 0), 0, pos2, (0, 0), 0)


if __name__ == "__main__":
    pytest.main()
