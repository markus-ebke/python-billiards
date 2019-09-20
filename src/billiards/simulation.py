# -*- coding: utf-8 -*-
"""Main code for billiard simulation."""
from math import sqrt

import numpy as np

INF = float("inf")


def time_of_impact(pos1, vel1, radius1, pos2, vel2, radius2):
    """Calculate the time of impact of two moving balls.

    Args:
        pos1: Center of the first ball.
        vel1: Velocity of the first ball.
        radius1: Radius of the first ball.
        pos2: Center of the second ball.
        vel2: Velocity of the second ball.
        radius2: Radius of the second ball.

    Return:
        Non-negative time of impact, is infinite if there is no impact

    """
    # switch to coordinate system of ball 1
    pos_diff = np.subtract(pos2, pos1)
    vel_diff = np.subtract(vel2, vel1)

    pos_dot_vel = np.dot(pos_diff, vel_diff)
    if pos_dot_vel >= 0:
        # balls are moving apart, no impact
        return INF
    else:
        pos_sqrd = np.dot(pos_diff, pos_diff)

        dist_sqrd = pos_sqrd - (radius1 + radius2) ** 2
        if dist_sqrd < 0:
            # one ball is inside the other, but don't count this as an impact
            return INF

        # time of impact is given as the solution of the quadratic equation
        # t^2 + b t + c = 0 with b and c below
        vel_sqrd = np.dot(vel_diff, vel_diff)  # note vel_sqrd != 0
        assert vel_sqrd > 0, vel_sqrd
        b = pos_dot_vel / vel_sqrd  # note b < 0
        assert b < 0, b
        c = dist_sqrd / vel_sqrd  # note c >= 0
        assert c >= 0, c

        discriminant = b ** 2 - c
        if discriminant <= 0:
            # the balls miss
            return INF

        # when writing the solution of the quadratic equation use that
        # c = t1 t2
        t1 = -b + sqrt(discriminant)  # note t1 > 0
        assert t1 > 0, (t1, b, sqrt(discriminant))
        t2 = c / t1  # note t2 >= 0, is zero if c = 0, i.e. balls are touching
        assert t2 >= 0, (t2, c)
        return min(t1, t2)


class Simulation(object):
    """The simulation object represent a billiard world.

    Attributes:
        time: Current simulation time.
        num: Number of simulated balls.
        balls_position: List of 2D position of the balls' centers.
        balls_velocity: List of 2D velocities of the balls.
        balls_radius: List of numbers that represent the radii of the balls.

    """

    def __init__(self):
        """Create an empty world."""
        self.time = 0
        self.num = 0

        self.balls_position = np.empty(shape=(0, 2), dtype=np.float64)
        self.balls_velocity = np.empty(shape=(0, 2), dtype=np.float64)
        self.balls_radius = []

    def add_ball(self, pos, vel, radius=0):
        """Add a ball at the given position with the given velocity.

        Args:
            pos: A 2D vector that represents the center of the ball.
            vel: A 2D vector that represents the velocity of the ball.
            radius (optional): The radius of the added ball.
                Defaults to 0 in which case the ball behaves like a point
                particle.

        Returns:
            List-index where the balls' information is stored.

        """
        self.balls_position = np.append(self.balls_position, [pos], axis=0)
        self.balls_velocity = np.append(self.balls_velocity, [vel], axis=0)
        self.balls_radius.append(radius)

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
