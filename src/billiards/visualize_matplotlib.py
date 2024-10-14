"""Visualize a billiard simulation using *matplotlib*.

Usage (assuming ``bld`` is an instance of the ``Billiard`` class)::

    import matplotlib.pyplot as plt  # for plt.show()
    from billiards import visualize_matplotlib

    # show the billiard simulation including velocity vectors
    visualize_matplotlib.plot(bld)
    plt.show()

    # show evolution of the simulation from bld.time to end_time
    visualize_matplotlib.animate(bld, end_time=10)
    plt.show()

Use the functions ``plot_obstacles``, ``plot_balls``, ``plot_particles`` and
``plot_velocities`` for plotting only certain aspects of the billiard. Each of
these function takes a ``billiard.Simulation`` instance, a
``matplotlib.axes.Axes`` instance and an optional ``color_scheme`` argument (a
mapping from billiard objects to *matplotlib* colors). Any additional keyword
arguments are passed to the appropriate plotting functions of the
``matplotlib.axes.Axes`` instance.

The global variable ``default_color_scheme`` stores colors for each billiard
object type. To adjust the colors (or disable plotting) for certain objects or
object types:
* change or add entries of ``default_color_scheme`` or
* use the ``color_scheme`` parameter of the plot functions above.
For more information, see the documentation for ``default_color_scheme``.

The ``plot_obstacles`` function uses the global variable
``obstacle_plot_functions`` to look up the appropriate plotting function. If
you implement a custom obstacle, add the corresponding plot function to this
mapping (key: obstacle class, value: plot function). For more information, see
the documentation for ``obstacle_plot_functions``.
"""

import matplotlib.animation as manimation
import matplotlib.artist as martist
import matplotlib.axes as maxes
import matplotlib.collections as mcollections
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.path as mpath
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
import numpy as np

# If tqdm is installed, use it to draw a progress bar in 'animate'
try:
    from tqdm.auto import trange
except ImportError:  # pragma: no cover
    trange = range


from .obstacles import Disk, InfiniteWall, LineSegment

default_color_scheme = {
    "obstacles": "C2",  # green
    "balls": ("C0", "C1"),  # balls: blue, velocities: orange
    "particles": ("C0", "C1"),  # particles: blue, velocities: orange
}
"""dict: The default value of the ``color_scheme`` argument.
Possible keys for this mapping are:

* the strings ``"obstacles"``, ``"balls"`` and ``"particles"``:
  set the color used for all obstacles, all balls with positive radius
  (``"balls"``) and all balls with zero radius (``"particles"``).
  These keys must always be present.
* an integer ``i`` in the range from 0 to ``bld.num``:
  set the color of the ball with index ``i`` (takes priority over the setting
  for ``"balls"``, ``"particles``" and ``"velocities"``).
* an obstacle class (e.g., ``obstacle.Disk``):
  set the color of all obstacles of this class (takes priority over ``"obstacle"``).
* an obstacle instance:
  set the color of this obstacle (takes priority over the obstacle class and
  ``"obstacle"``).

Possible values are:

* A valid *matplotlib* color. The velocity arrows will copy the color of their ball
  or particle.
* For ``"balls"`` and ``"particles"``: A tuple of *matplotlib* colors, the second
  entry is the arrow color.
* ``None``, to disable drawing this object or types of objects.

The default colors are (in draw order) green for obstacles, blue with orange arrows
for balls and particles::

    {"obstacles": "C2", "balls": ("C0", "C1"), "particles": ("C0", "C1")}

Examples:
    * Disable velocity arrows::

        color_scheme = {"balls": ("C0", None), "particles": ("C0", None)}

      or ``arrow_size = 0`` in the plot functions.

    * Disable velocity arrows for balls, but use an arrow for ball number 42::

        color_scheme = {"balls": ("C0", None), 42: ("C0", "C1")}

    * Draw ball 42 and its arrow in red, default colors for everything else::

        color_scheme = {42: "red"}

    * Draw balls and their velocity arrows in black with transparency::

        color_scheme = {"balls": ("black", 0.4)}  # matplotlib>=3.8
        color_scheme = {"balls": (0.0, 0.0, 0.0, 0.4)}

    * Draw obstacles in black, balls in red with transparent orange arrows, but
      ball 42 and its arrow in blue and without an arrow::

        color_scheme = {
            "obstacles": "black",
            "balls": ("red", ("orange", 0.5)),  # matplotlib>=3.8
            "balls": ("red", (1.0, 0.65, 0.0, 0.5)),  # matplotlib<3.8
            42: ("blue", None)
        }

"""


