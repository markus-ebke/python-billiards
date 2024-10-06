from math import cos, pi, sin, sqrt

import numpy as np
import pytest
from pytest import approx

from billiards.physics import (
    elastic_collision,
    toi_and_param_ball_segment,
    toi_ball_ball,
    toi_ball_point,
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

    # toi was in the past
    assert toi((2, 2), (1, 1), 1) == (INF, None)

    # toi was in the past, use t_eps
    pos, vel, radius = (0.1, 1), (0, -1), 1 + 1e-5
    assert toi(pos, vel, radius) == (INF, None)
    assert toi(pos, vel, radius, t_eps=-1e-4) == (approx(-1e-5, abs=1e-14), 0.1)


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
