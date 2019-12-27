#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

import billiards

print(os.getcwd())

bil = billiards.Billiard()

bil.add_ball((2, 0), (4, 0), radius=1)
bil.evolve(end_time=10.0)
fig = billiards.visualization.plot(bil, show=False)
fig.savefig("_images/quickstart_1.png")

bil.add_ball((50, 18), (0, -9), radius=1, mass=2)
bil.evolve(14.0)
fig2 = billiards.visualization.plot(bil, show=False)
fig2.savefig("_images/quickstart_2.png")
