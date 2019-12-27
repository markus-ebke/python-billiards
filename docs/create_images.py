#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

import billiards

print(os.getcwd())  # print current working directory


# Quickstart
bil = billiards.Billiard()

fig_name = "_images/quickstart_1.svg"
bil.add_ball((2, 0), (4, 0), radius=1)
bil.evolve(end_time=10.0)
fig = billiards.visualize.plot(bil, show=False)
fig.savefig(fig_name)
print(fig_name)

fig2_name = "_images/quickstart_2.svg"
bil.add_ball((50, 18), (0, -9), radius=1, mass=2)
bil.evolve(14.0)
fig2 = billiards.visualize.plot(bil, show=False)
fig2.savefig(fig2_name)
print(fig2_name)


# Usage: Newton's cradle
sim = billiards.Billiard()

anim_name = "_static/newtons_cradle.mp4"
sim.add_ball((0, 0), (1, 0), 1)
sim.add_ball((3, 0), (0, 0), 1)
sim.add_ball((5.1, 0), (0, 0), 1)
sim.add_ball((7.2, 0), (0, 0), 1)
sim.add_ball((9.3, 0), (0, 0), 1)

anim = billiards.visualize.animate(sim, end_time=5, show=False)
anim.save(anim_name)
print(anim_name)
