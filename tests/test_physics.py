from math import cos, sin, sqrt

import numpy as np
import pytest
from pytest import approx

from billiards.physics import elastic_collision, time_of_impact

INF = float("inf")
np.seterr(divide="raise")  # use pytest.raises to catch them


def test_time_of_impact():
    # check that only relative coordinates are important
    assert time_of_impact((0, 42), (42, 0), 1, (5, 42), (41, 0), 1) == 3
    assert time_of_impact((0, 0), (0, 0), 1, (5, 0), (-1, 0), 1) == 3

    # for convenience
    def toi(p2, v2, r2, t_eps=0):
        return time_of_impact((0, 0), (0, 0), 1, p2, v2, r2, t_eps)

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
    assert toi((1, 2), (0, -1), sqrt(2) - 1) == approx(1)

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
    assert toi(diag, (-1, 0), r2=1 + 1e-5, t_eps=1e-4) == approx(0.0, abs=2e-5)
    assert toi(diag, (-1, 0), r2=1) == approx(0.0)
    assert toi((sqrt(2), sqrt(2)), (-1, 0), r2=1) == approx(0.0)

    # using t_eps to detect collision
    x, y = 2 * cos(1 / 4), 2 * sin(1 / 4)
    assert (x * x + y * y) - (1 + 1) ** 2 < 0  # rounding error => not zero
    assert toi((x, y), (-1, 0), 1) == INF  # fails to detect collision
    assert toi((x, y), (-1, 0), 1, t_eps=1e-10) == approx(0.0)


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
