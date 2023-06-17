from math import cos, pi, sin, sqrt

import numpy as np
import pytest
from pytest import approx

from billiards.physics import (
    elastic_collision,
    toi_ball_ball,
    toi_ball_point,
    toi_ball_segment,
)

INF = float("inf")
np.seterr(divide="raise")  # use pytest.raises to catch them


def test_toi_ball_ball():
    assert toi_ball_ball((0, 0), (0, 0), 1, (5, 0), (-1, 0), 1) == 3

    # check that only relative coordinates are important
    assert toi_ball_ball((0, 42), (42, 0), 1, (5, 42), (41, 0), 1) == 3

    # for convenience
    def toi(p2, v2, r2, t_eps=-0.0):
        return toi_ball_ball((0, 0), (0, 0), 1, p2, v2, r2, t_eps)

    # check miss
    assert toi((2, 0), (1, 0), 1) == INF
    assert toi((2, 0), (0, 1), 1) == INF

    # check head-on impact
    assert toi((3, 0), (-1, 0), 1) == 1.0
    assert toi((0, 101), (0, -33), 1) == approx(3.0)

    # check sliding past each other
    assert toi((2, 0), (0, 1), 1) == INF
    assert toi((2, 10), (0, -1), 1) == INF
    assert toi((sqrt(2), sqrt(2)), (1 - 1e-7, -1), 1) == approx(0.0, abs=1e-8)

    # check sideways collision
    # length of diagonal of a unit square is sqrt(2)
    assert toi((1, 2), (0, -1), sqrt(2) - 1) == approx(1.0)

    # check touching, note that this might not work so nicely with floating
    # point numbers
    assert toi((2, 0), (-1, 0), 1) == 0
    assert toi((1 + 1e-12, 1), (0, -1), sqrt(2) - 1) == approx(0.0)

    # check one inside the other
    assert toi((1, 0), (-42, 0), 1) == INF
    assert toi((1, 0), (-42, 0), 10) == INF

    # check point particle
    assert toi((2, 0), (-1, 0), 0) == 1  # head-on
    assert toi((1, 0), (0, 1), 0) == INF  # slide
    # cos(60°) == 1/2 => pythagoras: sin(60°) == sqrt(1 - 1/2**2) == sqrt(3/4)
    assert toi((0.5, 1), (0, -1), 0) == approx(1 - sqrt(3 / 4))  # side

    # test touching balls and t_eps
    diag = (sqrt(2), sqrt(2))
    assert toi(diag, (-1, 0), r2=1 + 1e-5) == INF
    assert toi(diag, (-1, 0), r2=1 + 1e-5, t_eps=-1e-4) == approx(0.0, abs=2e-5)
    assert toi(diag, (-1, 0), r2=1) == approx(0.0)

    # using t_eps to detect collision
    x, y = 2 * cos(1 / 4), 2 * sin(1 / 4)
    assert (x * x + y * y) - (1 + 1) ** 2 < 0  # rounding error => not zero
    assert toi((x, y), (-1, 0), 1) == INF  # fails to detect collision
    assert toi((x, y), (-1, 0), 1, t_eps=-1e-10) == approx(0.0)


