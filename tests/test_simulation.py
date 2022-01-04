import numpy as np
import pytest
from pytest import approx

import billiards
from billiards.simulation import Billiard

INF = float("inf")
np.seterr(divide="raise")  # use pytest.raises to catch them


def table_tolist(toi_table):
    return [row.tolist() for row in toi_table]


def test_time():
    bld = Billiard()

    assert bld.time == 0.0

    ret = bld.evolve(1.0)
    assert ret == []
    assert bld.time == 1.0

    ret = bld.evolve(42.0)
    assert ret == []
    assert bld.time == 42.0


def test_index():
    n = 10
    bld = Billiard()

    # add balls and check index
    for i in range(n):
        idx = bld.add_ball((i, 0), (0, i))
        assert idx == i

    assert bld.num == n

    # check that the indices are actually right
    for idx in range(n):
        assert tuple(bld.balls_position[idx]) == (idx, 0)
        assert tuple(bld.balls_velocity[idx]) == (0, idx)


def test_add():
    # missing required positional arguments
    bld = Billiard()
    with pytest.raises(TypeError):
        bld.add_ball((0, 0))

    # wrong type send to numpy
    bld = Billiard()
    with pytest.raises(ValueError):
        bld.add_ball((0, 0), None)

    # wrong data send to numpy
    bld = Billiard()
    with pytest.raises(ValueError):
        bld.add_ball((0, 0), (0, 0, 0))

    bld = Billiard()
    assert bld.add_ball((0, 0), (0, 0)) == 0

    # wrong type for radius
    bld = Billiard()
    with pytest.raises(TypeError):
        bld.add_ball((0, 0), (0, 0), None)

    bld = Billiard()
    assert bld.add_ball((0, 0), (0, 0), 0) == 0

    # wrong type for mass
    bld = Billiard()
    with pytest.raises(TypeError):
        bld.add_ball((0, 0), (0, 0), 1, None)

    bld = Billiard()
    assert bld.add_ball((0, 0), (0, 0), 0, 0) == 0


def test_movement():
    bld = Billiard()

    # add ten balls
    for i in range(10):
        bld.add_ball((i, 0), (0, 1))

    # move
    time = 42.0
    ret = bld.evolve(time)
    assert ret == []

    for idx in range(10):
        # movement in y-direction
        assert tuple(bld.balls_position[idx]) == (idx, time)
        assert tuple(bld.balls_velocity[idx]) == (0, 1)


def test_toi_structure():
    bld = Billiard()

    for i in range(1, 10):
        bld.add_ball((i, 0), (0, 1))
        assert bld.num == i

        assert len(bld.toi_table) == i
        assert bld.toi_table[i - 1].shape == (i - 1,)

        assert bld._balls_toi.shape == (i,)
        assert len(bld._balls_idx) == i

        assert bld._obstacles_toi.shape == (i,)
        assert len(bld._obstacles_obs) == i


def test_toi_contents():
    bld = Billiard()

    # add a single ball, no collision possible here
    bld.add_ball((0, 0), (0, 0), 1)
    assert bld._balls_toi.tolist() == [INF]
    assert bld._balls_idx == [-1]
    assert bld.next_ball_ball_collision == (INF, -1, 0)

    # add one more ball on collision course
    bld.add_ball((4, 0), (-1, 0), 1)
    assert bld.toi_table[1].tolist() == [2.0]
    assert bld._balls_toi.tolist() == [INF, 2.0]
    assert bld._balls_idx == [-1, 0]
    assert bld.next_ball_ball_collision == (2.0, 0, 1)

    # add a third ball that collides earlier with the first one and then with
    # the second one
    bld.add_ball((0, 4), (0, -2), 1)
    assert bld.toi_table[2].tolist() == [1.0, approx(2.0)]
    assert bld._balls_toi.tolist() == [INF, 2.0, 1.0]
    assert bld._balls_idx == [-1, 0, 0]
    assert bld.next_ball_ball_collision == (1.0, 0, 2)

    # test simulation.calc_toi
    assert bld.calc_toi(0, 1) == 2.0
    assert bld.calc_toi(0, 2) == 1.0
    assert bld.calc_toi(1, 2) == approx(2.0)


def test_simple_collision():
    bld = Billiard()

    bld.add_ball((2, 0), (4, 0), radius=1)
    bld.evolve(10.0)
    assert tuple(bld.balls_position[0]) == (42.0, 0.0)
    assert tuple(bld.balls_velocity[0]) == (4.0, 0.0)

    # add another ball that will collide with the first one
    bld.add_ball((50, 18), (0, -9), radius=1, mass=2)
    assert bld.next_ball_ball_collision == (approx(11.79693), 0, 1)

    collisions = bld.evolve(14.0)
    assert bld.time == 14
    assert len(collisions) == 1
    assert collisions[0] == (approx(11.79693), 0, 1)
    assert tuple(bld.balls_position[0]) == (approx(46.2503), approx(-26.43683))
    assert tuple(bld.balls_position[1]) == (approx(55.8748), approx(-4.78158))
    assert tuple(bld.balls_velocity[0]) == (approx(-1.333333), approx(-12))
    assert tuple(bld.balls_velocity[1]) == (approx(2.666667), approx(-3))


