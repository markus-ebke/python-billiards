#!/usr/bin/env python3
"""Sinai billiard (aka Lorentz gas)

The billiard table is a square where a disk in the center was removed.
The billiard balls are point particles that don't collide with each other.
"""

from math import cos, pi, sin

import matplotlib.pyplot as plt
import numpy as np

import billiards
from billiards import visualize

# global settings
disk_radius = 0.5  # radius of the disk in the middle
num_balls = 300  # increase this if your computer can handle it
np.random.seed(0)  # fix random state for reproducibility

# construct the billiard table
obs = [
    billiards.InfiniteWall((-1, -1), (1, -1)),  # bottom side
    billiards.InfiniteWall((1, -1), (1, 1)),  # right side
    billiards.InfiniteWall((1, 1), (-1, 1)),  # top side
    billiards.InfiniteWall((-1, 1), (-1, -1)),  # left side
    billiards.Disk((0, 0), radius=disk_radius),  # disk in the middle
]
bld = billiards.Billiard(obstacles=obs)

# distribute particles uniformly in the square, moving in random directions but
# with the same speed
for _i in range(num_balls):
    pos = np.random.uniform((-1, -1), (1, 1))
    angle = np.random.uniform(0, 2 * pi)
    vel = [cos(angle), sin(angle)]

    bld.add_ball(pos, vel, radius=0)

bld.balls_velocity /= 5  # slow down
bld.recompute_toi()

# start the animation
anim = visualize.animate(bld, end_time=10)
anim._fig.set_size_inches((6, 6))
# anim.save("sinai_billiard.mp4")
plt.show()