def test_toi_ball_point():
    assert toi_ball_point((0, 0), (1, 0), 1, (5, 0)) == 4

    # check that only relative coordinates are important
    assert toi_ball_point((0, 42), (1, 0), 1, (5, 42)) == 4

    # for convenience
    def toi(pos, vel, radius, t_eps=-0.0):
        return toi_ball_point(pos, vel, radius, (0, 0), t_eps)

    # check miss
    assert toi((2, 0), (1, 0), 1) == INF
    assert toi((2, 0), (0, 1), 1) == INF

    # check head-on impact
    assert toi((2, 0), (-1, 0), 1) == 1.0
    assert toi((0, 100), (0, -33), 1) == approx(3.0)

    # check sliding past each other
    assert toi((1, 0), (0, 1), 1) == INF
    assert toi((1, 10), (0, -1), 1) == INF
    assert toi((sqrt(1 / 2), sqrt(1 / 2)), (1 - 1e-7, -1), 1) == approx(0.0, abs=1e-8)

    # check sideways collision
    # length of diagonal of a unit square is sqrt(2)
    assert toi((1, 2), (0, -1), sqrt(2)) == approx(1.0)
    # cos(60°) == 1/2 => pythagoras: sin(60°) == sqrt(1 - 1/2**2) == sqrt(3/4)
    assert toi((0.5, 1), (0, -1), 1) == approx(1 - sqrt(3 / 4))

    # check touching, note that this might not work so nicely with floating
    # point numbers
    assert toi((1, 0), (-1, 0), 1) == 0
    assert toi((1 + 1e-12, 1), (0, -1), sqrt(2)) == approx(0.0)

    # check point inside ball
    assert toi((1 - 1e-12, 0), (-42, 0), 1) == INF

    # test touching with t_eps
    diag = (sqrt(1 / 2), sqrt(1 / 2))
    assert toi(diag, (-1, 0), 1 + 1e-5) == INF
    assert toi(diag, (-1, 0), 1 + 1e-5, t_eps=-1e-4) == approx(0.0, abs=2e-5)
    assert toi(diag, (-1, 0), 1) == approx(0.0)

    # using t_eps to detect collision
    x, y = 2 * cos(1 / 4), 2 * sin(1 / 4)
    assert (x * x + y * y) - (1 + 1) ** 2 < 0  # rounding error => not zero
    assert toi((x, y), (-1, 0), 2) == INF  # fails to detect collision
    assert toi((x, y), (-1, 0), 2, t_eps=-1e-10) == approx(0.0)


def test_toi_ball_segment():
    start, end = np.asarray([0, 0]), np.asarray([1, 0])
    direction = end - start
    length_sqrd = direction.dot(direction)
    vector = direction / length_sqrd
    normal = np.asarray([-direction[1], direction[0]]) / sqrt(length_sqrd)

    line = (start, end, vector, normal)
    assert toi_ball_segment((1 / 2, 2), (0, -1), 1, *line) == 1

    # check that only relative coordinates are important
    line = (start + (42, 0), end + (42, 0), vector, normal)
    assert toi_ball_segment((1 / 2 + 42, 2), (0, -1), 1, *line) == 1

    # check that scale doesn't matter
    line = (10 * start, 10 * end, vector / 10, normal)
    assert toi_ball_segment((5, 20), (0, -10), 10, *line) == 1

    # for convenience
    def toi(pos, vel, radius, t_eps=-0.0):
        return toi_ball_segment(pos, vel, radius, start, end, vector, normal, t_eps)

    # collision at left endpoint
    for a in [0, 1 / 6, 1 / 4, -1 / 2, pi / 2 - 1e-6, pi / 2]:
        assert toi((-cos(a), sin(a)), (cos(a), -sin(a)), 1 / 2) == approx(0.5), a
    assert toi((-sqrt(1 / 2) - 1, sqrt(1 / 2) - 1), (1, 1), 1 + 1e-14) == approx(1.0)

    # collision along the line
    for a in [pi / 2 + 1e-6, 5 / 6 * pi - 1e-15]:
        pos = (-cos(a), sin(a))
        vel = (cos(a), -sin(a))
        assert toi(pos, vel, 1 / 2) == approx((pos[1] - 1 / 2) / (-vel[1])), a

    # miss
    assert toi((-1, 0), (0, 1), 1) == INF
    assert toi((-1, -1), (0, 1), 1) == INF
    assert toi((-sqrt(1 / 2) - 1, sqrt(1 / 2) - 1), (1, 1), 1 - 1e-10) == INF
    assert toi((0.1, 1), (1, 0), 1) == INF  # slide

    # overlap is a miss
    assert toi((-1, 0), (0, 1), 1.1) == INF
    assert toi((0.1, 0), (0, 1), 1) == INF
    assert toi((0.1, -0.5), (0, 1), 1) == INF
    assert toi((0.1, 0), (0, 1), 10) == INF

    # toi was in the past, use t_eps
    assert toi((0.1, 1), (0, -1), 1 + 1e-5) == INF
    assert toi((0.1, 1), (0, -1), 1 + 1e-5, t_eps=-1e-4) == approx(-1e-5, abs=1e-10)


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

    # collision of two massless particles makes no sense
    with pytest.raises(FloatingPointError):
        elastic_collision(pos1, (1, 0), 0, pos2, (0, 0), 0)


if __name__ == "__main__":
    pytest.main()
