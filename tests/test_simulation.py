# -*- coding: utf-8 -*-
from billiards import Simulation


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
