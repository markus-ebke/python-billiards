#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

import billiards

print(os.getcwd())  # print current working directory


# Quickstart
bil = billiards.Billiard()

fig_name = "_static/quickstart_1.svg"
bil.add_ball((2, 0), (4, 0), radius=1)
bil.evolve(end_time=10.0)
fig = billiards.visualize.plot(bil, show=False)
fig.savefig(fig_name)
print(fig_name)

fig2_name = "_static/quickstart_2.svg"
bil.add_ball((50, 18), (0, -9), radius=1, mass=2)
bil.evolve(14.0)
fig2 = billiards.visualize.plot(bil, show=False)
fig2.savefig(fig2_name)
print(fig2_name)
