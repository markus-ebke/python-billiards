#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A game of eight-ball (https://en.wikipedia.org/wiki/Eight-ball).

Note that the breakup should be perfect (everything is perfectly placed within
floating point accuracy), but it is not (and I don't know why, probably it's
the floating point accuracy).
"""
from math import sqrt

import billiards
from billiards import Billiard
from billiards.obstacles import InfiniteWall

width = 112
length = 224
radius = 5.715 / 2

# setup the billiard table
obs = [
    InfiniteWall((0, 0), (length, 0)),  # bottom side
    InfiniteWall((length, 0), (length, width)),  # right side
    InfiniteWall((length, width), (0, width)),  # top side
    InfiniteWall((0, width), (0, 0)),  # left side
]
bld = Billiard(obstacles=obs)

# add the balls in pyramid
px = length * 3 / 4
py = width / 2
for i in range(5):
    for j in range(i + 1):
        x = px + radius * sqrt(3) * i
        y = py + radius * (2 * j - i)
        bld.add_ball((x, y), (0, 0), radius)

bld.add_ball((length / 4, py), (length / 3, 0), radius)  # white ball

# start the animation
fig, anim = billiards.visualize.animate(bld, end_time=10)
fig.set_size_inches((10, 5.5))
