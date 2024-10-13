#!/usr/bin/env python3
"""Ideal gas trapped in one corner of a box filled with obstacles."""

import random
from math import cos, pi, sin

import matplotlib.pyplot as plt
import numpy as np

import billiards
import billiards.visualize_matplotlib as visualize

# global settings
num_balls = 200  # increase this if your computer can handle it
random.seed(0)  # fix random state for reproducibility

# setup the billiard table
bounds = [
    billiards.InfiniteWall((-1, -1), (1, -1)),  # bottom side
    billiards.InfiniteWall((1, -1), (1, 1)),  # right side
    billiards.InfiniteWall((1, 1), (-1, 1)),  # top side
    billiards.InfiniteWall((-1, 1), (-1, -1)),  # left side
    # lines for maze
    billiards.LineSegment((-0.3, -1), (-0.3, 0.5)),
    billiards.LineSegment((0.3, 1), (0.3, -0.5)),
    billiards.LineSegment((-0.2, -0.4), (0.2, 0.4)),
    billiards.LineSegment((-0.2, 0.4), (0.2, -0.4)),
]
bld = billiards.Billiard(obstacles=bounds)

# distribute particles uniformly in the square, moving in random directions but
# with the same speed
np.random.seed(1)
for _i in range(num_balls):
    pos = np.random.uniform((-0.98, -0.98), (-0.32, -0.32))
    angle = np.random.uniform(0, 2 * pi)
    vel = np.asarray([cos(angle), sin(angle)]) / 2

    bld.add_ball(pos, vel, radius=0.02)

# show a simulation of the first 10 seconds
anim, fig, ax = visualize.animate(bld, end_time=10, arrow_size=0, figsize=(7, 7))
# note: bld.time == 10.0
# anim.save("maze.mp4")
plt.show()