def test_newton_cradle():
    bld = Billiard()

    # setup Newton's cradle with four balls
    bld.add_ball((-3, 0), (1, 0), 1)
    bld.add_ball((0, 0), (0, 0), 1)
    bld.add_ball((5, 0), (0, 0), 1)  # this is the last ball (more coverage)
    bld.add_ball((3, 0), (0, 0), 1)  # in direct contact with third ball

    assert bld.next_ball_ball_collision == (1.0, 0, 1)

    # first collision
    collisions = bld.evolve(1.0)
    assert len(collisions) == 1
    assert collisions[0] == (1.0, 0, 1)
    assert tuple(bld.balls_position[0]) == (-2, 0)
    assert tuple(bld.balls_velocity[0]) == (0, 0)
    assert tuple(bld.balls_position[1]) == (0, 0)
    assert tuple(bld.balls_velocity[1]) == (1, 0)
    assert bld.next_ball_ball_collision == (2.0, 1, 3)

    # second and third collision and then some more time
    collisions = bld.evolve(11.0)
    assert len(collisions) == 2
    assert collisions[0] == (2.0, 1, 3)
    assert collisions[1] == (2.0, 2, 3)
    assert tuple(bld.balls_position[1]) == (1, 0)
    assert tuple(bld.balls_velocity[1]) == (0, 0)
    assert tuple(bld.balls_position[2]) == (5 + (11 - 2) * 1, 0)
    assert tuple(bld.balls_velocity[2]) == (1, 0)
    assert tuple(bld.balls_position[3]) == (3, 0)
    assert tuple(bld.balls_velocity[3]) == (0, 0)

    # there are no other collisions
    assert table_tolist(bld.toi_table) == [[], [INF], [INF, INF], [INF, INF, INF]]
    assert bld._balls_toi.tolist() == [INF, INF, INF, INF]
    assert bld._balls_idx == [-1, 0, 0, 0]
    assert bld.next_ball_ball_collision == (INF, -1, 0)


def test_masses():
    bld = Billiard()

    # setup three balls
    bld.add_ball((-3, 0), (1, 0), 1, mass=0)  # massless
    bld.add_ball((0, 0), (0, 0), 1, mass=42)  # finite mass
    bld.add_ball((4, 0), (-1, 0), 1, mass=INF)  # infinite mass
    assert table_tolist(bld.toi_table) == [[], [1.0], [2.5, 2.0]]

    bld.evolve(1.0)  # massless <-> finite mass collision
    assert tuple(bld.balls_position[0]) == (-2, 0)
    assert tuple(bld.balls_velocity[0]) == (-1, 0)
    assert tuple(bld.balls_position[1]) == (0, 0)
    assert tuple(bld.balls_velocity[1]) == (0, 0)
    assert table_tolist(bld.toi_table) == [[], [INF], [INF, 2.0]]

    bld.evolve(2.0)  # finite mass <-> infinite mass collision
    assert tuple(bld.balls_position[1]) == (0, 0)
    assert tuple(bld.balls_velocity[1]) == (-2, 0)
    assert tuple(bld.balls_position[2]) == (2, 0)
    assert tuple(bld.balls_velocity[2]) == (-1, 0)
    assert table_tolist(bld.toi_table) == [[], [3.0], [INF, INF]]

    bld.evolve(3.0)  # again massless <-> finite mass collision
    assert tuple(bld.balls_position[0]) == (-4, 0)
    assert tuple(bld.balls_velocity[0]) == (-3, 0)
    assert tuple(bld.balls_position[1]) == (-2, 0)
    assert tuple(bld.balls_velocity[1]) == (-2, 0)
    assert table_tolist(bld.toi_table) == [[], [INF], [INF, INF]]


