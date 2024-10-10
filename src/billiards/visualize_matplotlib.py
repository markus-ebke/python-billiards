"""Visualize a billiard simulation using matplotlib.

Usage (assuming ``bld`` is an instance of the ``Billiard`` class)::

    import matplotlib.pyplot as plt  # for plt.show()
    from billiards import visualize_matplotlib

    # show the billiard simulation including velocity vectors
    visualize_matplotlib.plot(bld)
    plt.show()

    # show evolution of the simulation from bld.time to end_time
    visualize_matplotlib.animate(bld, end_time=10)
    plt.show()

Use the functions ``plot_obstacles``, ``plot_balls``, ``plot_points`` and
``plot_velocities`` for plotting only certain aspects of the billiard. Each of
these function takes a ``billiard.Simulation`` instance, a
``matplotlib.axes.Axes`` instance and an optional ``colors`` argument (a mapping
from billiard objects to `matplotlib` colors). Any additional keyword arguments
are passed to the appropriate plotting functions of the ``matplotlib.axes.Axes``
instance.

The global variable ``default_colors`` stores colors for each billiard object
type. To adjust the colors (or disable plotting) for certain objects or object
types:
* change or add entries of ``default_colors`` or
* use the ``colors`` parameter of the plot functions above.

The ``plot_obstacles`` function looks up the appropriate plotting function in
the global variable ``obstacle_plot_functions``. If you implement a custom
obstacle, add the corresponding plot function here.
"""

import matplotlib.animation
import matplotlib.path
import matplotlib.pyplot as plt
import matplotlib.transforms
import numpy as np

try:
    from tqdm import trange
except ImportError:  # pragma: no cover
    import warnings

    warnings.warn(
        "Could not import tqdm, will not show progress in 'animate' function.",
        stacklevel=1,
    )
    trange = range


from .obstacles import Disk, InfiniteWall, LineSegment

default_colors = {
    "obstacles": "C2",
    "balls": "C0",
    "points": "C0",
    "velocities": "C1",
}
"""dict: The default values for the colors.
Possible keys for this mapping are:

* the strings ``"obstacles"``, ``"balls"``, ``"points"`` and ``"velocities"``:
  set the color used for all obstacles, all balls with positive radius
  (``"balls"``), all balls with zero radius (``"points"``) and the velocity
  vectors. These keys must always be present.
* an integer ``i`` in the range from 0 to ``bld.num``:
  set the color of the ball with index ``i`` (takes precedence over the
  setting for ``"balls"``).
* an obstacle class (e.g., ``obstacle.Disk``):
  set the color all obstacles of this class (takes precedence over
  ``"obstacle"``).
* an obstacle instance:
  set the color of this obstacle (takes precedence over the obstacle class
  and ``"obstacle"``).

Possible values are valid `matplotlib` colors and ``None`` (which disables
plotting for this object or class of objects).

The default colors are (in draw order)::

    {"obstacles": "C2", "balls": "C0", "points": "C0", "velocities": "C1"}

"""


def _merge_colors(colors=None):
    if colors is None:
        colors = default_colors
    else:
        if not isinstance(colors, dict):  # TODO generalize "dict" to "Mapping"?
            raise TypeError(f"'colors' must be a mapping, not {type(colors)}")
        colors = {**default_colors, **colors}
    return colors


obstacle_plot_functions = {}
"""dict: The plotting functions for obstacles. Each key is an obstacle classes
(e.g., ``Disk``, ``InfiniteLine``), the corresponding value is a function with
signature::

    plot_func(obs: obstacle.Obstacle, ax: matplotlib.axes.Axes, color, **kwargs) -> None

The color argument is a `matplotlib` colors, the keyword arguments will be
passed to `matplotlib` plotting functions."""


def plot_disk(obs, ax, color, **kwargs):
    """Draw the disk onto the given matplotlib axes."""
    assert isinstance(obs, Disk), type(obs)
    assert isinstance(ax, matplotlib.axes.Axes), type(ax)

    patch = matplotlib.patches.Circle(obs.center, obs.radius, facecolor=color, **kwargs)
    ax.add_patch(patch)


