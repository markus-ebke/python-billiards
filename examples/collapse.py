#!/usr/bin/env python3
"""A cloud of billiard balls collapses, but the balls keep colliding with each other."""

import matplotlib.pyplot as plt
import numpy as np

import billiards

MODE = ["animate", "interact"][0]

# global settings
num_balls = 200  # increase this if your computer can handle it
np.random.seed(0)  # fix random state for reproducibility

# setup an empty billiard table
bld = billiards.Billiard()

# add random balls
for _i in range(num_balls):
    # create ball that moves towards the origin from a random starting point
    pos = np.random.normal(0, scale=1, size=2)  # fuzzy origin
    vel = np.random.normal(0, scale=5, size=2)
    pos -= vel * 10  # go back in time 10 seconds

    # add ball to billiard
    idx = bld.add_ball(pos, vel, radius=1)


# visualize the simulation
if MODE == "animate":
    import billiards.visualize_matplotlib as visualize

    anim, fig, ax = visualize.animate(bld, 15.0)

    # zoom into the origin to see the cloud colliding
    ax.set_xlim(-40, 40)
    ax.set_ylim(-40, 40)

    # anim.save("collapse.mp4")
    plt.show()
elif MODE == "interact":
    import billiards.visualize_pyglet as visualize

    visualize.interact(bld, camera_zoom=1 / 200)
else:
    raise ValueError(f"MODE must be 'animate' or 'interact', not {MODE}")
