#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np


class Simulation(object):
    def __init__(self):
        self.time = 0

        self.balls_position = np.empty(shape=(0, 2), dtype=np.float64)
        self.balls_velocity = np.empty(shape=(0, 2), dtype=np.float64)

    def add_ball(self, pos, vel):
        self.balls_position = np.append(self.balls_position, [pos], axis=0)
        self.balls_velocity = np.append(self.balls_velocity, [vel], axis=0)

        idx = self.balls_position.shape[0]  # last added ball is at the end
        return idx

    def step(self, dt):
        self._move(dt)
        self.time += dt

    def _move(self, dt):
        # just update position, no collision handling here
        self.balls_position += self.balls_velocity * dt
