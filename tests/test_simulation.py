# -*- coding: utf-8 -*-
from math import sqrt

import numpy as np
import pytest

from billiards import Simulation, elastic_collision, time_of_impact

INF = float("inf")
np.seterr(divide="raise")  # use pytest.raises to catch them


def test_time_of_impact():
    # check that only relative coordinates are important
    assert time_of_impact((0, 42), (42, 0), 1, (5, 42), (41, 0), 1) == 3
    assert time_of_impact((0, 0), (0, 0), 1, (5, 0), (-1, 0), 1) == 3

    # for convenience
    def toi(p2, v2, r2):
        return time_of_impact((0, 0), (0, 0), 1, p2, v2, r2)

    # check miss
    assert toi((2, 0), (1, 0), 1) == INF
    assert toi((2, 0), (0, 1), 1) == INF

    # check head-on impact
    assert toi((3, 0), (-1, 0), 1) == 1.0
    assert toi((0, 101), (0, -33), 1) == pytest.approx(3.0)

    # check sliding past each other
    assert toi((2, 0), (0, 1), 1) == INF
    assert toi((2, 10), (0, -1), 1) == INF

    # check sideways collision
    # length of diagonal of a unit square is sqrt(2)
    assert toi((1, 2), (0, -1), sqrt(2) - 1) == pytest.approx(1)

    # check touching, note that this might not work so nicely with floating
    # point numbers
    assert toi((2, 0), (-1, 0), 1) == 0
    assert toi((1 + 1e-12, 1), (0, -1), sqrt(2) - 1) == pytest.approx(0.0)

    # check one inside the other
    assert toi((1, 0), (-42, 0), 1) == INF
    assert toi((1, 0), (-42, 0), 10) == INF

    # check point particle
    assert toi((2, 0), (-1, 0), 0) == 1  # head-on
    assert toi((1, 0), (0, 1), 0) == INF  # slide
    # cos(60°) == 1/2 => pythagoras: sin(60°) == sqrt(1 - 1/2**2) == sqrt(3/4)
    assert toi((0.5, 1), (0, -1), 0) == pytest.approx(1 - sqrt(3 / 4))  # side


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


def test_index():
    n = 10
    sim = Simulation()

    # add balls and check index
    for i in range(n):
        idx = sim.add_ball((i, 0), (0, i))
        assert idx == i

    assert sim.num == n

    # check that the indices are actually right
    for idx in range(n):
        assert tuple(sim.balls_position[idx]) == (idx, 0)
        assert tuple(sim.balls_velocity[idx]) == (0, idx)


def test_movement():
    sim = Simulation()

    # add ten balls
    for i in range(10):
        sim.add_ball((i, 0), (0, 1))

    # move
    dt = 42.0
    sim.step(dt)

    for idx in range(10):
        # movement in y-direction
        assert tuple(sim.balls_position[idx]) == (idx, dt)
        assert tuple(sim.balls_velocity[idx]) == (0, 1)


def test_toi_structure():
    sim = Simulation()

    for i in range(10):
        sim.add_ball((i, 0), (0, 1))

        assert len(sim.toi_table) == i + 1
        assert len(sim.toi_table[i]) == i

        assert len(sim.toi_min) == i + 1


def test_toi_contents():
    sim = Simulation()

    # add a single ball, no collision possible here
    sim.add_ball((0, 0), (0, 0), 1)
    assert sim.toi_min[0] == (INF, -1)
    assert sim.toi_next == (INF, -1, 0)

    # add one more ball on collision course
    sim.add_ball((4, 0), (-1, 0), 1)
    assert sim.toi_table[1] == [2.0]
    assert sim.toi_min[1] == (2.0, 0)
    assert sim.toi_next == (2.0, 0, 1)

    # add a third ball that collides earlier with the first one and then with
    # the second one
    sim.add_ball((0, 4), (0, -2), 1)
    assert sim.toi_table[2] == [1.0, pytest.approx(2.0)]
    assert sim.toi_min[2] == (1.0, 0)
    assert sim.toi_next == (1.0, 0, 2)

    # test Simulation.calc_toi
    assert sim.calc_toi(0, 1) == 2.0
    assert sim.calc_toi(0, 2) == 1.0
    assert sim.calc_toi(1, 2) == pytest.approx(2.0)


