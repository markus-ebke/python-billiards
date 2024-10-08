"""Visualize a billiard simulation using matplotlib.

Usage (assuming ``bld`` is an instance of the ``Billiard`` class)::

    import matplotlib.pyplot as plt  # for plt.show()
    from billiards import visualize

    # show billiard balls and indicate their velocity with arrows, draw obstacles
    visualize.plot(bld)
    plt.show()

    # show how the billiard evolves from bld.time to end_time
    visualize.animate(bld, end_time=10)
    plt.show()

See also the functions ``plot_obstacles``, ``plot_balls`` and ``plot_velocities``
for plotting only certain aspects of the billiard.
"""

import warnings

import numpy as np

try:
    import matplotlib.path as mpath
    import matplotlib.pyplot as plt
    import matplotlib.transforms as mtransforms
    from matplotlib.animation import FuncAnimation
    from matplotlib.artist import allow_rasterization
    from matplotlib.collections import Collection
except ImportError:  # pragma: no cover
    warnings.warn(
        "Could not import matplotlib, "
        "'visualize.plot' and 'visualize.animate' will not work.",
        stacklevel=1,
    )

try:
    from tqdm import trange
except ImportError:  # pragma: no cover
    trange = range
    warnings.warn(
        "Could not import tqdm, will not show progress in 'visualize.animate'.",
        stacklevel=1,
    )


# don't use matplotlib.collections.CircleCollection because there the circle
# size is in screen coordinates, but we need data coordinates
class CircleCollection(Collection):  # pragma: no cover
    """A collection of circles with their radius in data coordinates."""

    def __init__(self, centers, radii, **kwargs):
        """Create balls with given centers and radii.

        Args:
            centers: A Nx2-shaped numpy array, each row the center of a circle.
            radii: The N radii of the circles.
            **kwargs: Keyword arguments for matplotlib.collections.Collection.
        """
        super().__init__(offsets=centers, **kwargs)

        self.set_paths()
        self.set_radii(radii)

    def set_paths(self):
        """Set path (here: a unit circle)."""
        self._paths = [mpath.Path.unit_circle()]
        self.stale = True

    def set_radii(self, radii):
        """Set radii of the circles (modifies self._transforms)."""
        if radii is None:
            self._radii = np.array([])
            self._transforms = np.empty((0, 3, 3))
        else:
            self._radii = np.asarray(radii)
            self._transforms = np.zeros((len(self._radii), 3, 3))
            self._transforms[:, 0, 0] = self._radii
            self._transforms[:, 1, 1] = self._radii
            self._transforms[:, 2, 2] = 1.0

        self.stale = True

    def get_datalim(self, transData):
        """Get the smallest rectangle that encloses the collection."""
        transform = self.get_transform()

        # reverse the translation in transOffset
        transOffset = self.get_offset_transform().frozen()
        transOffset_inv = transOffset.inverted()
        transOffset.get_matrix()[:2, 2:] = transOffset_inv.get_matrix()[:2, 2:]

        offsets = self._offsets
        paths = self.get_paths()

        if not transform.is_affine:
            paths = [transform.transform_path_non_affine(p) for p in paths]
            transform = transform.get_affine()
        if not transOffset.is_affine:
            offsets = transOffset.transform_non_affine(offsets)
            transOffset = transOffset.get_affine()

        if isinstance(offsets, np.ma.MaskedArray):
            offsets = offsets.filled(np.nan)
            # get_path_collection_extents handles nan but not masked arrays

        if len(paths) and len(offsets):
            transforms = self.get_transforms()
            transforms = np.matmul(transData.get_matrix(), transforms)

            result = mpath.get_path_collection_extents(
                transform.frozen(),
                paths,
                transforms,
                offsets,
                transOffset.frozen(),
            )
            result = result.transformed(transData.inverted())
        else:
            result = mtransforms.Bbox.null()
        return result

    def _set_transform(self, transData):
        # use the data -> screen transformation, but delete the translation
        # part because these are in self._transforms
        transform = transData.frozen()
        transform.get_matrix()[:2, 2:] = 0
        self.set_transform(transform)

    @allow_rasterization
    def draw(self, renderer):
        """Render the collection."""
        self._set_transform(self.axes.transData)
        if len(self._paths) and len(self._offsets):
            # only draw if there is somthing to draw
            super().draw(renderer)