def _merge_color_scheme(color_scheme=None):
    if color_scheme is None:
        color_scheme = default_color_scheme
    else:
        if not isinstance(color_scheme, dict):  # TODO generalize "dict" to "Mapping"?
            msg = f"'color_scheme' must be a mapping, not {type(color_scheme)}"
            raise TypeError(msg)
        color_scheme = {**default_color_scheme, **color_scheme}
    return color_scheme


def _is_color_like(col):
    # Wrapper around matplotlib.colors.is_color_like, treats (color, None) never
    # as a color (matplotlib>=3.8 will interpret the "None" part as alpha=1.0)
    if isinstance(col, tuple) and len(col) == 2 and col[1] is None:
        return False
    return mcolors.is_color_like(col)


obstacle_plot_functions = {}
"""dict: The plotting functions for obstacles. Each key is an obstacle class
(e.g., ``Disk``, ``InfiniteLine``), the corresponding value is a function with
signature::

    plot_func(obs: obstacle.Obstacle, ax: matplotlib.axes.Axes, color, **kwargs) -> None

The color argument is a *matplotlib* color, the keyword arguments will be
passed to *matplotlib* plotting functions."""


def plot_disk(obs, ax, color, **kwargs):
    """Draw the disk onto the given *matplotlib* axes."""
    assert isinstance(obs, Disk), type(obs)
    assert isinstance(ax, maxes.Axes), type(ax)

    patch = mpatches.Circle(obs.center, obs.radius, facecolor=color, **kwargs)
    ax.add_patch(patch)


obstacle_plot_functions[Disk] = plot_disk


def plot_infinite_wall(obs, ax, color, **kwargs):
    """Draw the infinite wall onto the given *matplotlib* axes."""
    assert isinstance(obs, InfiniteWall), type(obs)
    assert isinstance(ax, maxes.Axes), type(ax)

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
    patch = mpatches.Polygon(
        xy, hatch="xx", edgecolor=color, linewidth=0, fill=None, **kwargs
    )
    ax.add_patch(patch)


obstacle_plot_functions[InfiniteWall] = plot_infinite_wall


def plot_line_segment(obs, ax, color, **kwargs):
    """Draw the line segment onto the given *matplotlib* axes."""
    assert isinstance(obs, LineSegment), type(obs)
    assert isinstance(ax, maxes.Axes), type(ax)

    sx, sy = obs.start_point
    ex, ey = obs.end_point
    ax.plot([sx, ex], [sy, ey], color=color, solid_capstyle="round", **kwargs)


obstacle_plot_functions[LineSegment] = plot_line_segment


