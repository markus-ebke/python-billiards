#!/usr/bin/env python3
"""First shot in a game of pool (note that there is no friction)

Note that the breakup should be perfect (everything is perfectly placed within
floating point accuracy), but it is not (and I don't know why, probably it's
the floating point accuracy).
"""

from math import sqrt

import matplotlib.pyplot as plt

import billiards
import billiards.visualize_matplotlib as visualize

# setup the billiard table
width, length = 112, 224
bounds = [
    billiards.InfiniteWall((0, 0), (length, 0)),  # bottom side
    billiards.InfiniteWall((length, 0), (length, width)),  # right side
    billiards.InfiniteWall((length, width), (0, width)),  # top side
    billiards.InfiniteWall((0, width), (0, 0)),  # left side
]
bld = billiards.Billiard(obstacles=bounds)

# arrange the balls in a pyramid shape
radius = 2.85
for i in range(5):
    for j in range(i + 1):
        x = 0.75 * length + radius * sqrt(3) * i
        y = width / 2 + radius * (2 * j - i)
        bld.add_ball((x, y), (0, 0), radius)

# add the white ball and give it a push
bld.add_ball((0.25 * length, width / 2), (length / 3, 0), radius)

# start the animation
anim = visualize.animate(bld, end_time=30)
anim._fig.set_size_inches((10, 5.5))
# anim.save("pool_first_shot.mp4")
plt.show()
