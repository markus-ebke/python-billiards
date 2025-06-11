"""Static obstacles on the billiard table.

You can import the obstacles from the top-level module::

    from billiard import Disk, InfiniteWall
"""

from math import sqrt

import numpy as np

from .physics import (
    elastic_collision,
    toi_args_ball_line_onesided,
    toi_args_ball_segment_onesided,
    toi_args_ball_segment_twosided,
    toi_ball_circle,
    toi_ball_disk,
    toi_ball_disk_exterior,
)


class Obstacle:  # pragma: no cover
    """Obstacle base class.

    Subclasses must implement the `detect_collision` and `resolve_collision`
    methods.
    """

    def detect_collision(self, pos, vel, radius):
        """Calculate the time of impact of a ball with this obstacle.

        Args:
            pos: Center of the ball.
            vel: Velocity of the ball.
            radius: Ball radius.

        Returns:
            A tuple ``(t, args)``, where ``t`` (a float) is the time until
            the ball collides with this obstacle. If there is no collision
            in the present or the future, then ``t`` is infinite. The tuple
            ``args`` contains optional arguments for the `resolve_collision`
            method. These arguments will be unpacked. In particular,
            ``args`` is an empty tuple if the resolve method needs no
            optional arguments.
        """
        raise NotImplementedError("Subclasses should implement this!")

    def resolve_collision(self, pos, vel, radius, *args):
        """Calculate the position and velocity of a ball after the collision.

        The adjusted position is the location of the ball when it touches
        the obstacle. The velocity after an elastic collision is::

            vel - 2 * normal.dot(vel) * normal

        where ``normal`` is a unit vector perpendicular to the boundary
        of the obstacle at the location where the ball touches. (The normal
        points away from the obstacle.)

        Args:
            pos: Center of the ball at the moment of collision.
            vel: Velocity of the ball before the impact.
            radius: Ball radius.
            *args: Optional arguments for more collision info.

        Returns:
            A tuple ``(pos_new, vel_new)``, where ``pos_new`` is the
            corrected position so that the ball touches the boundary of
            the obstacle and ``vel_new`` is the velocity of the ball
            after the impact. Both entries are numpy arrays of the form
            np.ndarray(shape=(2,), dtype=np.float64).
        """
        # To compute pos_new, compute
        # - the distance (gap) between the ball and the obstacle, and
        # - the normal of the obstacle boundary at the point closest to
        #   the ball,
        # then set pos_new = pos - (gap / normal.dot(vel)) * vel

        # For the velocity, compute
        # - the normal at the point where the ball touches,
        # then set vel_new = vel - 2 * normal.dot(vel) * normal
        raise NotImplementedError("Subclasses should implement this!")


class Disk(Obstacle):
    """A circular obstacle where balls are not allowed on the inside or the outside.

    To create a circular hole where balls are not allowed on the outside
    use ``blocked = "outside"`` when creating the obstacle.
    """

    def __init__(self, center, radius, blocked="inside"):
        """Create a circular obstacle with the given center and radius."""
        self.center = np.asarray(center)
        self.radius = float(radius)

        if blocked not in {"inside", "outside"}:
            raise ValueError("'blocked' must be either 'inside' or 'outside'")
        self.blocked = blocked

    def detect_collision(self, pos, vel, radius):
        """Calculate the time of impact of a ball with the disk."""
        if self.blocked == "inside":
            t = toi_ball_disk(pos, vel, radius, self.center, self.radius)
        else:
            t = toi_ball_disk_exterior(pos, vel, radius, self.center, self.radius)
        return t, ()

    def resolve_collision(self, pos, vel, radius, *args):
        """Calculate the position and velocity of a ball after the collision."""
        pos, vel = np.asarray(pos), np.asarray(vel)

        # Compute the size of the gap between the ball and the obstacle
        dpos = np.subtract(pos, self.center)
        dist = sqrt(dpos.dot(dpos))
        if self.blocked == "inside":
            gap = dist - self.radius - radius
        else:
            assert self.blocked == "outside", self.blocked
            gap = dist - self.radius + radius

        # Compute position such that the ball touches the obstacle,
        # i.e. pos - (gap / normal.dot(vel)) * vel
        # with normal = dpos / dist
        assert dpos.dot(vel) != 0.0  # ball should not move parallel to the obstacle
        pos_new = pos - (gap * dist / dpos.dot(vel)) * vel

        # Compute the change in velocity (normal = dpos / |dpos|)
        dpos = np.subtract(pos_new, self.center)
        vel_new = vel - 2 * dpos.dot(vel) / dpos.dot(dpos) * dpos

        return pos_new, vel_new