# Don't use matplotlib.collections.CircleCollection, because there the circle
# size is in screen coordinates but we need data coordinates.
# We also can't use EllipseCollection with units="xy", because the get_datalim
# method does not include the size of the ellipses. When plotting, balls at the
# edges may end up partly outside the axes limits.
class CircleCollection(mcollections.Collection):  # pragma: no cover
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

    @martist.allow_rasterization
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
        fig (optional): A *matplotlib* figure or None (will create a new
            figure). Defaults to None.
        ax (optional): A *matplotlib* axes instance or None (will create a new
            axes for the figure). The axes coordinate system will use equal
            aspect ratio. Defaults to None.
        **kwargs: Keyword arguments for ``plt.figure`` (called when ``fig`` is
            None).

    Returns:
        A tuple (figure, axes).
    """
    # TODO compute figsize from aspect ratio of billiard

    # setup figure if needed
    if fig is None:
        fig = plt.figure(**kwargs)

    # setup axes if needed and use equal aspect
    if ax is None:
        ax = fig.add_subplot(1, 1, 1)
    ax.set_aspect(aspect="equal", adjustable="datalim")

    return fig, ax


def plot_obstacles(bld, ax, color_scheme=None, **kwargs):
    """Plot the obstacles of the billiard.

    Args:
        bld: Plot obstacles of this billiard.
        ax: Axes to draw onto.
        color_scheme (optional): Contains settings for the color of the
            obstacles. Will use as keys the obstacle instance (color for a
            specific obstacle), the obstacle class (color for all instances of
            a specific class) or the string ``"obstacles"`` (color for all
            obstacles) in decreasing order of priority.
            The default values for these keys are taken from the global variable
            ``default_color_scheme``. Defaults to None (all colors are taken from
            the default color scheme).
        **kwargs: Keyword arguments for the obstacle plot functions.
    """
    color_scheme = _merge_color_scheme(color_scheme)
    default_color = color_scheme["obstacles"]

    for obs in bld.obstacles:
        col = color_scheme.get(type(obs), default_color)
        col = color_scheme.get(obs, col)

        if col is not None:
            plot_func = obstacle_plot_functions[type(obs)]
            plot_func(obs, ax, col, **kwargs)


def plot_balls(bld, ax, color_scheme=None, **kwargs):
    """Plot balls with non-zero radius as circles.

    Args:
        bld: Plot balls of this billiard.
        ax: Axes to draw onto.
        color_scheme (optional): Settings for the color of the balls. Will use
            as keys the integers in the range ``range(bld.num)`` (color for a
            specific ball) or the string ``"balls"`` (default color for all balls)
            in decreasing order of priority.
            The default values for these keys are taken from the global variable
            ``default_color_scheme``. Defaults to None (all colors are taken from
            the default color scheme).
        **kwargs: Keyword arguments for ``CircleCollection``.

    Returns:
        A ``CircleCollection`` or None (if all balls have radius zero or
        their color is set to None).
    """
    color_scheme = _merge_color_scheme(color_scheme)
    default_color = color_scheme["balls"]
    if (
        isinstance(default_color, tuple)
        and len(default_color) == 2
        and not _is_color_like(default_color)
    ):
        default_color = default_color[0]

    # filter out proper balls
    radii = np.asarray(bld.balls_radius)
    draw_as_circles = radii > 0

    # Set custom ball color
    if any(draw_as_circles[key] for key in color_scheme.keys() if isinstance(key, int)):
        col = []
        for i in range(bld.num):
            if not draw_as_circles[i]:
                continue

            c = color_scheme.get(i, default_color)
            if c is None:
                draw_as_circles[i] = False
            elif isinstance(c, tuple) and len(c) == 2 and not _is_color_like(c):
                if c[0] is None:
                    draw_as_circles[i] = False
                else:
                    col.append(c[0])
            else:
                col.append(c)

        assert np.count_nonzero(draw_as_circles) == len(col)
        if len(col) == 1:
            col = col[0]
    else:
        col = default_color

    # plot balls
    if col is not None and np.any(draw_as_circles):
        # The get_datalim method of EllipseCollection does not include the size of the
        # ellipses. That's why we need to implement our own collection class
        # diameter = 2 * radii[draw_as_circles]
        # circles = mcollections.EllipseCollection(
        #     widths=diameter,
        #     heights=diameter,
        #     angles=np.full(len(diameter), 0.0),
        #     offsets=bld.balls_position[draw_as_circles],
        #     units="xy",
        #     offset_transform=ax.transData,
        #     facecolor=col,
        #     **kwargs,
        # )

        circles = CircleCollection(
            bld.balls_position[draw_as_circles],
            radii[draw_as_circles],
            transOffset=ax.transData,
            facecolor=col,
            **kwargs,
        )
        ax.add_collection(circles)
        return circles


def plot_particles(
    bld, ax, particle_marker=".", particle_size=20, color_scheme=None, **kwargs
):
    """Plot balls with zero radius (point particles) using the given marker.

    Args:
        bld: Plot balls of this billiard.
        ax: Axes to draw onto.
        particle_marker (optional): A *matplotlib* marker style for the particles.
            Defaults to ".".
        particle_size (optional): The marker size in points**2. Defaults to 20.
        color_scheme (optional): Settings for the color of the balls. Will use
            as keys the integers in the range ``range(bld.num)`` (color for a
            specific ball) or the string ``"particles"`` (default color for all point
            particles) in decreasing order of priority.
            The default values for these keys are taken from the global variable
            ``default_color_scheme``. Defaults to None (all colors are taken from
            the default color scheme).
        **kwargs: Keyword arguments for ``Axes.scatter``.

    Returns:
        The return value of ``Axes.scatter`` or None (if all balls have
        positive radius or their color is set to None).
    """
    color_scheme = _merge_color_scheme(color_scheme)
    default_color = color_scheme["particles"]
    if (
        isinstance(default_color, tuple)
        and len(default_color) == 2
        and not _is_color_like(default_color)
    ):
        default_color = default_color[0]

    # filter out point particles
    radii = np.asarray(bld.balls_radius)
    draw_as_markers = radii == 0

    # Set custom ball color
    if any(draw_as_markers[key] for key in color_scheme.keys() if isinstance(key, int)):
        col = []
        for i in range(bld.num):
            if not draw_as_markers[i]:
                continue

            c = color_scheme.get(i, default_color)
            if c is None:
                draw_as_markers[i] = False
            elif isinstance(c, tuple) and len(c) == 2 and not _is_color_like(c):
                if c[0] is None:
                    draw_as_markers[i] = False
                else:
                    col.append(c[0])
            else:
                col.append(c)

        assert np.count_nonzero(draw_as_markers) == len(col)
        if len(col) == 1:
            col = col[0]
    else:
        col = default_color

    # plot particles
    if col is not None and np.any(draw_as_markers):
        points = ax.scatter(
            bld.balls_position[draw_as_markers, 0],
            bld.balls_position[draw_as_markers, 1],
            s=particle_size,
            marker=particle_marker,
            color=col,
            **kwargs,
        )
        return points


def plot_velocities(bld, ax, arrow_size=1.0, color_scheme=None, **kwargs):
    """Draw ball velocities as arrows.

    Args:
        bld: Plot ball velocities of this billiard.
        ax: Axes to draw onto.
        arrow_size (optional): The length of the velocity arrows is
            ``ball velocity * arrow_size``. A size of zero disables arrows.
            Defaults to 1.0.
        color_scheme (optional): Settings for the color of the arrows. Will use
            as keys the integers in the range ``range(bld.num)`` (color for the
            arrow of a specific ball) or the strings ``"balls"`` and
            ``"particles"`` (default color for all arrows) in decreasing order
            of priority.
            The default values for these keys are taken from the global variable
            ``default_color_scheme``. Defaults to None (all colors are taken from
            the default color scheme).
        **kwargs: Keyword arguments for ``Axes.quiver``.

    Returns:
        The return value of ``Axes.quiver`` or None (if ``arrow_size`` is zero,
        all balls have their color set to None or their velocity color set to None.
    """
    if arrow_size == 0.0:
        return None

    color_scheme = _merge_color_scheme(color_scheme)
    default_ball_color = color_scheme["balls"]
    default_particle_color = color_scheme["particles"]

    # filter out invisible balls
    draw_velocities = np.full(bld.num, True, dtype=bool)

    # Set custom arrow color
    col = []
    for i in range(bld.num):
        if bld.balls_radius[i] > 0:
            c = color_scheme.get(i, default_ball_color)
        else:
            c = color_scheme.get(i, default_particle_color)

        if c is None:
            draw_velocities[i] = False
        elif isinstance(c, tuple) and len(c) == 2 and not _is_color_like(c):
            if c[1] is None:
                draw_velocities[i] = False
            else:
                col.append(c[1])
        else:
            col.append(c)

    assert np.count_nonzero(draw_velocities) == len(col)
    if len(col) == 1:
        col = col[0]

    # draw velocities as arrows (slow balls will be marked with small dots)
    if col is not None and np.any(draw_velocities):
        arrows = ax.quiver(
            bld.balls_position[draw_velocities, 0],
            bld.balls_position[draw_velocities, 1],
            bld.balls_velocity[draw_velocities, 0],
            bld.balls_velocity[draw_velocities, 1],
            angles="xy",
            scale_units="xy",
            scale=1 / arrow_size,
            width=2.5,  # a bit thinner than the default
            units="dots",  # dots: width is in pixels and independent of figure width
            color=col,
            **kwargs,
        )
        return arrows


def plot(
    bld,
    particle_marker=".",
    particle_size=20,
    arrow_size=1.0,
    color_scheme=None,
    fig=None,
    ax=None,
    figsize=(8, 6),
    dpi=100,
    layout="tight",
    **kwargs,
):
    """Draw the given billiard simulation.

    Call ``matplotlib.pyplot.show()`` to display the plot.

    Args:
        bld: A billiard simulation to plot.
        particle_marker (optional): A *matplotlib* marker style for the particles.
            Defaults to ".".
        particle_size (optional): The marker size in points**2. Defaults to 20.
        arrow_size (optional): The length of the velocity arrows is
            ``ball velocity * arrow_size``. A size of zero disables arrows.
            Defaults to 1.0.
        color_scheme (optional): Settings for the color of the billiard objects.
            The default values are taken from the global variable
            ``default_color_scheme`` (see its docstring for more info). Defaults
            to None (all colors are taken from the default color scheme).
        fig (optional): A *matplotlib* figure or None (will create a new
            figure). Defaults to None.
        ax (optional): A *matplotlib* axes instance or None (will create a new
            axes for the figure). The axes coordinate system will use equal
            aspect ratio. Defaults to None.
        **kwargs: Keyword arguments for ``plt.figure`` (called when ``fig`` is
            None) and *matplotlib* plotting functions.

    Returns:
        A tuple (fig, ax). To save the plot use ``fig.savefig("savename.png")``.
        The properties of fig and ax can be adjusted before showing.
    """
    fig, ax = default_fig_and_ax(fig, ax, figsize=figsize, dpi=dpi, layout=layout)
    # color_scheme = _merge_color_scheme(color_scheme)

    # plot billiard obstacles, balls and velocities
    plot_obstacles(bld, ax, color_scheme, **kwargs)
    plot_balls(bld, ax, color_scheme, **kwargs)
    plot_particles(bld, ax, particle_marker, particle_size, color_scheme, **kwargs)
    plot_velocities(bld, ax, arrow_size, color_scheme, **kwargs)

    # show the current simulation time
    text = f"Time: {bld.time:.3f}"
    ax.text(0.02, 0.95, text, transform=ax.transAxes)

    return fig, ax


def animate(
    bld,
    end_time,
    dt=1 / 30,
    particle_marker=".",
    particle_size=20,
    arrow_size=1.0,
    color_scheme=None,
    fig=None,
    ax=None,
    figsize=(8, 6),
    dpi=100,
    layout="tight",
    fps=30,
    blit=True,
    repeat=True,
    repeat_delay=0,
    **kwargs,
):
    """Animate the billiard plot.

    Advance the simulation from ``bld.time`` in steps of size ``dt`` until
    ``bld.time`` reaching ``end_time``. After every step, create a plot of the
    billiard simulation and assemble the plots into an animation. To display the
    animation, assign the returned animation instance to a variable (to prevent
    it from garbage-collection) and call ``matplotlib.pyplot.show()``.

    Will show a progress bar if the package *tqdm* is installed.

    Args:
        bld: A billiard simulation.
        end_time: The animation runs from ``t = bld.time`` until ``t = end_time``.
        dt (optional): Size of the timesteps. Defaults to 1 / 30.
        particle_marker (optional): A *matplotlib* marker style for the particles.
            Defaults to ".".
        particle_size (optional): The marker size in points**2. Defaults to 20.
        arrow_size (optional): The length of the velocity arrows is
            ``ball velocity * arrow_size``. A size of zero disables arrows.
            Defaults to 1.0.
        color_scheme (optional): Settings for the color of the billiard objects.
            The default values are taken from the global variable
            ``default_color_scheme`` (see its docstring for more info). Defaults
            to None (all colors are taken from the default color scheme).
        fig (optional): A *matplotlib* figure or None (will create a new
            figure). Defaults to None.
        ax (optional): A *matplotlib* axes instance or None (will create a new
            axes for the figure). The axes coordinate system will use equal
            aspect ratio. Defaults to None.
        **kwargs: Keyword arguments for ``plt.figure`` (called when ``fig`` is
            None), ``matplotlib.animation.FuncAnimation`` and plotting functions.

    Returns:
        A tuple (anim, fig, ax).

        The first element ``anim`` is a ``matplotlib.animation.FuncAnimation``
        instance. To play the animation, assign ``anim`` to a variable and call
        ``matplotlib.pyplot.show()``. To save it as a video use
        ``anim.save("videoname.mp4")``.

        The other elements (a ``matplotlib.figure.Figure`` and a
        ``matplotlib.axes.Axes`` instance) are the figure and axes that will be
        animated. Their properties can be adjusted before calling ``pyplot.show()``.
    """
    start_time = bld.time
    frames = int((end_time - start_time) / dt) + 1  # include end_time frame

    # precompute the simulation
    time = []
    positions = []
    velocities = []
    for i in trange(frames):
        bld.evolve(start_time + i * dt)

        time.append(bld.time)
        positions.append(bld.balls_position.copy())
        velocities.append(bld.balls_velocity.copy())

    # setup plot
    fig, ax = default_fig_and_ax(fig, ax, figsize=figsize, dpi=dpi, layout=layout)
    # color_scheme = _merge_color_scheme(color_scheme)

    # plot billiard obstacle and balls
    plot_obstacles(bld, ax, color_scheme, **kwargs)
    circles = plot_balls(bld, ax, color_scheme, **kwargs)
    points = plot_particles(
        bld, ax, particle_marker, particle_size, color_scheme, **kwargs
    )
    arrows = plot_velocities(bld, ax, arrow_size, color_scheme, **kwargs)

    # show the current simulation time
    text = f"Time: {bld.time:.3f}"
    time_text = ax.text(0.02, 0.95, text, transform=ax.transAxes)

    # draw point particles only as markers
    draw_as_circles = np.asarray(bld.balls_radius) > 0
    draw_as_markers = np.logical_not(draw_as_circles)
    draw_velocities = np.full(bld.num, True, dtype=bool)

    # remove balls and arrows where color is set to None
    color_scheme = _merge_color_scheme(color_scheme)
    default_ball_color = color_scheme["balls"]
    default_particle_color = color_scheme["particles"]
    for i in range(bld.num):
        if bld.balls_radius[i] > 0:
            c = color_scheme.get(i, default_ball_color)
        else:
            c = color_scheme.get(i, default_particle_color)

        if c is None:
            draw_as_circles[i] = False
            draw_as_markers[i] = False
            draw_velocities[i] = False
        elif isinstance(c, tuple) and len(c) == 2:
            # note matplotlib>=3.8: c could also be (color, alpha) tuple
            if c[0] is None:
                draw_as_circles[i] = False
                draw_as_markers[i] = False
            if c[1] is None:
                draw_velocities[i] = False

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
    def func(i):
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
            arrows.set_offsets(pos[draw_velocities])
            vel = velocities[i]
            arrows.set_UVC(vel[draw_velocities, 0], vel[draw_velocities, 1])
            ret += (arrows,)

        return ret

    anim = manimation.FuncAnimation(
        fig,
        func,
        frames,
        interval=1000 / fps,
        blit=blit,
        init_func=init,
        repeat=repeat,
        repeat_delay=repeat_delay,
        cache_frame_data=False,  # to save memory
    )

    return anim, fig, ax