obstacle_plot_functions[Disk] = plot_disk


def plot_infinite_wall(obs, ax, color, **kwargs):
    """Draw the infinite wall onto the given matplotlib axes."""
    assert isinstance(obs, InfiniteWall), type(obs)
    assert isinstance(ax, matplotlib.axes.Axes), type(ax)

    # wall
    ax.axline(obs.start_point, obs.end_point, color=color, **kwargs)

    # hatching to mark inside of wall
    scale = 0.05
    extent = scale * np.linalg.norm(obs.start_point - obs.end_point)
    xy = [
        obs.start_point,
        obs.start_point - extent * obs._normal,
        obs.end_point - extent * obs._normal,
        obs.end_point,
    ]
    patch = matplotlib.patches.Polygon(
        xy, hatch="xx", edgecolor=color, linewidth=0, fill=None, **kwargs
    )
    ax.add_patch(patch)


obstacle_plot_functions[InfiniteWall] = plot_infinite_wall


def plot_line_segment(obs, ax, color, **kwargs):
    """Draw the line segment onto the given matplotlib axes."""
    assert isinstance(obs, LineSegment), type(obs)
    assert isinstance(ax, matplotlib.axes.Axes), type(ax)

    kwargs.setdefault("solid_capstyle", "round")
    sx, sy = obs.start_point
    ex, ey = obs.end_point
    ax.plot([sx, ex], [sy, ey], color=color, **kwargs)


obstacle_plot_functions[LineSegment] = plot_line_segment


# don't use matplotlib.collections.CircleCollection because there the circle
# size is in screen coordinates, but we need data coordinates
class CircleCollection(matplotlib.collections.Collection):  # pragma: no cover
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
        self._paths = [matplotlib.path.Path.unit_circle()]
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

            result = matplotlib.path.get_path_collection_extents(
                transform.frozen(),
                paths,
                transforms,
                offsets,
                transOffset.frozen(),
            )
            result = result.transformed(transData.inverted())
        else:
            result = matplotlib.transforms.Bbox.null()
        return result

    def _set_transform(self, transData):
        # use the data -> screen transformation, but delete the translation
        # part because these are in self._transforms
        transform = transData.frozen()
        transform.get_matrix()[:2, 2:] = 0
        self.set_transform(transform)

    @matplotlib.artist.allow_rasterization
    def draw(self, renderer):
        """Render the collection."""
        self._set_transform(self.axes.transData)
        if len(self._paths) and len(self._offsets):
            # only draw if there is somthing to draw
            super().draw(renderer)


CircleCollection.set.__doc__ = ""  # Sphinx complains about :mpltype:


def default_fig_and_ax(fig=None, ax=None, **kwargs):
    """Create a figure and add an Axes with equal aspect ratio.

    Args:
        fig (optional): Create a new figure or use this one.
        ax (optional): Create a new axes object from figure or use this one.
        **kwargs: Keyword arguments for ``plt.figure``.

    Returns:
        A figure and an axes object.
    """
    # setup figure if needed
    if fig is None:
        fig = plt.figure(**kwargs)

    # setup axes if needed and use equal aspect
    if ax is None:
        ax = fig.add_subplot(1, 1, 1)
    ax.set_aspect(aspect="equal", adjustable="datalim")

    return fig, ax


def plot_obstacles(bld, ax, colors=None, **kwargs):
    """Draw the obstacles of the billiard.

    Args:
        bld: Billiard object.
        ax: matplotlib axes object.
        color (optional): Color of the obstacles, default: "C2" (green).
        **kwargs: Keyword arguments for Obstacle.plot.

    Returns:
        List of artists that were drawn onto the axes.
    """
    colors = _merge_colors(colors)
    default_color = colors["obstacles"]

    obs_artists = []
    for obs in bld.obstacles:
        col = colors.get(type(obs), default_color)
        col = colors.get(obs, col)

        if col is not None:
            plot_func = obstacle_plot_functions[type(obs)]
            plot_func(obs, ax, col, **kwargs)

    return obs_artists