CircleCollection.set.__doc__ = ""  # Sphinx complains about :mpltype:


def default_fig_and_ax(figsize=(8, 6), fig=None, ax=None):
    """Create a 800x600 figure with tight layout and equal aspect axes.

    Figure is set the use tight layout, axes will use equal aspect.

    Args:
        figsize: Width and height of the figure, default: (8, 6).
        fig: Create a new figure or use this one.
        ax: Create a new axes object from figure or use this one.

    Returns:
        A figure and one axes object.

    """
    # setup figure if needed and use tight layout
    if fig is None:
        fig = plt.figure(figsize=figsize, dpi=100)
    fig.set_layout_engine("tight")

    # setup axes if needed and use equal aspect
    if ax is None:
        ax = fig.add_subplot(1, 1, 1)
    ax.set_aspect(aspect="equal", adjustable="datalim")

    return fig, ax


def plot_obstacles(bld, ax, color="C2", **kwargs):
    """Draw the obstacles of the billiard.

    Args:
        bld: Billiard object.
        ax: matplotlib axes object.
        color (optional): Color of the obstacles, default: "C2" (green).
        **kwargs: Keyword arguments for Obstacle.plot.

    Returns:
        List of artists that were drawn onto the axes.
    """
    obs_artists = []
    for obs in bld.obstacles:
        ret = obs.plot(ax, color=color, zorder=-1)
        obs_artists.append(ret)

    return obs_artists


def plot_balls(bld, ax, color="C0", **kwargs):
    """Draw the balls in the billiard.

    Balls with zero radius (i.e. point particles) will be drawn using scatter.

    Args:
        bld: Billiard object.
        ax: matplotlib axes object.
        color (optional): Color of the balls, default: "C0" (light blue).
        **kwargs: Keyword arguments for CircleCollection and Axes.scatter.

    Returns:
        Two matplotlib collections, the first one for the proper balls and the
        second one for the point particles.
    """
    # simplify variables
    pos = bld.balls_position
    radii = np.asarray(bld.balls_radius)

    # draw point particles only as markers
    draw_as_circles = radii > 0
    draw_as_markers = np.logical_not(draw_as_circles)

    # draw proper balls as circles
    circles = CircleCollection(
        pos[draw_as_circles],
        radii[draw_as_circles],
        transOffset=ax.transData,
        facecolor=color,
        zorder=0,
        **kwargs,
    )
    ax.add_collection(circles)

    # draw point particles
    points = ax.scatter(
        pos[draw_as_markers, 0],
        pos[draw_as_markers, 1],
        s=20,
        marker="x",
        color=color,
        zorder=0,
        **kwargs,
    )

    return circles, points


def plot_velocities(bld, ax, color="C1", arrow_factor=1, **kwargs):
    """Plot velocites of the balls in the billiard.

    Args:
        bld: Billiard object.
        ax: matplotlib axes object.
        color (optional): Color of the arrows, default: "C1" (yellow).
        arrow_factor (optional): Scale the length of the velocity arrows.
        **kwargs: Keyword arguments for Axes.quiver.

    Returns:
        The output of axes.quiver.

    """
    # simplify variables
    pos = bld.balls_position
    vel = bld.balls_velocity

    # draw velocities as arrows (slow balls will be marked with hexagons)
    arrows = ax.quiver(
        pos[:, 0],
        pos[:, 1],
        vel[:, 0],
        vel[:, 1],
        angles="xy",
        scale_units="xy",
        scale=1 / arrow_factor,
        width=0.004,
        color=color,
        zorder=1,
        **kwargs,
    )

    return arrows


def plot(bld, fig=None, ax=None, velocity_arrow_factor=1):
    """Plot the given billiard for the current moment.

    Args:
        bld: A billiard simulation.
        fig (optional): Figure used for drawing.
            Defaults to None in which case a new figure will be created.
        ax (optional): Axes used for drawing.
            Defaults to None in which case a new axes object will be created.
            If an axes object is supplied, use
            ax.set_aspect(self, aspect="equal", adjustable="datalim")
            for correct aspect ratio.
        velocity_arrow_factor (optional): Scale the length of velocity arrows.
            The default value is 1, meaning that in one time unit the particle
            reaches the tip of the arrow. Larger values increase the length of
            the arrows, smaller values will shrink them. A value of 0 disables
            arrows.

    Returns:
        matplotlib.figure.Figure: The figure used for drawing, to save the
        plot use fig.savefig("savename.png").

    """
    fig, ax = default_fig_and_ax(fig=fig, ax=ax)

    # plot billiard obstacles and balls
    plot_obstacles(bld, ax)
    plot_balls(bld, ax)
    if velocity_arrow_factor > 0:
        plot_velocities(bld, ax, arrow_factor=velocity_arrow_factor)

    # show the current simulation time
    text = f"Time: {bld.time:.3f}"
    ax.text(0.02, 0.95, text, transform=ax.transAxes)

    return fig


