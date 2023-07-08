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
    assert ret == (0, 0)
    assert bld.time == 1.0

    ret = bld.evolve(42.0)
    assert ret == (0, 0)
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
    assert ret == (0, 0)

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
    toi = approx(11.79693)
    assert bld.next_ball_ball_collision == (toi, 0, 1)

    # record ball collisions via callback function
    collisions = []

    def record(t, p, u, v, j):
        nonlocal collisions
        collisions.append((t, p.tolist(), u.tolist(), v.tolist(), j))

    ret = bld.evolve(14.0, ball_callbacks={0: record, 1: record})
    assert bld.time == 14
    assert ret == (1, 0)
    assert len(collisions) == 2
    assert collisions[0] == (
        toi,
        [approx(49.18772), 0],
        [4, 0],
        [approx(-4 / 3), -12],
        1,
    )
    assert collisions[1] == (
        toi,
        [50, approx(1.827623)],
        [0, -9],
        [approx(8 / 3), -3],
        0,
    )
    assert tuple(bld.balls_position[0]) == (approx(46.2503), approx(-26.43683))
    assert tuple(bld.balls_position[1]) == (approx(55.8748), approx(-4.78158))
    assert tuple(bld.balls_velocity[0]) == (approx(-4 / 3), -12)
    assert tuple(bld.balls_velocity[1]) == (approx(8 / 3), -3)


def test_newton_cradle():
    bld = Billiard()

    # setup Newton's cradle with four balls
    bld.add_ball((-3, 0), (1, 0), 1)
    bld.add_ball((0, 0), (0, 0), 1)
    bld.add_ball((5, 0), (0, 0), 1)  # this is the last ball (more coverage)
    bld.add_ball((3, 0), (0, 0), 1)  # in direct contact with third ball

    assert bld.next_ball_ball_collision == (1.0, 0, 1)

    # first collision
    ret = bld.evolve(1.0)
    assert ret == (1, 0)
    assert tuple(bld.balls_position[0]) == (-2, 0)
    assert tuple(bld.balls_velocity[0]) == (0, 0)
    assert tuple(bld.balls_position[1]) == (0, 0)
    assert tuple(bld.balls_velocity[1]) == (1, 0)
    assert bld.next_ball_ball_collision == (2.0, 1, 3)

    # second and third collision and then some more time
    ret = bld.evolve(11.0)
    assert ret == (2, 0)
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
    disk = billiards.Disk((0, 0), radius=1)
    bld = Billiard(obstacles=[disk])

    assert len(bld.obstacles) == 1
    assert bld.obstacles[0] == disk

    bld.add_ball((-10, 0), (1, 0), radius=1)
    assert bld._obstacles_toi.shape == (1,)
    assert bld._obstacles_toi.tolist() == [8.0]
    assert bld._obstacles_obs == [(disk, ())]
    assert bld.next_ball_obstacle_collision == (8.0, 0, (disk, ()))

    # record ball collisions via callback function
    collisions = []

    def record(t, p, u, v, o):
        nonlocal collisions
        collisions.append((t, p.tolist(), u.tolist(), v.tolist(), o))

    bld.bounce_ballobstacle(ball_callbacks={0: record})
    assert len(collisions) == 1
    assert collisions[0] == (8.0, [-2.0, 0.0], [1.0, 0.0], [-1.0, 0.0], disk)
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
    assert bld._obstacles_obs == [(right_wall, (1.0,)), None]
    assert bld.next_ball_obstacle_collision == (9.0, 0, (right_wall, (1.0,)))
    assert bld.next_collision == bld.next_ball_ball_collision

    # evolve until first ball-ball collision
    collisions = bld.evolve(3.0)
    assert collisions == (1, 0)

    # check again toi of ball-ball and ball-obstacle collisions
    assert bld.next_ball_ball_collision == (INF, -1, 0)
    assert bld._obstacles_toi.tolist() == [INF, 7.0]
    assert bld._obstacles_obs == [None, (right_wall, (1.0,))]
    assert bld.next_ball_obstacle_collision == (7.0, 1, (right_wall, (1.0,)))
    assert bld.next_collision == bld.next_ball_obstacle_collision

    # evolve until the second ball hits the right wall
    collisions = bld.evolve(7.0)
    assert collisions == (0, 1)

    # check again toi of ball-ball and ball-obstacle collisions
    assert bld.next_ball_ball_collision == (11.0, 0, 1)
    assert bld._obstacles_toi.tolist() == [INF, 16.0]
    assert bld._obstacles_obs == [None, (left_wall, (1.0,))]
    assert bld.next_ball_obstacle_collision == (16.0, 1, (left_wall, (1.0,)))
    assert bld.next_collision == bld.next_ball_ball_collision

    # evolve until the second ball hits the first which then hits the left wall
    collisions = bld.evolve(14.0)
    assert collisions == (1, 1)


