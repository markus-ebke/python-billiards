# -*- coding: utf-8 -*-
from math import sqrt

import pytest

from billiards import Simulation, elastic_collision, time_of_impact


def test_time_of_impact():
    inf = float("inf")

    # check that only relative coordinates are important
    assert time_of_impact((0, 42), (42, 0), 1, (5, 42), (41, 0), 1) == 3
    assert time_of_impact((0, 0), (0, 0), 1, (5, 0), (-1, 0), 1) == 3

    # for convenience
    def toi(p2, v2, r2):
        return time_of_impact((0, 0), (0, 0), 1, p2, v2, r2)

    # check miss
    assert toi((2, 0), (1, 0), 1) == inf
    assert toi((2, 0), (0, 1), 1) == inf

    # check head-on impact
    assert toi((3, 0), (-1, 0), 1) == 1.0
    assert toi((0, 101), (0, -33), 1) == pytest.approx(3.0)

    # check sliding past each other
    assert toi((2, 0), (0, 1), 1) == inf
    assert toi((2, 10), (0, -1), 1) == inf

    # check sideways collision
    # length of diagonal of a unit square is sqrt(2)
    assert toi((1, 2), (0, -1), sqrt(2) - 1) == pytest.approx(1)

    # check touching, note that this might not work so nicely with floating
    # point numbers
    assert toi((2, 0), (-1, 0), 1) == 0
    assert toi((1 + 1e-12, 1), (0, -1), sqrt(2) - 1) == pytest.approx(0.0)

    # check one inside the other
    assert toi((1, 0), (-42, 0), 1) == inf
    assert toi((1, 0), (-42, 0), 10) == inf

    # check point particle
    assert toi((2, 0), (-1, 0), 0) == 1  # head-on
    assert toi((1, 0), (0, 1), 0) == inf  # slide
    # cos(60°) == 1/2 => pythagoras: sin(60°) == sqrt(1 - 1/2**2) == sqrt(3/4)
    assert toi((0.5, 1), (0, -1), 0) == pytest.approx(1 - sqrt(3 / 4))  # side


def test_elastic_collision():
    pos1, pos2 = (0, 0), (2, 0)
    mass1, mass2 = 1, 1

    def ec(vel1, vel2):
        v1, v2 = elastic_collision(pos1, vel1, mass1, pos2, vel2, mass2)
        return (tuple(v1), tuple(v2))

    # head-on collision
    assert ec((0, 0), (-1, 0)) == ((-1, 0), (0, 0))
    assert ec((1, 0), (-1, 0)) == ((-1, 0), (1, 0))
    assert ec((1, 0), (0, 0)) == ((0, 0), (1, 0))

    # sideways collsion
    assert ec((0, 0), (-1, 1)) == ((-1, 0), (0, 1))
    assert ec((0, 0), (-0.5, 1)) == ((-0.5, 0), (0, 1))
    assert ec((0, 0), (-42, 1 / 42)) == ((-42, 0), (0, 1 / 42))


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
        pos = sim.balls_position[idx]
        assert pos[0] == idx

        vel = sim.balls_velocity[idx]
        assert vel[1] == idx


def test_movement():
    sim = Simulation()

    # add ten balls
    for i in range(10):
        sim.add_ball((i, 0), (0, 1))

    # move
    dt = 42
    sim.step(dt)

    for idx in range(10):
        # movement in y-direction
        pos = sim.balls_position[idx]
        assert pos[0] == idx and pos[1] == dt

        # no change in velocity
        vel = sim.balls_velocity[idx]
        assert vel[0] == 0 and vel[1] == 1


def test_toi_structure():
    sim = Simulation()

    for i in range(10):
        sim.add_ball((i, 0), (0, 1))

        assert len(sim.toi_table) == i + 1
        assert len(sim.toi_table[i]) == i

        assert len(sim.toi_min) == i + 1


def test_toi_contents():
    inf = float("inf")
    sim = Simulation()

    # add a single ball, no collision possible here
    sim.add_ball((0, 0), (0, 0), 1)
    assert sim.toi_min[0] == (inf, -1)
    assert sim.toi_next == (inf, -1)

    # add one more ball on collision course
    sim.add_ball((4, 0), (-1, 0), 1)
    assert sim.toi_table[1] == [2.0]
    assert sim.toi_min[1] == (2.0, 0)
    assert sim.toi_next == (2.0, 0)

    # add a third ball that collides earlier with the first one and then with
    # the second one
    sim.add_ball((0, 4), (0, -2), 1)
    assert sim.toi_table[2] == [1.0, pytest.approx(2.0)]
    assert sim.toi_min[2] == (1.0, 0)
    assert sim.toi_next == (1.0, 0)

    # test Simulation.calc_toi
    assert sim.calc_toi(0, 1) == 2.0
    assert sim.calc_toi(0, 2) == 1.0
    assert sim.calc_toi(1, 2) == pytest.approx(2.0)


if __name__ == "__main__":
    pytest.main()