def animate(
    bld, end_time, fps=30, fig=None, ax=None, velocity_arrow_factor=1, **kwargs
):
    """Animate the billiard plot.

    Advance the simulation in timesteps of size 1/fps until bld.time equals
    end_time, in every iteration save a snapshot of the balls. A progressbar
    indicates how many frames must be computed. After the simulation is done,
    the animation is returned as a matplotlib animation object. To play the
    animation, assign it to a variable (to prevent it from garbage-collection)
    and use matplotlib.pyplot.show().

    Args:
        bld: A billiard simulation.
        end_time: Animate from t=bld.time to t=end_time.
        fps (optional): Frames per second of the animation.
            Defaults to 30.
        fig (optional): Figure used for drawing.
            Defaults to None in which case a new figure will be created.
        ax (optional): Axes used for drawing.
            Defaults to None in which case a new axes object will be created.
            If an axes object is supplied, use
            ax.set_aspect(self, aspect="equal", adjustable="datalim")
            for correct aspect ratio.
        velocity_arrow_factor (optional): Scale the length of velocity arrows.
            The default value is 1, meaning that in one time unit the particle
            reaches the tip of the arrow. Larger values increase the length of
            the arrows, smaller values will shrink them. A value of 0 disables
            arrows.
        **kwargs (optional): other keyword arguments are passed to
            matplotlib.animation.FuncAnimation.

    Returns:
        matplotlib.animation.FuncAnimation: An animation object, to play the
        animation use matplotlib.pyplot.show(), to save it as a video use
        anim.save("savename.mp4").

    """
    start_time = bld.time
    frames = int(fps * (end_time - start_time)) + 1  # include end_time frame

    # precompute the simulation
    time = []
    positions = []
    velocities = []
    for i in trange(frames):
        bld.evolve(start_time + i / fps)

        time.append(bld.time)
        positions.append(bld.balls_position.copy())
        velocities.append(bld.balls_velocity.copy())

    # setup plot
    fig, ax = default_fig_and_ax(fig=fig, ax=ax)

    # plot billiard obstacle and balls
    plot_obstacles(bld, ax)
    circles, points = plot_balls(bld, ax)
    if velocity_arrow_factor > 0:
        arrows = plot_velocities(bld, ax, arrow_factor=velocity_arrow_factor)

    # show the current simulation time
    text = f"Time: {bld.time:.3f}"
    time_text = ax.text(0.02, 0.95, text, transform=ax.transAxes)

    # draw point particles only as markers
    draw_as_circles = np.asarray(bld.balls_radius) > 0
    draw_as_markers = np.logical_not(draw_as_circles)

    def init():
        time_text.set_text("")

        circles.set_offsets(np.empty(shape=(1, 2)))
        points.set_offsets(np.empty(shape=(1, 2)))

        if velocity_arrow_factor > 0:
            arrows.set_offsets(np.empty(shape=(1, 2)))
            arrows.set_UVC(np.empty(shape=(1, 1)), np.empty(shape=(1, 1)))

            return (time_text, circles, points, arrows)
        else:
            return (time_text, circles, points)

    # animate will play the precomputed simulation
    def animate(i):
        time_text.set_text(f"Time: {time[i]:.3f}")

        pos = positions[i]
        circles.set_offsets(pos[draw_as_circles])
        points.set_offsets(pos[draw_as_markers])

        if velocity_arrow_factor > 0:
            arrows.set_offsets(pos)
            vel = velocities[i]
            arrows.set_UVC(vel[:, 0], vel[:, 1])

            return (time_text, circles, points, arrows)
        else:
            return (time_text, circles, points)

    kwargs.setdefault("cache_frame_data", False)  # to save memory
    anim = FuncAnimation(
        fig, animate, frames, interval=1000 / fps, blit=True, init_func=init, **kwargs
    )

    return anim
