#!/usr/bin/env python3
"""Static obstacles on the billiard table.

You can import the obstacles from the top-level module::

    from billiard import Disk, InfiniteWall
"""

from math import isinf, sqrt

import numpy as np

from .physics import (
    INF,
    elastic_collision,
    toi_and_param_ball_segment,
    toi_ball_ball,
    toi_ball_point,
)


class Obstacle:  # pragma: no cover
    """Obstacle base class.

    Subclasses must implement the calc_toi and collide methods. Optionally they
    can implement the plot method for visualization with matplotlib.
    """

    def calc_toi(self, pos, vel, radius):
        """Calculate the time of impact of a ball with this obstacle.

        Args:
            pos: Center of the ball.
            vel: Velocity of the ball.
            radius: Ball radius.

        Returns:
            A tuple ``(t, args)``, where ``t`` (a float) is the time until the given
            ball collides with this obstacle. If there is no collision, ``t`` will be
            infinite. The tuple ``args`` contains optional arguments for the collide
            method. These arguments will be unpacked, i.e. if the collide method needs
            no optional arguments then ``args`` should be ``()``.
        """
        raise NotImplementedError("subclasses should implement this!")

    def collide(self, pos, vel, radius, *args):
        """Calculate the velocity of a ball after colliding with this obstacle.

        Args:
            pos: Center of the ball.
            vel: Velocity of the ball.
            radius: Ball radius.
            *args: Optional arguments for more collision info.

        Returns:
            np.ndarray: Velocity after impact.
        """
        raise NotImplementedError("subclasses should implement this!")


class Disk(Obstacle):
    """A circluar obstacle where balls are not allowed on the inside."""

    def __init__(self, center, radius):
        """Create a circular obstacle with the given center and radius."""
        self.center = np.asarray(center)
        self.radius = radius

    def calc_toi(self, pos, vel, radius):
        """Calculate the time of impact of a ball with the disk."""
        return toi_ball_ball(self.center, (0, 0), self.radius, pos, vel, radius), ()

    def collide(self, pos, vel, radius, *args):
        """Calculate the velocity of a ball after colliding with the disk."""
        return elastic_collision(self.center, (0, 0), 1, pos, vel, 0)[1]


class InfiniteWall(Obstacle):
    """An infinite wall where balls can collide only from one side."""

    def __init__(self, start_point, end_point, exterior="left"):
        """Create an infinite wall through two points.

        Going from the starting point to the end, the inside of the billiard is on the
        side indicated by the argument 'exterior', i.e. balls coming from the exterior
        side will be reflected at the wall, balls that cross the wall from the interior
        to the exterior side will not be reflected.

        Args:
            start_point: x and y coordinates of the lines starting point.
            end_point: x and y of the end point.
            exterior: Either "left" or "right" of the line, defaults to "left".
        """
        self.start_point = np.asarray(start_point)
        self.end_point = np.asarray(end_point)

        dx, dy = self.end_point - self.start_point
        if dx == 0.0 and dy == 0.0:
            raise ValueError("this is not a line")

        # normal = vector perpendicular to the wall, used for collision
        self._normal = np.asarray([-dy, dx])  # normal on the left
        self._normal = self._normal / np.linalg.norm(self._normal)

        if exterior == "right":
            self._normal *= -1  # switch normal to the other side
        elif not exterior == "left":
            # if inside is not "right", then it MUST be "left"
            raise ValueError(f'exterior must be "left" or "right", not {exterior}')

    def calc_toi(self, pos, vel, radius):
        """Calculate the time of impact of a ball with the wall."""
        # headway: speed towards the wall, is positive if the ball moves from
        # inside to outside (i.e. on a collision course)
        headway = -np.dot(vel, self._normal)
        if headway <= 0:
            # ball does not get closer to the wall, no collision
            return INF, ()

        # size of the gap between the perimeter of the ball and the wall, is
        # negative if the ball is not completely on the inside
        gap = np.dot(pos - self.start_point, self._normal) - radius

        t = gap / headway  # time of impact: size of gap / speed of closing
        if t < -1e-10:
            # If t is negative, then the ball overlaps with the wall. This
            # doesn't count as an impact, but if t is close to zero, then a
            # collision might have happened and we miss it just because of
            # rounding errors
            return INF, ()
        else:
            return t, (headway,)

    def collide(self, pos, vel, radius, headway):
        """Calculate the velocity of a ball after colliding with the wall."""
        # if headway is None:
        #    headway = -np.dot(vel, self._normal)
        # else:
        #    ref = -np.dot(vel, self._normal)
        #    assert np.linalg.norm(headway - ref) <= 1e-14, (headway, ref)
        assert headway > 0  # if the ball is colliding, it can't move away

        return vel + 2 * (headway * self._normal)


class LineSegment(Obstacle):
    """A line segment with collisions from both sides."""

    def __init__(self, start_point, end_point):
        """Create a line segment between two points.

        Args:
            start_point: Starting point of the line segment.
            end_point: Endpoint of the line segment.
        """
        self.start_point = np.asarray(start_point)
        self.end_point = np.asarray(end_point)
        direction = self.end_point - self.start_point
        length_sqrd = direction.dot(direction)

        if length_sqrd == 0.0:
            raise ValueError("this is not a line")

        # Direction of the line, dividing by the squared length simplifies some
        # calculations in calc_toi
        self._covector = direction / length_sqrd

        # normalized vector perpendicular to the line
        self._normal = np.array([-direction[1], direction[0]]) / sqrt(length_sqrd)

    def calc_toi(self, pos, vel, radius):
        """Calculate the time of impact of a ball with the line segment."""
        t, u = toi_and_param_ball_segment(
            pos, vel, radius, self.start_point, self._covector, self._normal
        )
        if isinf(t):
            if u == 0:
                return toi_ball_point(pos, vel, radius, self.start_point), (u,)
            elif u == 1:
                return toi_ball_point(pos, vel, radius, self.end_point), (u,)

        return t, (u,)

    def collide(self, pos, vel, radius, u):
        """Calculate the velocity of a ball after colliding with the line segment."""
        # dpos = np.subtract(pos, self.start_point)
        # if abs(dpos.dot(dpos) - radius**2) < 1e-14:
        if u == 0:
            return elastic_collision(self.start_point, (0, 0), 1, pos, vel, 0)[1]

        # dpos = np.subtract(pos, self.end_point)
        # if abs(dpos.dot(dpos) - radius**2) < 1e-14:
        elif u == 1:
            return elastic_collision(self.end_point, (0, 0), 1, pos, vel, 0)[1]

        # collision with the line part of the segment
        return vel - 2 * self._normal.dot(vel) * self._normal
