#!/usr/bin/env python3
"""Sinai billiard (aka Lorentz gas)

The billiard table is a square where a disk in the center was removed.
The billiard balls are point particles that don't collide with each other.
"""

import matplotlib.pyplot as plt
import numpy as np

import billiards

MODE = ["animate", "interact"][0]

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

# particles start from almost the same point, moving with the same velocity
for i in range(num_balls):
    bld.add_ball((-1, 0.01 * 0.98**i), (1, 0), radius=0)

# scale velocity to slow down particles
# bld.balls_velocity *= 1 / 2
# bld.recompute_toi()  # call this method after modifying position or velocity

# visualize the simulation
if MODE == "animate":
    import billiards.visualize_matplotlib as visualize

    anim, fig, ax = visualize.animate(
        bld, 15.0, figsize=(6, 6), arrow_size=0, particle_marker="."
    )
    # anim.save("sinai_billiard.mp4")
    plt.show()
elif MODE == "interact":
    import billiards.visualize_pyglet as visualize

    visualize.interact(bld, camera_zoom=0.25)
else:
    raise ValueError(f"MODE must be 'animate' or 'interact', not {MODE}")