def test_exceptional_balls():
    bld = Billiard()

    # setup two point particles
    bld.add_ball((-3, 0), (1, 0), 0, mass=0)  # note: massless
    bld.add_ball((-2, 0), (0, 0), 0, mass=42)
    assert table_tolist(bld.toi_table) == [[], [INF]]  # no collision

    # setup two balls with infinite masses
    bld.add_ball((0, 0), (0, 0), 1, mass=INF)
    bld.add_ball((100, 0), (-20, 0), 1, mass=INF)
    assert bld.toi_table[2].tolist() == [2.0, INF]
    assert bld.toi_table[3].tolist() == [
        approx(102 / 21),
        approx(101 / 20),
        approx(98 / 20),
    ]

    assert bld.next_ball_ball_collision == (2.0, 0, 2)

    bld.evolve(2.0)  # massless <-> infinite mass collision
    assert tuple(bld.balls_position[0]) == (-1, 0)
    assert tuple(bld.balls_velocity[0]) == (-1, 0)
    assert tuple(bld.balls_position[2]) == (0, 0)
    assert tuple(bld.balls_velocity[2]) == (0, 0)
    assert table_tolist(bld.toi_table[:3]) == [[], [INF], [INF, INF]]
    assert bld.toi_table[3].tolist() == [
        approx(98 / 19),
        approx(101 / 20),
        approx(98 / 20),
    ]

    assert bld.next_ball_ball_collision == (approx(98 / 20), 2, 3)  # toi == 4.9

    bld.evolve(5.0)  # infinite mass <-> infinite mass collision
    assert tuple(bld.balls_position[2]) == (0, 0)
    assert tuple(bld.balls_velocity[2]) == (0, 0)
    assert tuple(bld.balls_position[3]) == (approx(2 + 0.1 * 20), 0)
    assert tuple(bld.balls_velocity[3]) == (20, 0)
    assert bld.toi_table[3].tolist() == [INF, INF, INF]

    assert tuple(bld.balls_position[0]) == (-4, 0)
    assert tuple(bld.balls_velocity[0]) == (-1, 0)

    # add one more massless ball that collides with the first one
    bld.add_ball((-6, 0), (0, 0), 1, mass=0)
    assert bld.toi_table[4].tolist() == [approx(6.0), INF, INF, INF]
    assert bld.next_ball_ball_collision == (approx(6.0), 0, 4)

    # collisions of two massless balls do not make sense
    with pytest.raises(FloatingPointError):
        bld.evolve(7.0)


def test_obstacles():
    disk = billiards.obstacles.Disk((0, 0), radius=1)
    bld = Billiard(obstacles=[disk])

    assert len(bld.obstacles) == 1
    assert bld.obstacles[0] == disk

    bld.add_ball((-10, 0), (1, 0), radius=1)
    assert bld._obstacles_toi.shape == (1,)
    assert bld._obstacles_toi.tolist() == [8.0]
    assert bld._obstacles_obs == [disk]
    assert bld.next_ball_obstacle_collision == (8.0, 0, disk)

    ret = bld.bounce_ballobstacle()
    assert ret == (8.0, 0, disk)
    assert bld._obstacles_toi.tolist() == [INF]
    assert bld._obstacles_obs == [None]
    assert bld.next_ball_obstacle_collision == (INF, 0, None)
    assert tuple(bld.balls_velocity[0]) == (-1.0, 0.0)

    # wrong type
    with pytest.raises(TypeError):
        Billiard(obstacles=[42])


def test_newtons_cradle_with_obstacles(create_newtons_cradle):
    bld = create_newtons_cradle(2)
    left_wall, right_wall = bld.obstacles

    # check toi of ball-ball and ball-obstacle collisions
    assert bld.next_ball_ball_collision == (3.0, 0, 1)
    assert bld._obstacles_toi.tolist() == [9.0, INF]
    assert bld._obstacles_obs == [right_wall, None]
    assert bld.next_ball_obstacle_collision == (9.0, 0, right_wall)
    assert bld.next_collision == bld.next_ball_ball_collision

    # evolve until first ball-ball collision
    collisions = bld.evolve(3.0)
    assert len(collisions) == 1
    assert collisions[0] == (3.0, 0, 1)

    # check again toi of ball-ball and ball-obstacle collisions
    assert bld.next_ball_ball_collision == (INF, -1, 0)
    assert bld._obstacles_toi.tolist() == [INF, 7.0]
    assert bld._obstacles_obs == [None, right_wall]
    assert bld.next_ball_obstacle_collision == (7.0, 1, right_wall)
    assert bld.next_collision == bld.next_ball_obstacle_collision

    # evolve until the second ball hits the right wall
    collisions = bld.evolve(7.0)
    assert len(collisions) == 1
    assert collisions[0] == (7.0, 1, right_wall)

    # check again toi of ball-ball and ball-obstacle collisions
    assert bld.next_ball_ball_collision == (11.0, 0, 1)
    assert bld._obstacles_toi.tolist() == [INF, 16.0]
    assert bld._obstacles_obs == [None, left_wall]
    assert bld.next_ball_obstacle_collision == (16.0, 1, left_wall)
    assert bld.next_collision == bld.next_ball_ball_collision

    # evolve until the second ball hits the first which then hits the left wall
    collisions = bld.evolve(14.0)
    assert len(collisions) == 2
    assert collisions[0] == (11.0, 0, 1)
    assert collisions[1] == (14.0, 0, left_wall)


if __name__ == "__main__":
    pytest.main()
