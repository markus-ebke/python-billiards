#!/usr/bin/env python3
"""Ideal gas trapped in a box.

In the beginning, all balls have the same speed. But after many collisions, the
distribution of speeds converges to the (two-dimensional) Maxwell-Boltzmann
distribution.
"""

import random
from math import cos, pi, sin

import matplotlib.pyplot as plt
import numpy as np

import billiards
from billiards import visualize

# global settings
num_balls = 1000  # increase this if your computer can handle it
random.seed(0)  # fix random state for reproducibility

# setup the billiard table
bounds = [
    billiards.InfiniteWall((-1, -1), (1, -1)),  # bottom side
    billiards.InfiniteWall((1, -1), (1, 1)),  # right side
    billiards.InfiniteWall((1, 1), (-1, 1)),  # top side
    billiards.InfiniteWall((-1, 1), (-1, -1)),  # left side
]
bld = billiards.Billiard(obstacles=bounds)

# distribute particles uniformly in the square, moving in random directions but
# with the same speed
for _ in range(num_balls):
    pos = np.random.uniform((-0.99, -0.99), (0.99, 0.99))
    angle = np.random.uniform(0, 2 * pi)
    vel = np.asarray([cos(angle), sin(angle)]) / 5

    bld.add_ball(pos, vel, radius=0.01)

# add a bigger ball to illustrate Brownian motion
# bld.add_ball((0, 0), (0, 0), radius=0.1, mass=10)

# show a simulation of the first 10 seconds
anim = visualize.animate(bld, end_time=10, velocity_arrow_factor=0)
# note: bld.time == 10.0
anim._fig.set_size_inches((7, 7))
# anim.save("ideal_gas.mp4")
plt.show()

# plot histogram of speed distribution and compare with 2-dimensional
# Maxwell–Boltzmann distribution (formula from Wikipedia, n-dimensional case)
speeds = np.linalg.norm(bld.balls_velocity, axis=1)
plt.hist(speeds, bins=20, density=True, edgecolor="white", label="Simulation")
x = np.linspace(0, speeds.max(), num=1000)
beta = pi / (4 * np.mean(speeds) ** 2)  # inverse temperature, m / (2 k_B T)
plt.plot(x, 2 * beta * x * np.exp(-beta * x**2), label="Theory")

# adjust axes and labels
plt.xlim(left=0)
plt.ylim(bottom=0)
plt.title("Maxwell-Boltzmann Distribution")
plt.xlabel("Speed")
plt.ylabel("Frequency")
plt.legend()

# plt.savefig("ideal_gas.png")
plt.show()
