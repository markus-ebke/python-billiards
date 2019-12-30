#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Description of unmovable obstacles in the billiard world."""
import numpy as np

from .physics import elastic_collision, time_of_impact

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


class Obstacle(object):  # pragma: no cover
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

    def plot(self, ax, **kwargs):
        """Draw the obstacle onto the given matplotlib axes.

        Args:
            ax: Axes to draw the obstacle on.
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
        return time_of_impact(
            self.center, (0, 0), self.radius, pos, vel, radius
        )

    def collide(self, pos, vel, radius):
        """Calculate the velocity of a ball after colliding with the disk."""
        vel1, vel2 = elastic_collision(self.center, (0, 0), 1, pos, vel, 0)
        return vel2

    def plot(self, ax, **kwargs):
        """Draw the disk onto the given matplotlib axes."""
        patch = mpl.patches.Circle(self.center, self.radius, **kwargs)
        ax.add_patch(patch)

    def model(self):
        """Vertices, indices and drawing mode for OpenGL drawing the disk."""
        vertices, indices = circle_model(self.radius)
        vertices += self.center
        return (vertices, indices, gl.GL_LINES)
