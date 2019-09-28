# -*- coding: utf-8 -*-
import numpy as np
import pytest
from pytest import approx

from billiards.simulation import Billiard

INF = float("inf")
np.seterr(divide="raise")  # use pytest.raises to catch them


def test_time():
    sim = Billiard()

    assert sim.time == 0.0

    sim.evolve(1.0)
    assert sim.time == 1.0

    sim.evolve(42.0)
    assert sim.time == 42.0


def test_index():
    n = 10
    sim = Billiard()

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
    sim = Billiard()

    # add ten balls
    for i in range(10):
        sim.add_ball((i, 0), (0, 1))

    # move
    time = 42.0
    sim.evolve(time)

    for idx in range(10):
        # movement in y-direction
        assert tuple(sim.balls_position[idx]) == (idx, time)
        assert tuple(sim.balls_velocity[idx]) == (0, 1)


def test_toi_structure():
    sim = Billiard()

    for i in range(10):
        sim.add_ball((i, 0), (0, 1))

        assert len(sim.toi_table) == i + 1
        assert len(sim.toi_table[i]) == i

        assert len(sim.toi_min) == i + 1


def test_toi_contents():
    sim = Billiard()

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
    assert sim.toi_table[2] == [1.0, approx(2.0)]
    assert sim.toi_min[2] == (1.0, 0)
    assert sim.toi_next == (1.0, 0, 2)

    # test Simulation.calc_toi
    assert sim.calc_toi(0, 1) == 2.0
    assert sim.calc_toi(0, 2) == 1.0
    assert sim.calc_toi(1, 2) == approx(2.0)


def test_simple_collision():
    sim = Billiard()

    sim.add_ball((2, 0), (4, 0), radius=1)
    sim.evolve(10.0)
    assert tuple(sim.balls_position[0]) == (42.0, 0.0)
    assert tuple(sim.balls_velocity[0]) == (4.0, 0.0)

    # add another ball that will collide with the first one
    sim.add_ball((50, 18), (0, -9), radius=1, mass=2)
    assert sim.toi_next == (approx(11.79693), 0, 1)

    sim.evolve(14.0)
    assert sim.time == 14
    assert tuple(sim.balls_position[0]) == (approx(46.2503), approx(-26.43683))
    assert tuple(sim.balls_position[1]) == (approx(55.8748), approx(-4.78158))
    assert tuple(sim.balls_velocity[0]) == (approx(-1.333333), approx(-12))
    assert tuple(sim.balls_velocity[1]) == (approx(2.666667), approx(-3))


def test_newton_cradle():
    sim = Billiard()

    # setup newton's cradle with four balls
    sim.add_ball((-3, 0), (1, 0), 1)
    sim.add_ball((0, 0), (0, 0), 1)
    sim.add_ball((5, 0), (0, 0), 1)  # this is the last ball (more coverage)
    sim.add_ball((3, 0), (0, 0), 1)  # in direct contact with third ball

    assert sim.toi_next == (1.0, 0, 1)

    # first collision
    sim.evolve(1.0)
    assert tuple(sim.balls_position[0]) == (-2, 0)
    assert tuple(sim.balls_velocity[0]) == (0, 0)
    assert tuple(sim.balls_position[1]) == (0, 0)
    assert tuple(sim.balls_velocity[1]) == (1, 0)
    assert sim.toi_next == (2.0, 1, 3)

    # second and third collision and then some more time
    sim.evolve(11.0)
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
    sim = Billiard()

    # setup three balls
    sim.add_ball((-3, 0), (1, 0), 1, mass=0)  # massless
    sim.add_ball((0, 0), (0, 0), 1, mass=42)  # finite mass
    sim.add_ball((4, 0), (-1, 0), 1, mass=INF)  # infinite mass
    assert sim.toi_table == [[], [1.0], [2.5, 2.0]]

    sim.evolve(1.0)  # massless <-> finite mass collision
    assert tuple(sim.balls_position[0]) == (-2, 0)
    assert tuple(sim.balls_velocity[0]) == (-1, 0)
    assert tuple(sim.balls_position[1]) == (0, 0)
    assert tuple(sim.balls_velocity[1]) == (0, 0)
    assert sim.toi_table == [[], [INF], [INF, 2.0]]

    sim.evolve(2.0)  # finite mass <-> infinite mass collision
    assert tuple(sim.balls_position[1]) == (0, 0)
    assert tuple(sim.balls_velocity[1]) == (-2, 0)
    assert tuple(sim.balls_position[2]) == (2, 0)
    assert tuple(sim.balls_velocity[2]) == (-1, 0)
    assert sim.toi_table == [[], [3.0], [INF, INF]]

    sim.evolve(3.0)  # again massless <-> finite mass collision
    assert tuple(sim.balls_position[0]) == (-4, 0)
    assert tuple(sim.balls_velocity[0]) == (-3, 0)
    assert tuple(sim.balls_position[1]) == (-2, 0)
    assert tuple(sim.balls_velocity[1]) == (-2, 0)
    assert sim.toi_table == [[], [INF], [INF, INF]]


def test_exceptional_balls():
    sim = Billiard()

    # setup two point particles
    sim.add_ball((-3, 0), (1, 0), 0, mass=0)  # note: massless
    sim.add_ball((-2, 0), (0, 0), 0, mass=42)
    assert sim.toi_table == [[], [INF]]  # no collision

    # setup two balls with infinite masses
    sim.add_ball((0, 0), (0, 0), 1, mass=INF)
    sim.add_ball((100, 0), (-20, 0), 1, mass=INF)
    assert sim.toi_table[2] == [2.0, INF]
    assert sim.toi_table[3] == [
        approx(102 / 21),
        approx(101 / 20),
        approx(98 / 20),
    ]

    assert sim.toi_next == (2.0, 0, 2)

    sim.evolve(2.0)  # massless <-> infinite mass collision
    assert tuple(sim.balls_position[0]) == (-1, 0)
    assert tuple(sim.balls_velocity[0]) == (-1, 0)
    assert tuple(sim.balls_position[2]) == (0, 0)
    assert tuple(sim.balls_velocity[2]) == (0, 0)
    assert sim.toi_table[:3] == [[], [INF], [INF, INF]]
    assert sim.toi_table[3] == [
        approx(98 / 19),
        approx(101 / 20),
        approx(98 / 20),
    ]

    assert sim.toi_next == (approx(98 / 20), 2, 3)  # toi == 4.9

    sim.evolve(5.0)  # infinite mass <-> infinite mass collision
    assert tuple(sim.balls_position[2]) == (0, 0)
    assert tuple(sim.balls_velocity[2]) == (0, 0)
    assert tuple(sim.balls_position[3]) == (approx(2 + 0.1 * 20), 0)
    assert tuple(sim.balls_velocity[3]) == (20, 0)
    assert sim.toi_table[3] == [INF, INF, INF]

    assert tuple(sim.balls_position[0]) == (-4, 0)
    assert tuple(sim.balls_velocity[0]) == (-1, 0)

    # add one more massless ball that collides with the first one
    sim.add_ball((-6, 0), (0, 0), 1, mass=0)
    assert sim.toi_table[4] == [approx(6.0), INF, INF, INF]
    assert sim.toi_next == (approx(6.0), 0, 4)

    # collisions of two massless balls do not make sense
    with pytest.raises(FloatingPointError):
        sim.evolve(7.0)


if __name__ == "__main__":
    pytest.main()
