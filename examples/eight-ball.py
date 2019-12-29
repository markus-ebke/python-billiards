#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A game of eight-ball (https://en.wikipedia.org/wiki/Eight-ball).

Note that the breakup should be perfect (everything is perfectly placed within
floating point accuracy), but it is not (and I don't know why).
"""
from math import sqrt

import billiards
from billiards import Billiard

# add balls in pyramid
bld = Billiard()
for i in range(5):
    for j in range(i + 1):
        pos = (sqrt(3) * i, 2 * j - i)
        bld.add_ball(pos, vel=(0, 0), radius=1)

# add white ball
bld.add_ball((-10, 0), vel=(3, 0), radius=1)

# start the animation, but correct the view to see the breakup
fig, anim = billiards.visualize.animate(bld, end_time=10)
ax = fig.gca()
ax.set_xlim(-10, 15)
ax.set_ylim(-10, 10)