def test_newton_cradle():
    sim = Simulation()

    # setup newton's cradle with four balls
    sim.add_ball((-3, 0), (1, 0), 1)
    sim.add_ball((0, 0), (0, 0), 1)
    sim.add_ball((5, 0), (0, 0), 1)  # this is the last ball (more coverage)
    sim.add_ball((3, 0), (0, 0), 1)  # in direct contact with third ball

    assert sim.toi_next == (1.0, 0, 1)

    # first collision
    sim.step(1.0)
    assert tuple(sim.balls_position[0]) == (-2, 0)
    assert tuple(sim.balls_velocity[0]) == (0, 0)
    assert tuple(sim.balls_position[1]) == (0, 0)
    assert tuple(sim.balls_velocity[1]) == (1, 0)
    assert sim.toi_next == (2.0, 1, 3)

    # second and third collision and then some more time
    sim.step(10.0)
    assert sim.time == 11.0
    assert tuple(sim.balls_position[1]) == (1, 0)
    assert tuple(sim.balls_velocity[1]) == (0, 0)
    assert tuple(sim.balls_position[2]) == (5 + (11 - 2) * 1, 0)
    assert tuple(sim.balls_velocity[2]) == (1, 0)
    assert tuple(sim.balls_position[3]) == (3, 0)
    assert tuple(sim.balls_velocity[3]) == (0, 0)

    # there are no other collisions
    assert sim.toi_table == [[], [INF], [INF, INF], [INF, INF, INF]]
    assert sim.toi_min == [(INF, -1), (INF, 0), (INF, 0), (INF, 0)]
    assert sim.toi_next == (INF, -1, 0)


def test_masses():
    sim = Simulation()

    # setup four balls
    sim.add_ball((-3, 0), (1, 0), 1, mass=0)  # massless
    sim.add_ball((0, 0), (0, 0), 1, mass=42)  # finite mass
    sim.add_ball((4, 0), (-1, 0), 1, mass=INF)  # infinite mass
    sim.add_ball((100, 0), (-20, 0), 0, mass=0)  # small, fast and massless
    assert sim.toi_table[:3] == [[], [1.0], [2.5, 2.0]]

    sim.step(1.0)  # massless <-> finite mass collision
    assert tuple(sim.balls_position[0]) == (-2, 0)
    assert tuple(sim.balls_velocity[0]) == (-1, 0)
    assert tuple(sim.balls_position[1]) == (0, 0)
    assert tuple(sim.balls_velocity[1]) == (0, 0)
    assert sim.toi_table[:3] == [[], [INF], [INF, 2.0]]

    sim.step(1.0)  # finite mass <-> infinite mass collision
    assert tuple(sim.balls_position[1]) == (0, 0)
    assert tuple(sim.balls_velocity[1]) == (-2, 0)
    assert tuple(sim.balls_position[2]) == (2, 0)
    assert tuple(sim.balls_velocity[2]) == (-1, 0)
    assert sim.toi_table[:3] == [[], [3.0], [INF, INF]]

    sim.step(1.0)  # again massless <-> finite mass collision
    assert tuple(sim.balls_position[0]) == (-4, 0)
    assert tuple(sim.balls_velocity[0]) == (-3, 0)
    assert tuple(sim.balls_position[1]) == (-2, 0)
    assert tuple(sim.balls_velocity[1]) == (-2, 0)
    assert sim.toi_table[:3] == [[], [INF], [INF, INF]]
    assert sim.toi_next == (pytest.approx(5.0), 2, 3)

    sim.step(2.0)  # infinite mass <-> massless
    assert tuple(sim.balls_position[2]) == pytest.approx((-1, 0))
    assert tuple(sim.balls_velocity[2]) == (-1, 0)
    assert tuple(sim.balls_position[3]) == pytest.approx((0, 0))
    assert tuple(sim.balls_velocity[3]) == pytest.approx((18, 0))

    # add one more massless ball
    sim.add_ball((19, 0), (0, 0), 1, mass=0)
    assert sim.calc_toi(3, 4) == pytest.approx(6.0)
    assert sim.toi_table[4] == [INF, INF, INF, pytest.approx(6.0)]
    assert sim.toi_min[:4] == [(INF, -1), (INF, 0), (INF, 0), (INF, 0)]
    assert sim.toi_min[4] == (pytest.approx(6.0), 3)
    assert sim.toi_next == (pytest.approx(6.0), 3, 4)

    # collisions of massless balls are do not make sense
    with pytest.raises(FloatingPointError):
        sim.collision(3, 4)

    with pytest.raises(FloatingPointError):
        sim.step(1.0)


if __name__ == "__main__":
    pytest.main()
