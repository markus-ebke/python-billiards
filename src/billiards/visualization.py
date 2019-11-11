# -*- coding: utf-8 -*-
import numpy as np

try:
    from matplotlib.artist import allow_rasterization
    import matplotlib.transforms as transforms
    from matplotlib.path import Path
    from matplotlib.collections import Collection
    from matplotlib.animation import FuncAnimation
    import matplotlib.pyplot as plt
except ImportError as ex:
    print("Cannot use billiards.visualization, matplotlib is not installed.")
    raise ex


class BallCollection(Collection):
    def __init__(self, radius, **kwargs):
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
    fig, ax, balls, scatter, quiver, time_text = _plot_frame(sim, fig, ax)

    if show:
        plt.show()

    return fig


def animate(sim, end_time, fps=30, fig=None, ax=None, show=True):
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

    if show:
        plt.show()

    return anim
