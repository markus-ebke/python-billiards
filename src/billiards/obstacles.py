#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np

from .physics import elastic_collision, time_of_impact


class Obstacle(object):
    """Obstacle base class.

    Subclasses must implement the calc_toi and collide methods."""

    def __init__(self):
        pass

    def calc_toi(self, pos, vel, radius):
        """Calculate the time of impact of a ball with this obstacle.

        Args:
            pos: Center of the ball.
            vel: Velocity of the ball.
            radius: Ball radius.

        Return:
            float: Time until impact the given ball with this obstacle.
            float("inf") if there is no collision.

        """
        raise NotImplementedError("Subclasses should implement this!")

    def collide(self, pos, vel, radius):
        """Calculate the velocity of a ball after colliding with this obstacle.

        Args:
            pos: Center of the ball.
            vel: Velocity of the ball.
            radius: Ball radius.

        Return:
            np.ndarry: Velocity after impact

        """
        raise NotImplementedError("Subclasses should implement this!")


class Disk(Obstacle):
    """A circluar obstacle where balls are not allowed on the inside."""

    def __init__(self, center, radius):
        self.center = np.asarray(center)
        self.radius = radius

    def calc_toi(self, pos, vel, radius):
        return time_of_impact(
            self.center, (0, 0), self.radius, pos, vel, radius
        )

    def collide(self, pos, vel, radius):
        vel1, vel2 = elastic_collision(self.center, (0, 0), 1, pos, vel, 0)
        return vel2
