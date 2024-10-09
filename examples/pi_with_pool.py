#!/usr/bin/env python3
"""An implementation of G. Galperin's billiard to estimate π to any accuracy

The system consists of a fixed vertical wall (here at x = 0) and two balls (here with
x > 0). The middle ball has mass = 1 and does not move, the ball to the right has
mass = 100**n and moves to the left (towards the wall). The lighter ball will bounce
back and forth between the wall and the heavier ball, slowly redirecting the momentum of
the heavier ball in the opposite direction. The total number of collisions, after which
both balls will escape to the right and never touch again, is surprisingly equal to the
first n + 1 digits of π.

Reference:
Gregory Galperin, "Playing pool with π (the number π from a billiard point of view)",
Regular and Chaotic Dynamics, 2003, 8 (4), 375-394
"""

from math import isinf, pi

import matplotlib.pyplot as plt

import billiards
import billiards.visualize_matplotlib as visualize

digits = 6  # number of digits of pi

# setup the billiard table: Wall -- mass -<- MASS
obstacles = [billiards.obstacles.InfiniteWall((0, -1), (0, 1), exterior="right")]
bld = billiards.Billiard(obstacles)
bld.add_ball((3, 0), (0, 0), radius=0.2)
bld.add_ball((6, 0), (-1, 0), radius=1, mass=100 ** (digits - 1))

# simulate until there are no more collisions and print the total number of collisions
total_collisions = 0
while not isinf(bld.next_collision[0]):
    num_collisions = sum(bld.evolve(bld.time + 1))
    print(f"From t = {bld.time - 1:4} to t = {bld.time:4}: {num_collisions} collisions")
    total_collisions += num_collisions

print(f"Total number of collisions: {total_collisions}")
print(f"Value of pi:                {pi}")

# reset billiard
bld = billiards.Billiard(obstacles)
bld.add_ball((3, 0), (0, 0), radius=0.2)
bld.add_ball((6, 0), (-1, 0), radius=1, mass=100 ** (digits - 1))

# animate the simulation
anim = visualize.animate(bld, end_time=16, fps=60)
anim._fig.set_size_inches((10, 5))
# anim.save("pi_with_pool.mp4")
plt.show()