def plot_balls(bld, ax, colors=None, **kwargs):
    """Draw balls with non-zero radius as circles.

    Args:
        bld: Billiard object.
        ax: matplotlib axes object.
        color (optional): Color of the balls, default: "C0" (light blue).
        **kwargs: Keyword arguments for CircleCollection and Axes.scatter.

    Returns:
        Two matplotlib collections, the first one for the proper balls and the
        second one for the point particles.
    """
    colors = _merge_colors(colors)
    default_color = colors["balls"]

    # filter out proper balls
    radii = np.asarray(bld.balls_radius)
    draw_as_circles = radii > 0

    # Set custom ball color
    if any(isinstance(key, int) and draw_as_circles[key] for key in colors.keys()):
        col = []
        for i in range(bld.num):
            c = colors.get(i, default_color)
            if c is None:
                draw_as_circles[i] = False
            else:
                col.append(c)
    else:
        col = default_color

    # plot balls
    if col is not None:
        circles = CircleCollection(
            bld.balls_position[draw_as_circles],
            radii[draw_as_circles],
            transOffset=ax.transData,
            facecolor=col,
            **kwargs,
        )
        ax.add_collection(circles)
        return circles
    else:
        return []


def plot_points(bld, ax, colors=None, point_marker="x", point_size=20, **kwargs):
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
    colors = _merge_colors(colors)
    default_color = colors["points"]

    # filter out point particles
    radii = np.asarray(bld.balls_radius)
    draw_as_markers = radii == 0

    if any(isinstance(key, int) and draw_as_markers[key] for key in colors.keys()):
        col = []
        for i in range(bld.num):
            c = colors.get(i, default_color)
            if c is None:
                draw_as_markers[i] = False
            else:
                col.append(c)
    else:
        col = default_color

    # plot particles
    if col is not None:
        points = ax.scatter(
            bld.balls_position[draw_as_markers, 0],
            bld.balls_position[draw_as_markers, 1],
            s=point_size,
            marker=point_marker,
            color=col,
            **kwargs,
        )
        return points
    else:
        return []


def plot_velocities(bld, ax, colors=None, velocity_scale=1.0, **kwargs):
    """Plot velocites of the balls in the billiard.

    Args:
        bld: Billiard object.
        ax: matplotlib axes object.
        color (optional): Color of the arrows, default: "C1" (yellow).
        velocity_scale (optional): Scale the length of the velocity arrows.
        **kwargs: Keyword arguments for ``Axes.quiver``.

    Returns:
        The output of ``Axes.quiver``.
    """
    colors = _merge_colors(colors)
    col = colors["velocities"]

    # draw velocities as arrows (slow balls will be marked with hexagons)
    if col is not None and velocity_scale > 0:
        arrows = ax.quiver(
            bld.balls_position[:, 0],
            bld.balls_position[:, 1],
            bld.balls_velocity[:, 0],
            bld.balls_velocity[:, 1],
            angles="xy",
            scale_units="xy",
            scale=1 / velocity_scale,
            width=0.004,
            color=col,
            **kwargs,
        )
        return arrows
    else:
        return []


def plot(
    bld,
    fig=None,
    ax=None,
    colors=None,
    point_marker="x",
    point_size=20,
    velocity_scale=1.0,
    figsize=(8, 6),
    dpi=100,
    layout="tight",
    **kwargs,
):
    """Plot the given billiard for the current moment.

    Args:
        bld: A billiard simulation.
        fig (optional): Figure used for drawing.
            Defaults to None in which case a new figure will be created.
        ax (optional): Axes used for drawing.
            Defaults to None in which case a new axes object will be created.
            The new (or given) axes will be set to "equal" aspect ratio.
        velocity_scale (optional): Scale the length of velocity arrows.
            The default value is 1, meaning that in one time unit the particle
            reaches the tip of the arrow. Larger values increase the length of
            the arrows, smaller values will shrink them. A value of 0 disables
            arrows.

    Returns:
        matplotlib.figure.Figure: The figure used for drawing, to save the
        plot use fig.savefig("savename.png").

    """
    fig, ax = default_fig_and_ax(fig, ax, figsize=figsize, dpi=dpi, layout=layout)
    # colors = _merge_colors(colors)

    # plot billiard obstacles, balls and velocities
    plot_obstacles(bld, ax, colors, **kwargs)
    plot_balls(bld, ax, colors, **kwargs)
    plot_points(
        bld, ax, colors, point_marker=point_marker, point_size=point_size, **kwargs
    )
    plot_velocities(bld, ax, colors, velocity_scale=velocity_scale, **kwargs)

    # show the current simulation time
    text = f"Time: {bld.time:.3f}"
    ax.text(0.02, 0.95, text, transform=ax.transAxes)

    return fig, ax


