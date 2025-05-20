#!/usr/bin/env python3
"""First shot in a game of pool (note that there is no friction)

Note that the breakup should be perfect (everything is perfectly placed within
floating point accuracy), but it is not (and I don't know why, probably it's
the floating point accuracy).
"""

from math import sqrt

import matplotlib.pyplot as plt

import billiards

MODE = ["animate", "interact"][0]

# setup the billiard table
breadth, length = 112, 224
bounds = [
    billiards.InfiniteWall((0, 0), (length, 0)),  # bottom side
    billiards.InfiniteWall((length, 0), (length, breadth)),  # right side
    billiards.InfiniteWall((length, breadth), (0, breadth)),  # top side
    billiards.InfiniteWall((0, breadth), (0, 0)),  # left side
]
bld = billiards.Billiard(obstacles=bounds)

# arrange the balls in a pyramid shape
radius = 2.85
for i in range(5):
    for j in range(i + 1):
        x = 0.75 * length + radius * sqrt(3) * i
        y = breadth / 2 + radius * (2 * j - i)
        bld.add_ball((x, y), (0, 0), radius)

# add the white ball and give it a push
bld.add_ball((0.25 * length, breadth / 2), (length / 3, 0), radius)

# visualize the simulation
if MODE == "animate":
    import billiards.visualize_matplotlib as visualize

    anim, fig, ax = visualize.animate(bld, 30.0, figsize=(10, 5.5))
    # anim.save("pool_first_shot.mp4")
    plt.show()
elif MODE == "interact":
    import billiards.visualize_pyglet as visualize

    visualize.interact(
        bld, camera_position=(length / 2, breadth / 2), camera_zoom=1 / length
    )
else:
    raise ValueError(f"MODE must be 'animate' or 'interact', not {MODE}")
