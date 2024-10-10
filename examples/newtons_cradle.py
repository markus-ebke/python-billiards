#!/usr/bin/env python3
"""Newton's cradle

A ball strikes the end of a straight row of stationary balls and, through
conservation of momentum and energy (elastic collision), only the at the other
end starts moving.
"""

import matplotlib.pyplot as plt

import billiards
import billiards.visualize_matplotlib as visualize

num_balls = 5

# setup the billiard table
left, right = -4, 2 * num_balls + 2
obs = [
    billiards.InfiniteWall((left, -2), (left, 2), exterior="right"),
    billiards.InfiniteWall((right, -2), (right, 2)),
]
bld = billiards.Billiard(obstacles=obs)

# add the balls
bld.add_ball((-3, 0), (3, 0), 1)
for i in range(1, num_balls):
    bld.add_ball((2 * i, 0), (0, 0), radius=1)

# start the animation
anim, fig, ax = visualize.animate(bld, end_time=3 * 4)  # period: 4
plt.show()
