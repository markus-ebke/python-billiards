# -*- coding: utf-8 -*-
"""Visualize a billiard using Matplotlib."""
import numpy as np

try:
    from matplotlib.artist import allow_rasterization
    import matplotlib.transforms as transforms
    from matplotlib.path import Path
    from matplotlib.collections import Collection
    from matplotlib.animation import FuncAnimation
    import matplotlib.pyplot as plt
except ImportError as ex:  # pragma: no cover
    print("Cannot use billiards.visualization, matplotlib is not installed.")
    raise ex


class BallCollection(Collection):
    """Balls in data coordinates, simplified from EllipseCollection."""

    def __init__(self, radius, **kwargs):
        """Create balls from given parameters."""
        Collection.__init__(self, **kwargs)
        self.radius = np.asarray(radius)
        self.set_transform(transforms.IdentityTransform())
        self._paths = [Path.unit_circle()]

    def _set_transforms(self):
        self._transforms = np.zeros((len(self.radius), 3, 3))
        self._transforms[:, 0, 0] = self.radius
        self._transforms[:, 1, 1] = self.radius
        self._transforms[:, 2, 2] = 1.0

        transData = self.axes.transData
        trafo = transData.get_affine()
        m = trafo.get_matrix().copy()
        m[:2, 2:] = 0
        self.set_transform(transforms.Affine2D(m))

    @allow_rasterization
    def draw(self, renderer):
        """Set transform, then draw."""
        self._set_transforms()
        Collection.draw(self, renderer)


def _plot_frame(sim, fig, ax):
    # setup figure and axes if needed
    if fig is None:
        fig = plt.figure(figsize=(8, 6), dpi=100)
        fig.set_tight_layout(True)

    if ax is None:
        ax = fig.add_subplot(1, 1, 1, aspect="equal", adjustable="datalim")

    # simplify variables
    pos = sim.balls_position
    vel = sim.balls_velocity
    radii = sim.balls_radius

    # draw balls as circles
    balls = BallCollection(
        radii,
        offsets=pos,
        transOffset=ax.transData,
        edgecolor="black",
        linewidth=1,
        zorder=0,
    )
    ax.add_collection(balls)

    # indicate positions via scatter plot
    scatter = ax.scatter(pos[:, 0], pos[:, 1], s=20, color="black")

    # indicate velocities with arrows, slow balls are marked with hexagons
    quiver = ax.quiver(
        pos[:, 0],
        pos[:, 1],
        vel[:, 0],
        vel[:, 1],
        angles="xy",
        scale_units="xy",
        scale=1,
        width=0.004,
        color="black",
    )

    # show the current simulation time
    time_text = ax.text(
        0.02, 0.95, "time = {:.2f}s".format(sim.time), transform=ax.transAxes
    )

    return fig, ax, balls, scatter, quiver, time_text


def plot(sim, fig=None, ax=None, show=True):
    """Plot the given billiard for the current moment.

    Args:
        sim: A billiard simulation.
        fig (optional): Figure used for drawing.
            Defaults to None in which case a new figure will be created.
        ax (optional): Axes used for drawing.
            Defaults to None in which case a nex axes object will be created.
            If an axes object is supplied, use
            ax.set_aspect(self, aspect="equal", adjustable="datalim")
            for correct aspect ratio.
        show (optional): Use pyplot.show() to show the animation.

    Returns:
        fig: matplotlib.figure.Figure object, to save the plot use show=False
        and fig.savefig("savename.png").

    """
    fig, ax, balls, scatter, quiver, time_text = _plot_frame(sim, fig, ax)

    if show:  # pragma: no cover
        plt.show()

    return fig


def animate(sim, end_time, fps=30, fig=None, ax=None, show=True):
    """Animate the billiard plot.

    Args:
        sim: A billiard simulation.
        end_time: Animate from t=0 to t=end_time.
        fps (optional): Frames per second of the animation.
            Defaults to 30.
        fig (optional): Figure used for drawing.
            Defaults to None in which case a new figure will be created.
        ax (optional): Axes used for drawing.
            Defaults to None in which case a nex axes object will be created.
            If an axes object is supplied, use
            ax.set_aspect(self, aspect="equal", adjustable="datalim")
            for correct aspect ratio.
        show (optional): Use pyplot.show() to show the animation.

    Returns:
        anim: matplotlib.animation.FuncAnimation object, to save the animation
            use show=False and anim.save("savename.mp4").

    """
    fig, ax, balls, scatter, quiver, time_text = _plot_frame(sim, fig, ax)

    def init():
        balls.set_offsets(np.empty(shape=(0, 2)))
        scatter.set_offsets(np.empty(shape=(0, 2)))
        quiver.set_offsets(np.empty(shape=(0, 2)))
        quiver.set_UVC(np.empty(shape=(0, 1)), np.empty(shape=(0, 1)))

        time_text.set_text("")

        return (balls, scatter, quiver, time_text)

    def animate(i):
        sim.evolve(i / fps)
        pos = sim.balls_position
        vel = sim.balls_velocity

        balls.set_offsets(pos)
        scatter.set_offsets(pos)
        quiver.set_offsets(pos)
        quiver.set_UVC(vel[:, 0], vel[:, 1])

        time_text.set_text("time = {:.2f}s".format(sim.time))

        return (balls, scatter, quiver, time_text)

    anim = FuncAnimation(
        fig,
        animate,
        frames=int(fps * end_time),
        interval=1000 / fps,
        blit=True,
        init_func=init,
    )

    if show:  # pragma: no cover
        plt.show()

    return anim
