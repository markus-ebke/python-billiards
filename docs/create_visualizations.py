#!/usr/bin/env python3
import random
from math import cos, pi, sin
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm

import billiards
from billiards import visualize

here = Path(__file__).parent.resolve()  # should be docs folder


def quickstart():
    # Quickstart - Setup
    obstacles = [billiards.obstacles.InfiniteWall((0, -1), (0, 1), exterior="right")]
    bld = billiards.Billiard(obstacles)
    bld.add_ball((3, 0), (0, 0), radius=0.2)
    bld.add_ball((6, 0), (-1, 0), radius=1, mass=100 ** 5)
    fig = visualize.plot(bld)
    fig.savefig(here / "_images/quickstart_1.svg")
    # plt.show()

    v_squared = (bld.balls_velocity ** 2).sum(axis=1)
    print(f"Kinetic energy before: {(v_squared * bld.balls_mass).sum() / 2}")

    print()

    # Quickstart - Iteration
    print(bld.next_collision)
    total_collisions = 0
    for i in [1, 2, 3, 4, 5]:
        total_collisions += sum(bld.evolve(i))
        print(f"Until t = {bld.time}: {total_collisions} collisions")
    print(bld.time)
    fig = visualize.plot(bld)
    fig.savefig(here / "_images/quickstart_2.svg")
    # plt.show()

    print()

    # Quickstart - End Result
    total_collisions += sum(bld.evolve(16))
    print(bld.balls_velocity)
    print(bld.next_ball_ball_collision)
    print(bld.next_ball_obstacle_collision)
    print(total_collisions)
    fig = visualize.plot(bld)
    fig.savefig(here / "_images/quickstart_3.svg")
    # plt.show()

    v_squared = (bld.balls_velocity ** 2).sum(axis=1)
    print(f"Kinetic energy after: {(v_squared * bld.balls_mass).sum() / 2}")


def brownian_motion(animate=False):
    # fixed random seed for reproducibility, seed = 4 keeps the big ball away from the
    # walls
    random.seed(4)

    # the billiard table is a square box
    bounds = [
        billiards.InfiniteWall((-1, -1), (1, -1)),  # bottom side
        billiards.InfiniteWall((1, -1), (1, 1)),  # right side
        billiards.InfiniteWall((1, 1), (-1, 1)),  # top side
        billiards.InfiniteWall((-1, 1), (-1, -1)),  # left side
    ]
    bld = billiards.Billiard(obstacles=bounds)

    # distribute small particles (atoms) uniformly in the square, moving in random
    # directions but with the same speed
    for _i in range(250):
        pos = [random.uniform(-0.99, 0.99), random.uniform(-0.99, 0.99)]
        angle = random.uniform(0, 2 * pi)
        vel = [cos(angle), sin(angle)]

        bld.add_ball(pos, vel, radius=0.01, mass=1)

    # add a bigger ball (like a dust particle)
    idx = bld.add_ball((0, 0), (0, 0), radius=0.1, mass=10)

    # simulate until t = 50, recording the position at each collision
    end_time = 50
    poslist = []

    poslist = [bld.balls_position[idx].copy()]  # record initial position

    def record(t, p, u, v, i_o):
        poslist.append(p)

    if animate:  # just to check animation
        anim = visualize.animate(bld, end_time, velocity_arrow_factor=0)
        anim._fig.set_size_inches((7, 7))
        anim.save("brownian motion.mp4")
        # plt.show()
        return

    with tqdm(total=end_time) as pbar:
        t_prev = bld.time

        def progress(t):
            nonlocal t_prev
            t_now = round(t, 1)
            pbar.update(t_now - t_prev)
            t_prev = t_now

        bld.evolve(end_time, time_callback=progress, ball_callbacks={idx: record})
    poslist.append(bld.balls_position[idx].copy())  # record last position

    # plot the billiard and overlay the path of the particle
    fig = visualize.plot(bld, velocity_arrow_factor=0)
    fig.set_size_inches((7, 7))
    ax = fig.gca()
    poslist = np.asarray(poslist)
    ax.plot(poslist[:, 0], poslist[:, 1], color="red")
    plt.savefig(here / "_images/brownian_motion.svg")
    # plt.show()


def newtons_cradle():
    # example used in docs/usage.rst

    # 1. Setup
    walls = [
        billiards.InfiniteWall((-4, -2), (-4, 2), exterior="right"),
        billiards.InfiniteWall((10, -2), (10, 2), exterior="left"),
    ]
    bld = billiards.Billiard(obstacles=walls)

    # 2. Add Balls
    bld.add_ball(pos=(-3, 0), vel=(2, 0), radius=1)
    bld.add_ball((0, 0), (0, 0), 1)
    bld.add_ball((2.1, 0), (0, 0), 1)
    bld.add_ball((4.2, 0), (0, 0), 1)
    bld.add_ball((6.3, 0), (0, 0), 1)

    # 3. Run Simulation
    print(bld.next_ball_ball_collision)
    print(bld.next_ball_obstacle_collision)
    print(bld.next_collision)

    def print_time(t):
        print(f"Collision at t = {t:.3}")

    bld.evolve(end_time=4, time_callback=print_time)
    print(bld.time)
    anim = billiards.visualize.animate(bld, end_time=12)
    anim.save(here / "_static/newtons_cradle.mp4")
    # plt.show()

    # mess it up
    bld.balls_position[2, 1] = 1e-10
    bld.recompute_toi(indices=2)

    poslist = []

    def record(t, pos, vel_old, vel_new, idx_or_obs):
        poslist.append(pos)

    bld.evolve(end_time=40, ball_callbacks={2: record})
    poslist.append(bld.balls_position[2].copy())

    fig = visualize.plot(bld)  # state of the billiard right now
    x = [pos[0] for pos in poslist]
    y = [pos[1] for pos in poslist]
    fig.gca().plot(x, y, color="blue")  # overlay trajectory
    plt.savefig(here / "_images/newtons_failed_cradle.svg")
    # plt.show()


if __name__ == "__main__":
    quickstart()
    brownian_motion(animate=False)
    newtons_cradle()
