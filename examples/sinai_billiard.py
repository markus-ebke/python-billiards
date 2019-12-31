#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sinai billiard aka Lorentz gas

The billiard table is a unit square where a disk in the center was removed.
The billiard balls are point particles that don't collide with each other.
"""
from math import cos, pi, sin

import numpy as np

import billiards
from billiards import Billiard
from billiards.obstacles import Disk, InfiniteWall

# global settings
disk_radius = 0.5  # radius of the disk in the middle
num_balls = 300  # increase this if your computer can handle it
np.random.seed(0)  # fix random state for reproducibility

# construct the billiard table
obs = [
    InfiniteWall((-1, -1), (1, -1)),  # bottom side
    InfiniteWall((1, -1), (1, 1)),  # right side
    InfiniteWall((1, 1), (-1, 1)),  # top side
    InfiniteWall((-1, 1), (-1, -1)),  # left side
    Disk((0, 0), radius=disk_radius),  # disk in the middle
]
bld = Billiard(obstacles=obs)

# place a few point particles randomly in the square but with uniform speed
for i in range(num_balls):
    pos = np.random.uniform((-1, -1), (1, 1))
    angle = np.random.uniform(0, 2 * pi)
    vel = 0.2 * np.asarray([cos(angle), sin(angle)])

    bld.add_ball(pos, vel, radius=0)

# start the animation
fig, anim = billiards.visualize.animate(bld, end_time=10)
fig.set_size_inches((6, 6))
