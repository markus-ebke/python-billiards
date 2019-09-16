# -*- coding: utf-8 -*-
"""Main code for billiard simulation."""
import numpy as np


class Simulation(object):
    """The simulation object represent a billiard world.

    Attributes:
        time: Current simulation time.
        num: Number of simulated balls.
        balls_position: List of 2D position of the balls' centers.
        balls_velocity: List of 2D velocities of the balls.

    """

    def __init__(self):
        """Create an empty world."""
        self.time = 0
        self.num = 0

        self.balls_position = np.empty(shape=(0, 2), dtype=np.float64)
        self.balls_velocity = np.empty(shape=(0, 2), dtype=np.float64)

    def add_ball(self, pos, vel):
        """Add a ball at the given position with the given velocity.

        Args:
            pos: A 2D vector that represents the center of the ball.
            vel: A 2D vector that represents the velocity of the ball.

        Returns:
            index: List-index where the balls' information is stored.

        """
        self.balls_position = np.append(self.balls_position, [pos], axis=0)
        self.balls_velocity = np.append(self.balls_velocity, [vel], axis=0)

        self.num = self.balls_position.shape[0]
        idx = self.num - 1  # last added ball is at the end
        return idx

    def step(self, dt):
        """Advance the simulation by the given timestep.

        Args:
            dt: Size of the timestep.

        """
        self._move(dt)
        self.time += dt

    def _move(self, dt):
        # just update position, no collision handling here
        self.balls_position += self.balls_velocity * dt
