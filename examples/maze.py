#!/usr/bin/env python3
"""Ideal gas trapped in one corner of a box filled with obstacles."""

import random
from math import cos, pi, sin

import matplotlib.pyplot as plt
import numpy as np

import billiards

MODE = ["animate", "interact"][0]

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
    billiards.LineSegment((-0.3, -1), (-0.3, 0.5), blocked="none"),
    billiards.LineSegment((0.3, 1), (0.3, -0.5), blocked="none"),
    # first obstacle: "wedge"
    billiards.LineSegment((-0.2, 0.0), (0.0, 0.5), blocked="right"),
    billiards.LineSegment((0.0, 0.5), (0.2, 0.0), blocked="right"),
    # second obstacle: "one-way slit"
    billiards.LineSegment((0.3, -0.3), (0.1, -0.3), blocked="left"),
    billiards.LineSegment((-0.1, -0.3), (-0.3, -0.3), blocked="left"),
    # third obstacle: "disk"
    billiards.Disk((0.65, -0.2), 0.3),
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


# visualize the simulation
if MODE == "animate":
    import billiards.visualize_matplotlib as visualize

    anim, fig, ax = visualize.animate(bld, end_time=10, arrow_size=0, figsize=(7, 7))
    # note: bld.time == 10.0
    # anim.save("maze.mp4")
    plt.show()
elif MODE == "interact":
    import billiards.visualize_pyglet as visualize

    visualize.interact(bld, camera_zoom=0.25)
else:
    raise ValueError(f"MODE must be 'animate' or 'interact', not {MODE}")