class Circle(Obstacle):
    """A circular obstacle where balls can collide from the outside or the inside."""

    def __init__(self, center, radius):
        """Create a circular obstacle with the given center and radius."""
        self.center = np.asarray(center)
        self.radius = float(radius)

    def detect_collision(self, pos, vel, radius):
        """Calculate the time of impact of a ball with the circle."""
        t = toi_ball_circle(pos, vel, radius, self.center, self.radius)
        return t, ()

    def resolve_collision(self, pos, vel, radius, *args):
        """Calculate the position and velocity of a ball after the collision."""
        pos, vel = np.asarray(pos), np.asarray(vel)

        # Compute the size of the gap between the ball and the obstacle
        dpos = np.subtract(pos, self.center)
        dist = sqrt(dpos.dot(dpos))
        if dist > self.radius:
            gap = dist - self.radius - radius
        else:
            gap = dist - self.radius + radius

        # Compute position such that the ball touches the obstacle,
        # i.e. pos - (gap / normal.dot(vel)) * vel
        # with normal = dpos / dist
        assert dpos.dot(vel) != 0.0  # ball should not move parallel to the obstacle
        pos_new = pos - (gap * dist / dpos.dot(vel)) * vel

        # Compute the change in velocity (normal = dpos / norm(dpos))
        dpos = np.subtract(pos_new, self.center)
        vel_new = vel - 2 * dpos.dot(vel) / dpos.dot(dpos) * dpos

        return pos_new, vel_new


class InfiniteWall(Obstacle):
    """An infinite wall where balls can collide only from one side."""

    def __init__(self, start_point, end_point, blocked="right"):
        """Create an infinite wall through two points.

        Going from the starting point to the end, the inside of the billiard is on the
        side indicated by the ``blocked`` argument, i.e. balls coming from the exterior
        side will be reflected at the wall, balls that cross the wall from the blocked
        side to the outside will not be reflected.

        Args:
            start_point: x and y coordinates of the lines starting point.
            end_point: x and y of the end point.
            blocked (optional): Either "left" or "right" of the line, defaults to
                "right".
        """
        self.start_point = np.asarray(start_point)
        self.end_point = np.asarray(end_point)

        dx, dy = self.end_point - self.start_point
        if dx == 0.0 and dy == 0.0:
            raise ValueError("start and end are the same point, this is not a line")

        # The normal vector is perpendicular to the wall and points towards the allowed
        # area (so that normal.dot(pos) is the signed distance to the wall)
        if blocked == "right":
            self._normal = np.asarray([-dy, dx])
        elif blocked == "left":
            self._normal = np.asarray([dy, -dx])
        else:
            raise ValueError(f'blocked must be "left" or "right", not {blocked}')
        self._normal = self._normal / np.linalg.norm(self._normal)

    def detect_collision(self, pos, vel, radius):
        """Calculate the time of impact of a ball with the wall."""
        return toi_args_ball_line_onesided(
            pos, vel, radius, self.start_point, self._normal
        )

    def resolve_collision(self, pos, vel, radius, vel_normal):
        """Calculate the velocity of a ball after colliding with the wall."""
        pos, vel = np.asarray(pos), np.asarray(vel)
        assert vel_normal < 0  # if the ball is colliding, it shouldn't move away

        # Compute the size of the gap between the ball and the obstacle
        dpos = np.subtract(pos, self.start_point)
        gap = self._normal.dot(dpos) - radius

        # Compute position such that the ball touches the obstacle,
        # i.e. pos - (gap / normal.dot(vel)) * vel
        pos_new = pos - gap / vel_normal * vel

        # Compute the change in velocity (vel_normal = vel.dot(normal))
        vel_new = vel - 2 * vel_normal * self._normal

        return pos_new, vel_new