def animate(
    bld,
    end_time,
    fps=30,
    fig=None,
    ax=None,
    colors=None,
    point_marker="x",
    point_size=20,
    velocity_scale=1.0,
    figsize=(8, 6),
    dpi=100,
    layout="tight",
    blit=False,
    repeat=True,
    repeat_delay=0,
    **kwargs,
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
        velocity_scale (optional): Scale the length of velocity arrows.
            The default value is 1, meaning that in one time unit the particle
            reaches the tip of the arrow. Larger values increase the length of
            the arrows, smaller values will shrink them. A value of 0 disables
            arrows.
        **kwargs (optional): other keyword arguments are passed to the axes plot
            functions.

    Returns:
        A tuple of three objects: animation, figure and axes.

        The first element is a `matplotlib.animation.FuncAnimation` object. To
        play the animation use `matplotlib.pyplot.show()`, to save it as a video
        use anim.save("videoname.mp4").

        The second element (a `matplotlib.figure.Figure` object) and the third
        element (a `matplotlib.axes.Axes` object) are the figure and axes that
        will be animated.

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
    fig, ax = default_fig_and_ax(fig, ax, figsize=figsize, dpi=dpi, layout=layout)
    # colors = _merge_colors(colors)

    # plot billiard obstacle and balls
    plot_obstacles(bld, ax, colors, **kwargs)
    circles = plot_balls(bld, ax, colors, **kwargs)
    points = plot_points(
        bld, ax, colors, point_marker=point_marker, point_size=point_size, **kwargs
    )
    arrows = plot_velocities(bld, ax, colors, velocity_scale=velocity_scale, **kwargs)

    # show the current simulation time
    text = f"Time: {bld.time:.3f}"
    time_text = ax.text(0.02, 0.95, text, transform=ax.transAxes)

    # draw point particles only as markers
    draw_as_circles = np.asarray(bld.balls_radius) > 0
    draw_as_markers = np.logical_not(draw_as_circles)

    def init():
        time_text.set_text("")
        ret = (time_text,)

        if circles:
            circles.set_offsets(np.empty(shape=(1, 2)))
            ret += (circles,)

        if points:
            points.set_offsets(np.empty(shape=(1, 2)))
            ret += (points,)

        if arrows:
            arrows.set_offsets(np.empty(shape=(1, 2)))
            arrows.set_UVC(np.empty(shape=(1, 1)), np.empty(shape=(1, 1)))
            ret += (arrows,)

        return ret

    # animate will play the precomputed simulation
    def animate(i):
        time_text.set_text(f"Time: {time[i]:.3f}")
        ret = (time_text,)

        pos = positions[i]
        if circles:
            circles.set_offsets(pos[draw_as_circles])
            ret += (circles,)

        if points:
            points.set_offsets(pos[draw_as_markers])
            ret += (points,)

        if arrows:
            arrows.set_offsets(pos)
            vel = velocities[i]
            arrows.set_UVC(vel[:, 0], vel[:, 1])
            ret += (arrows,)

        return ret

    anim = matplotlib.animation.FuncAnimation(
        fig,
        animate,
        frames,
        interval=1000 / fps,
        blit=blit,
        init_func=init,
        repeat=repeat,
        repeat_delay=repeat_delay,
        cache_frame_data=False,  # to save memory
    )

    return anim, fig, ax
