#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A cloud of billiard balls collapses, but they keep colliding with each other.

Note that this example uses pyglet for rendering.
"""
import numpy as np

import billiards
from billiards import Billiard

# global settings
num_balls = 200  # increase this if your computer can handle it
np.random.seed(0)  # fixed for deterministic starting conditions

# add random balls
bld = Billiard()
for i in range(num_balls):
    # create ball that moves towards the origin from a random starting point
    pos = np.random.normal(0, scale=1, size=2)  # fuzzy origin
    vel = np.random.normal(0, scale=5, size=2)
    pos -= vel * 10  # go back in time 10 seconds

    # add ball to billiard
    idx = bld.add_ball(pos, vel, radius=1)

# start the simulation
billiards.visualize.interact(bld)
