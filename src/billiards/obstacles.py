#!/usr/bin/env python3
"""Static obstacles on the billiard table.

You can import the obstacles from the top-level module::

    from billiard import Disk, InfiniteWall

"""
import numpy as np

from .physics import INF, elastic_collision, time_of_impact

try:
    import matplotlib as mpl
    from pyglet import gl
except ImportError:  # pragma: no cover
    has_visualize = False
else:
    has_visualize = True


def circle_model(radius, num_points=32):
    """Vertices and order in which to draw lines for a circle.

    Args:
        radius: Radius of the circle.
        num_points: Number of vertices of the circle.

    Returns:
        np.ndarray: Position of the vertices in a Nx2-shaped array.
        list: Indicies indicating the start and endpoints of lines that will
        form the circle, has langth 2N.

    """
    # vertices on the circle
    angles = np.linspace(0, 2 * np.pi, num_points, endpoint=False)
    xy = (np.cos(angles), np.sin(angles))
    vertices = radius * np.stack(xy, axis=1)

    # indices for drawing lines
    indices = []
    for i in range(num_points):
        indices.extend([i, i + 1])
    indices[-1] = 0

    return vertices, indices


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

        Return:
            float: Time until impact the given ball with this obstacle.
            float("inf") if there is no collision.

        """
        raise NotImplementedError("subclasses should implement this!")

    def collide(self, pos, vel, radius):
        """Calculate the velocity of a ball after colliding with this obstacle.

        Args:
            pos: Center of the ball.
            vel: Velocity of the ball.
            radius: Ball radius.

        Return:
            np.ndarry: Velocity after impact.

        """
        raise NotImplementedError("subclasses should implement this!")

    def plot(self, ax, color, **kwargs):
        """Draw the obstacle onto the given matplotlib axes.

        Args:
            ax: Axes to draw the obstacle on.
            color: Color of the obstacle.
            **kwargs: Keyword arguments for plot.

        """
        if not has_visualize:
            raise RuntimeError("can't use plot, matplotlib is not available")

        raise NotImplementedError("subclasses should implement this!")

    def model(self):
        """Vertices, indices and drawing mode for OpenGL drawing this obstacle.

        The vertices, indices and mode are used for drawing of indexed vertex
        lists created from a pyglet.graphics.Batch (the vertex array will be
        flattened later).

        Args:
            ax: Axes to draw the obstacle on.
            **kwargs: Keyword arguments for plot.

        Returns:
            np.ndarray: A Nx2-array of vertex positions.
            list: Indices for the above array of length 2N.
            mode: OpenGL drawing mode.

        """
        if not has_visualize:
            raise RuntimeError("can't use model, pyglet is not available")

        raise NotImplementedError("subclasses should implement this!")


class Disk(Obstacle):
    """A circluar obstacle where balls are not allowed on the inside."""

    def __init__(self, center, radius):
        """Create a circular obstacle with the given center and radius."""
        self.center = np.asarray(center)
        self.radius = radius

    def calc_toi(self, pos, vel, radius):
        """Calculate the velocity of a ball after colliding with the disk."""
        return time_of_impact(self.center, (0, 0), self.radius, pos, vel, radius)

    def collide(self, pos, vel, radius):
        """Calculate the velocity of a ball after colliding with the disk."""
        vel1, vel2 = elastic_collision(self.center, (0, 0), 1, pos, vel, 0)
        return vel2

    def plot(self, ax, color, **kwargs):
        """Draw the disk onto the given matplotlib axes."""
        patch = mpl.patches.Circle(self.center, self.radius, facecolor=color, **kwargs)
        ax.add_patch(patch)

    def model(self):  # pragma: no cover
        """Vertices, indices and drawing mode for OpenGL drawing the disk."""
        vertices, indices = circle_model(self.radius)
        vertices += self.center
        return (vertices, indices, gl.GL_LINES)


class InfiniteWall(Obstacle):
    """An infinite wall where balls can collide only from one side."""

    def __init__(self, start_point, end_point, inside="left"):
        """Create an infinite wall through two points.

        The inside of the billiard is on the left (or the right) going from
        start along the line to end.

        Args:
            start_point: x and y coordinates of the lines starting point.
            end_point: x and y of the end point.
            inside: Either "left" or "right" of the line, defaults to "left".

        """
        self.start_point = np.asarray(start_point)
        self.end_point = np.asarray(end_point)

        dx, dy = self.end_point - self.start_point
        if dx == 0.0 and dy == 0.0:
            raise ValueError("this is not a line")

        # normal = vector perpendicular to the wall, used for collision
        self._normal = np.asarray([-dy, dx])  # normal on the left
        self._normal = self._normal / np.linalg.norm(self._normal)

        if inside == "right":
            self._normal *= -1  # switch normal to the other side
        elif not inside == "left":
            # if inside is not "right", then it MUST be "left"
            msg = 'inside must be "left" or "right", not {}'
            raise ValueError(msg.format(inside))

    def calc_toi(self, pos, vel, radius):
        """Calculate the velocity of a ball after colliding with the wall."""
        # headway: speed towards the wall, is positive if the ball moves from
        # inside to outside (i.e. on a collision course)
        headway = -np.dot(vel, self._normal)
        if headway <= 0:
            # ball does not get closer to the wall, no collision
            return INF

        # size of the gap between the perimeter of the ball and the wall, is
        # negative if the ball is not completely on the inside
        dist = np.dot(pos - self.start_point, self._normal)
        gap = dist - radius

        t = gap / headway  # time of impact: size of gap / speed of closing
        if t < -1e-10:
            # If t is negative, then the ball overlaps with the wall. This
            # doesn't count as an impact, but if t is close to zero, then a
            # collision might have happened and we miss it just because of
            # rounding errors
            return INF
        else:
            return t

    def collide(self, pos, vel, radius):
        """Calculate the velocity of a ball after colliding with the wall."""
        headway = -np.dot(vel, self._normal)
        assert headway > 0  # if the ball is colliding, it can't move away

        bla = 2 * (headway * self._normal)

        return vel + bla

    def plot(self, ax, color, **kwargs):
        """Draw the wall onto the given matplotlib axes."""
        ax.axline(self.start_point, self.end_point, color=color, **kwargs)

    def model(self):  # pragma: no cover
        """Vertices, indices and drawing mode for OpenGL drawing the wall."""
        vertices = np.asarray([self.start_point, self.end_point])
        indices = [0, 1]
        return (vertices, indices, gl.GL_LINES)
