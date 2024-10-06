#!/usr/bin/env python3
"""A cloud of billiard balls collapses, but the balls keep colliding."""

import matplotlib.pyplot as plt
import numpy as np

import billiards
from billiards import visualize

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

# start the animation, but zoom into the origin to see the cloud colliding
anim = visualize.animate(bld, end_time=15)
ax = anim._fig.gca()
ax.set_xlim(-40, 40)
ax.set_ylim(-40, 40)
# anim.save("collapse.mp4")
plt.show()
