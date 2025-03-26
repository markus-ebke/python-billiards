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
    toi_ball_circle,
    toi_ball_disk,
    toi_ball_disk_exterior,
    toi_ball_point,
)


class Obstacle:  # pragma: no cover
    """Obstacle base class.

    Subclasses must implement the ``detect_collision`` and ``resolve_collision``
    methods.
    """

    def detect_collision(self, pos, vel, radius):
        """Calculate the time of impact of a ball with this obstacle.

        Args:
            pos: Center of the ball.
            vel: Velocity of the ball.
            radius: Ball radius.

        Returns:
            A tuple ``(t, args)``, where ``t`` (a float) is the time until the ball
            collides with this obstacle. If there is no collision, ``t`` should be
            infinite. The tuple ``args`` contains optional arguments for the
            ``resolve_collision`` method. These arguments will be unpacked, i.e. if the
            resolve method needs no optional arguments, then ``args`` should be ``()``
            (an empty tuple).
        """
        raise NotImplementedError("Subclasses should implement this!")

    def resolve_collision(self, pos, vel, radius, *args):
        """Calculate the velocity of a ball after colliding with this obstacle.

        Args:
            pos: Center of the ball.
            vel: Velocity of the ball before the impact.
            radius: Ball radius.
            *args: Optional arguments for more collision info.

        Returns:
            The velocity of the ball after the impact as a numpy array of the form
            np.ndarray(shape=(2,), dtype=np.float64).
        """
        raise NotImplementedError("Subclasses should implement this!")


class Disk(Obstacle):
    """A circluar obstacle where balls are not allowed on the inside.

    To create a circular hole where balls are not allowed on the outside
    use ``no_go = "outside"`` when creating the obstacle.
    """

    def __init__(self, center, radius, no_go="inside"):
        """Create a circular obstacle with the given center and radius."""
        self.center = np.asarray(center)
        self.radius = float(radius)

        if no_go not in {"inside", "outside"}:
            raise ValueError("'no_go' must be either 'inside' or 'outside'")
        self.no_go = no_go

    def detect_collision(self, pos, vel, radius):
        """Calculate the time of impact of a ball with the disk."""
        if self.no_go == "inside":
            t = toi_ball_disk(pos, vel, radius, self.center, self.radius)
        else:
            t = toi_ball_disk_exterior(pos, vel, radius, self.center, self.radius)
        return t, ()

    def resolve_collision(self, pos, vel, radius, *args):
        """Calculate the velocity of a ball after colliding with the disk."""
        # Switch to coordinate system of the disk
        dpos = np.subtract(pos, self.center)

        # Compute the change in velocity (normal = dpos / |dpos|)
        return vel - 2 * (dpos.dot(vel) * dpos) / dpos.dot(dpos)


class Circle(Obstacle):
    """A circluar obstacle where balls can collide from the outside or the inside."""

    def __init__(self, center, radius):
        """Create a circular obstacle with the given center and radius."""
        self.center = np.asarray(center)
        self.radius = float(radius)

    def detect_collision(self, pos, vel, radius):
        """Calculate the time of impact of a ball with the circle."""
        t = toi_ball_circle(pos, vel, radius, self.center, self.radius)
        return t, ()

    def resolve_collision(self, pos, vel, radius, *args):
        """Calculate the velocity of a ball after colliding with the circle."""
        # Switch to coordinate system of circle
        dpos = np.subtract(pos, self.center)

        # Compute the change in velocity (normal = dpos / norm(dpos))
        return vel - 2 * dpos.dot(vel) * dpos / dpos.dot(dpos)


class InfiniteWall(Obstacle):
    """An infinite wall where balls can collide only from one side."""

    def __init__(self, start_point, end_point, no_go="right"):
        """Create an infinite wall through two points.

        Going from the starting point to the end, the inside of the billiard is on the
        side indicated by the ``no_go`` argument, i.e. balls coming from the exterior
        side will be reflected at the wall, balls that cross the wall from the no-go
        side to the outside will not be reflected.

        Args:
            start_point: x and y coordinates of the lines starting point.
            end_point: x and y of the end point.
            no_go: Either "left" or "right" of the line, defaults to "right".
        """
        self.start_point = np.asarray(start_point)
        self.end_point = np.asarray(end_point)

        dx, dy = self.end_point - self.start_point
        if dx == 0.0 and dy == 0.0:
            raise ValueError("this is not a line")

        # normal = vector perpendicular to the wall, used for collision
        self._normal = np.asarray([-dy, dx])  # normal on the left
        self._normal = self._normal / np.linalg.norm(self._normal)

        if no_go == "left":
            self._normal *= -1  # switch normal to the other side
        elif not no_go == "right":
            # if inside is not "left", then it MUST be "right"
            raise ValueError(f'no_go must be "left" or "right", not {no_go}')

    def detect_collision(self, pos, vel, radius):
        """Calculate the time of impact of a ball with the wall."""
        # vel_normal: speed away from the wall, is positive if the ball
        # moves away and negative if it moves toward the no-go area
        vel_normal = self._normal.dot(vel)
        if vel_normal >= 0:
            # No collision if the ball doesn't move towards the wall
            return INF, (vel_normal,)

        # Compute the relative position between the ball and the wall
        dpos = np.subtract(pos, self.start_point)

        # The ball collides with the wall when the gap between ball and
        # wall becomes equal to the ball radius:
        # <normal, dpos + t * vel> == radius
        # Rearranged: <normal, dpos> - radius == - t * <normal, vel>,
        # note that <normal, dpos> - radius is the size of the gap and
        # <normal, vel> is the speed of closing the gap.
        t = -(self._normal.dot(dpos) - radius) / vel_normal

        t_eps = 0.0  # t negative => ball overlaps with wall => no collision
        return t if t >= t_eps else INF, (vel_normal,)

    def resolve_collision(self, pos, vel, radius, vel_normal):
        """Calculate the velocity of a ball after colliding with the wall."""
        assert vel_normal < 0  # if the ball is colliding, it shouldn't move away
        return vel - 2 * vel_normal * self._normal


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
        # calculations in detect_collision
        self._covector = direction / length_sqrd

        # normalized vector perpendicular to the line
        self._normal = np.array([-direction[1], direction[0]]) / sqrt(length_sqrd)

    def detect_collision(self, pos, vel, radius):
        """Calculate the time of impact of a ball with the line segment."""
        t_eps = 1e-10 if radius == 0 else -1e-10  # point particles need a buffer zone
        t, u = toi_and_param_ball_segment(
            pos, vel, radius, self.start_point, self._covector, self._normal, t_eps
        )
        if isinf(t):
            if u == 0:
                return toi_ball_point(pos, vel, radius, self.start_point), (u,)
            elif u == 1:
                return toi_ball_point(pos, vel, radius, self.end_point), (u,)

        return t, (u,)

    def resolve_collision(self, pos, vel, radius, u):
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