class LineSegment(Obstacle):
    """A line segment with collisions from one or both sides."""

    def __init__(self, start_point, end_point, blocked="none"):
        """Create a line segment between two points.

        Args:
            start_point: Starting point of the line segment.
            end_point: Endpoint of the line segment.
            blocked (optional): Either "none", "left" or "right". If "left" or
                "right", then balls can collide only from one side.
                If "none", then balls can collide from both sides.
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

        # The normal vector is perpendicular to the line and points towards the allowed
        # area (so that normal.dot(pos) is the signed distance to the line)
        if blocked in {"right", "none"}:
            self._normal = np.array([-direction[1], direction[0]]) / sqrt(length_sqrd)
        elif blocked == "left":
            self._normal = np.array([direction[1], -direction[0]]) / sqrt(length_sqrd)
        else:
            raise ValueError(
                f'blocked must be "none", "left" or "right", not {blocked}'
            )
        self.blocked = blocked

    def detect_collision(self, pos, vel, radius):
        """Calculate the time of impact of a ball with the line segment."""
        if self.blocked == "none":
            return toi_args_ball_segment_twosided(
                pos,
                vel,
                radius,
                self.start_point,
                self.end_point,
                self._normal,
                self._covector,
            )
        else:
            return toi_args_ball_segment_onesided(
                pos,
                vel,
                radius,
                self.start_point,
                self.end_point,
                self._normal,
                self._covector,
            )

    def resolve_collision(self, pos, vel, radius, vel_normal, u):
        """Calculate the velocity of a ball after colliding with the line segment."""
        pos, vel = np.asarray(pos), np.asarray(vel)
        assert 0 <= u <= 1, u

        # u == 0 or u == 1: collision with one of the end points of the line,
        # 0 < u < 1: collision with the line part of the segment
        if u == 0:
            # Compute the size of the gap between the ball and the obstacle
            dpos = np.subtract(pos, self.start_point)
            dist = sqrt(dpos.dot(dpos))
            gap = dist - radius

            # Compute position such that the ball touches the obstacle,
            # i.e. pos - (gap / normal.dot(vel)) * vel
            # with normal = dpos / dist
            assert dpos.dot(vel) != 0.0  # ball should not move parallel to the obstacle
            pos_new = pos - (gap * dist / dpos.dot(vel)) * vel

            # Compute the change in velocity
            vel_new = elastic_collision(self.start_point, (0, 0), 1, pos_new, vel, 0)[1]
        elif u == 1:
            # Compute the size of the gap between the ball and the obstacle
            dpos = np.subtract(pos, self.end_point)
            dist = sqrt(dpos.dot(dpos))
            gap = dist - radius

            # Compute position such that the ball touches the obstacle,
            # i.e. pos - (gap / normal.dot(vel)) * vel
            # with normal = dpos / dist
            assert dpos.dot(vel) != 0.0  # ball should not move parallel to the obstacle
            pos_new = pos - (gap * dist / dpos.dot(vel)) * vel

            # Compute the change in velocity
            vel_new = elastic_collision(self.end_point, (0, 0), 1, pos_new, vel, 0)[1]
        else:
            assert vel_normal != 0.0  # ball should not move parallel to the obstacle

            # Compute the size of the gap between the ball and the obstacle
            dpos = np.subtract(pos, self.start_point)
            gap = abs(self._normal.dot(dpos)) - radius

            # Compute position such that the ball touches the obstacle,
            # i.e. pos - (gap / normal.dot(vel)) * vel
            pos_new = pos - gap / vel_normal * vel

            # Compute the change in velocity (vel_normal = vel.dot(normal))
            vel_new = vel - 2 * vel_normal * self._normal

        return pos_new, vel_new