def test_callbacks(create_newtons_cradle):
    bld = create_newtons_cradle(2)
    left_wall, right_wall = bld.obstacles

    # exception for wrong type
    with pytest.raises(TypeError):
        bld.evolve(15.0, ball_callbacks=lambda bla: bla)

    with pytest.raises(TypeError):
        bld.evolve(15.0, ball_callbacks=[lambda bla: bla])

    # create recorder for time
    times = []

    def record_time(t):
        nonlocal times
        times.append(t)

    # create recorders for every collision, but only save time and ball indices/obstacle
    # note that every ball-ball collision will create two entries!
    collisions = []

    def record_i(i):
        def record(t, p, u, v, j_o):
            nonlocal collisions
            collisions.append((t, i, j_o))

        return record

    callbacks = {i: record_i(i) for i in range(bld.num)}

    # evolve until first ball-ball collision
    ret = bld.evolve(15.0, time_callback=record_time, ball_callbacks=callbacks)
    assert ret == (2, 2)
    assert len(times) == 4
    assert times == [3.0, 7.0, 11.0, 14.0]
    assert len(collisions) == 2 * ret[0] + ret[1]
    assert collisions[0] == (3.0, 0, 1)
    assert collisions[1] == (3.0, 1, 0)
    assert collisions[2] == (7.0, 1, right_wall)
    assert collisions[3] == (11.0, 0, 1)
    assert collisions[4] == (11.0, 1, 0)
    assert collisions[5] == (14.0, 0, left_wall)


def test_step_consistency():
    # Since billiards is a chaotic system, small deviations due to floating point issues
    # can have a large effect on the final result. Here we make sure that computing the
    # simulation in one go gives the same end result as stopping and resuming the
    # simulation in multiple steps. If the end results were the deviate, then e.g. the
    # result of visualize.animate could not be trusted

    # the billiard table is a square box
    bounds = [
        billiards.InfiniteWall((-1, -1), (1, -1)),  # bottom side
        billiards.InfiniteWall((1, -1), (1, 1)),  # right side
        billiards.InfiniteWall((1, 1), (-1, 1)),  # top side
        billiards.InfiniteWall((-1, 1), (-1, -1)),  # left side
    ]

    # define two billiards
    bld_once = Billiard(obstacles=bounds)
    bld_step = Billiard(obstacles=bounds)

    # place a few balls with 'random' initial conditions
    bld_once.add_ball((0, 0.2), (1, 2), radius=0.2)
    bld_step.add_ball((0, 0.2), (1, 2), radius=0.2)
    bld_once.add_ball((0, 0.5), (-1, 2), radius=0.2)
    bld_step.add_ball((0, 0.5), (-1, 2), radius=0.2)
    bld_once.add_ball((0, -0.8), (0, -1), radius=0.2)
    bld_step.add_ball((0, -0.8), (0, -1), radius=0.2)
    bld_once.add_ball((0.7, -0.8), (0, 0), radius=0.2)
    bld_step.add_ball((0.7, -0.8), (0, 0), radius=0.2)

    # this billiard deviates between t = 1 and t = 2 if we don't handle stopping and
    # resuming properly
    end_time = 10
    bld_once.evolve(end_time)  # in one go

    # stopping and resuming 30 times each second (as visualize.animate would do it)
    for i in range(end_time):
        for j in range(1, 31):
            bld_step.evolve(i + j / 30)

    # compare the end states, they should match exactly
    diff = bld_once.balls_position - bld_step.balls_position
    assert np.linalg.norm(diff, axis=1).max() == 0


