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


# Quickstart - Setup
obstacles = [billiards.obstacles.InfiniteWall((0, -1), (0, 1), inside="right")]
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
    total_collisions += len(bld.evolve(i))
    print(f"Until t = {bld.time}: {total_collisions} collisions")
print(bld.time)
fig = visualize.plot(bld)
fig.savefig(here / "_images/quickstart_2.svg")
# plt.show()

print()

# Quickstart - End Result
total_collisions += len(bld.evolve(16))
print(bld.balls_velocity)
print(bld.next_ball_ball_collision)
print(bld.next_ball_obstacle_collision)
print(total_collisions)
fig = visualize.plot(bld)
fig.savefig(here / "_images/quickstart_3.svg")
# plt.show()

v_squared = (bld.balls_velocity ** 2).sum(axis=1)
print(f"Kinetic energy after: {(v_squared * bld.balls_mass).sum() / 2}")


# global settings
random.seed(0)  # fix random state for reproducibility

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
bld.add_ball((0, 0), (0, 0), radius=0.1, mass=10)

# simulate until t = 50, recording the position at each collision
end_time = 50
poslist = []
t_next = 0
# anim = visualize.animate(bld, end_time, velocity_arrow_factor=0)
# plt.show()
with tqdm(total=end_time) as pbar:
    while t_next < end_time:
        t_prev = t_next
        bld.evolve(t_next)
        poslist.append(bld.balls_position[-1].copy())
        t_next = min(bld._balls_toi[-1], bld._obstacles_toi[-1])
        pbar.update(t_next - t_prev)
bld.evolve(end_time)
poslist.append(bld.balls_position[-1])

# plot the billiard and overlay the path of the particle
fig = visualize.plot(bld, velocity_arrow_factor=0)
fig.set_size_inches((7, 7))
ax = fig.gca()
poslist = np.asarray(poslist)
ax.plot(poslist[:, 0], poslist[:, 1], marker=".", color="red")
plt.savefig(here / "_images/brownian_motion.svg")
# plt.show()


# Usage: Newton's cradle
bld = billiards.Billiard()
bld.add_ball((0, 0), (1, 0), 1)
bld.add_ball((3, 0), (0, 0), 1)
bld.add_ball((5.1, 0), (0, 0), 1)
bld.add_ball((7.2, 0), (0, 0), 1)
bld.add_ball((9.3, 0), (0, 0), 1)

anim = billiards.visualize.animate(bld, end_time=5)
anim.save(here / "_static/newtons_cradle.mp4")
# plt.show()