def copy_and_check(bld):
    """Re-setup a billiard and check that all internal attributes are consistent"""

    def table_tolist_approx(toi_table):
        return [approx(row.tolist(), rel=1e-15, abs=1e-15) for row in toi_table]

    def tolist_approx(arr):
        return approx(arr.tolist(), rel=1e-15, abs=1e-15)

    # 'copy' billiard table
    bld_check = Billiard(obstacles=bld.obstacles)
    bld_check.time = bld.time
    for idx in range(bld.num):
        p = bld.balls_position[idx]
        v = bld.balls_velocity[idx]
        r = bld.balls_radius[idx]
        m = bld.balls_mass[idx]
        bld_check.add_ball(p, v, r, m)

    # compare ball parameters
    assert bld.time == bld_check.time
    assert bld.num == bld_check.num
    assert bld.balls_position.tolist() == bld_check.balls_position.tolist()
    assert bld.balls_velocity.tolist() == bld_check.balls_velocity.tolist()
    assert bld.balls_radius == bld_check.balls_radius
    assert bld.balls_mass == bld_check.balls_mass

    # compare ball-ball collisions
    assert table_tolist(bld.toi_table) == table_tolist_approx(bld_check.toi_table)
    assert bld._balls_toi.tolist() == approx(bld_check._balls_toi.tolist())
    assert bld._balls_idx == bld_check._balls_idx
    t, i, j = bld.next_ball_ball_collision
    assert t == approx(bld_check.next_ball_ball_collision[0])
    assert i == bld_check.next_ball_ball_collision[1]
    assert j == bld_check.next_ball_ball_collision[2]

    # compare ball-obstacle collisions
    assert bld._obstacles_toi.tolist() == tolist_approx(bld_check._obstacles_toi)
    assert bld._obstacles_obs == bld_check._obstacles_obs
    t, i, o = bld.next_ball_obstacle_collision
    assert t == approx(bld_check.next_ball_obstacle_collision[0])
    assert i == bld_check.next_ball_obstacle_collision[1]
    assert o == bld_check.next_ball_obstacle_collision[2]


def test_recompute_toi_tables():
    # setup a 4 ball billiard in a square box
    bounds = [
        billiards.InfiniteWall((-1, -1), (1, -1)),  # bottom side
        billiards.InfiniteWall((1, -1), (1, 1)),  # right side
        billiards.InfiniteWall((1, 1), (-1, 1)),  # top side
        billiards.InfiniteWall((-1, 1), (-1, -1)),  # left side
    ]
    bld = Billiard(obstacles=bounds)
    bld.add_ball((0, 0.2), (1, 2), radius=0.2)
    bld.add_ball((0, 0.5), (-1, 2), radius=0.2)
    bld.add_ball((0, -0.8), (0, -1), radius=0.2)
    bld.add_ball((0.7, -0.8), (0, 0), radius=0.2)

    # simulate a bit, then modify a single ball
    bld.evolve(1)
    bld.balls_position[0] = (0, 0)
    bld.recompute_toi(0)
    assert bld.time == 1
    copy_and_check(bld)

    # evolve some more and modify two balls
    bld.evolve(2)
    bld.balls_velocity[1] = (0, 0)
    bld.balls_radius[2] = 0.1
    bld.recompute_toi([1, 2])
    assert bld.time == 2
    copy_and_check(bld)

    # evolve even more, then recompute everything
    bld.evolve(3)
    bld.recompute_toi()
    assert bld.time == 3
    copy_and_check(bld)


if __name__ == "__main__":
    pytest.main()
