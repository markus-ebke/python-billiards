"""Visualize a billiard table using matplotlib and pyglet.

With matplotlib (assuming ``bld`` is an instance of the ``Billiard`` class)::

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

With pyglet::

    billiards.visualize.interact(bld)

Instructions are printed to the console window.
"""

import warnings

import numpy as np

from .obstacles import circle_model

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

try:
    import pyglet
    from pyglet import gl
    from pyglet.window import Window, key
except ImportError:  # pragma: no cover
    warnings.warn(
        "Could not import pyglet, 'visualize.interact' will not work.", stacklevel=1
    )
except Exception as ex:  # pragma: no cover
    # When testing with tox this happens:
    # pyglet.canvas.xlib.NoSuchDisplayException: Cannot connect to "None"
    # I don't know how to prevent it, except with this hacky except case
    warnings.warn(
        f"Imported pyglet, but then something went wrong: {repr(ex)}", stacklevel=1
    )
    Window = object  # mock window


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


class BilliardWindow(Window):  # pragma: no cover
    """Custom window class for interacting with billiard simulations."""

    def __init__(self, bld, *args, **kwargs):
        """Set up pyglet window."""
        super().__init__(*args, **kwargs)
        self.bld = bld

        # viewport coordinate system
        self.aspect_ratio = self.width / self.height
        self.center = [0.0, 0.0]  # point in the middle of the viewport
        self.extent = 1.0  # width of visible area

        # interaction
        self.pause = False
        self.move = [0.0, 0.0, 0.0]  # change center and extent between frames
        self.simspeed = 1.0  # simulation speedup
        self.simaccel = 0.0  # change simulation speed

        # marker for point particles
        self.marker_size = 4  # diameter in pixels
        self.marker_model = circle_model(radius=1 / 2, num_points=16)
        self.marker_indices = []  # indices of the point particles in billiard

        # setup drawing
        self._setup_batches()
        self._setup_gui()

        # resize the window to include every object
        self.autoscale()
        self.resize_marker(self.marker_size)

        # schedule updates at 60 fps or as fast as the screen flips
        if self.vsync:
            # will be called only once per frame
            pyglet.clock.schedule(self.update)
        else:
            pyglet.clock.schedule_interval(self.update, 1 / 60)

    def _setup_batches(self):
        # batch for drawing obstacles
        self.obs_batch = pyglet.graphics.Batch()
        obs_models = []  # obstacle vertices (in model coordinates) and vlists
        for obs in self.bld.obstacles:
            vertices, indices, mode = obs.model()
            vlist = self.obs_batch.add_indexed(
                len(vertices),
                mode,
                None,
                indices,
                "v2f/static",
            )
            vlist.vertices[:] = vertices.flatten()
            obs_models.append([vertices, vlist])
        self.obs_batch.models = obs_models

        # add balls to pyglet batch for drawing and vlist for updating
        self.ball_batch = pyglet.graphics.Batch()
        ball_models = []  # ball vertices (in model coordinates) and vlists
        for idx in range(self.bld.num):
            radius = self.bld.balls_radius[idx]
            if radius > 0:
                # proper circle
                vertices, indices = circle_model(radius)
            else:
                # point particle marker
                vertices, indices = self.marker_model
                self.marker_indices.append(idx)

            vlist = self.ball_batch.add_indexed(
                len(vertices), gl.GL_LINES, None, indices, "v2f/stream"
            )
            ball_models.append([vertices, vlist])
        self.ball_batch.models = ball_models

    def _setup_gui(self):
        # for recording statistics
        self.frame = 0
        self.bounces = []

        # display statistics
        self.gui_batch = pyglet.graphics.Batch()

        self.label_bld = pyglet.text.Label(
            text="", x=7, y=self.height - 20, batch=self.gui_batch
        )
        self.label_coord = pyglet.text.Label(
            text="", x=7, y=self.height - 40, batch=self.gui_batch
        )
        self.label_update = pyglet.text.Label(
            text="", x=7, y=self.height - 60, batch=self.gui_batch
        )

    def autoscale(self):
        """Show the whole billiard table."""
        # Calculate the biggest rectangle that includes every object
        xmin, ymin, xmax, ymax = -1.0, -1.0, 1.0, 1.0

        def include(vertices):
            nonlocal xmin, ymin, xmax, ymax
            # rectangle around the object
            model_xmin, model_ymin = vertices.min(axis=0)
            model_xmax, model_ymax = vertices.max(axis=0)

            # update biggest rectangle
            xmin = min(xmin, model_xmin)
            ymin = min(ymin, model_ymin)
            xmax = max(xmax, model_xmax)
            ymax = max(ymax, model_ymax)

        # include every obstacle
        for vertices, _vlist in self.obs_batch.models:
            include(vertices)

        # include every (proper) ball
        ball_models = self.ball_batch.models
        balls_position = self.bld.balls_position
        all_balls = set(range(len(ball_models)))  # use set for fast exclusion
        not_proper = set(self.marker_indices)
        for idx in all_balls - not_proper:
            vertices, vlist = ball_models[idx]
            include(vertices + balls_position[idx])

        # set center and extent to show the whole rectangle
        self.center = [(xmin + xmax) / 2, (ymin + ymax) / 2]
        self.extent = max(xmax - xmin, (ymax - ymin) / self.aspect_ratio)
        assert self.extent > 0.0, (xmin, ymin, xmax, ymax)

    def resize_marker(self, diameter):
        """Resize markers for point particles."""
        marker_vertices, indices = self.marker_model
        size_of_pixel = self.extent / self.width
        vertices = diameter * size_of_pixel * marker_vertices

        ball_models = self.ball_batch.models
        for idx in self.marker_indices:
            ball_models[idx][0] = vertices

    def on_key_press(self, symbol, modifiers):
        """Handle key press."""
        super().on_key_press(symbol, modifiers)

        if symbol == key.SPACE:
            self.pause = not self.pause
            print(f"Pause: {self.pause}")
        elif symbol == key.W:
            self.move[1] += 1
        elif symbol == key.S:
            self.move[1] -= 1
        elif symbol == key.A:
            self.move[0] -= 1
        elif symbol == key.D:
            self.move[0] += 1
        elif symbol == key.Q:
            self.move[2] += 1
        elif symbol == key.E:
            self.move[2] -= 1
        elif symbol == key.R:
            self.simaccel += 1
        elif symbol == key.F:
            self.simaccel -= 1

    def on_key_release(self, symbol, modifiers):
        """Handle key release."""
        if symbol == key.W:
            self.move[1] -= 1
        elif symbol == key.S:
            self.move[1] += 1
        elif symbol == key.A:
            self.move[0] += 1
        elif symbol == key.D:
            self.move[0] -= 1
        elif symbol == key.Q:
            self.move[2] -= 1
        elif symbol == key.E:
            self.move[2] += 1
        elif symbol == key.R:
            self.simaccel -= 1
        elif symbol == key.F:
            self.simaccel += 1

    def on_resize(self, width, height):
        """Adjust window content when resized."""
        # update viewport aspect ratio
        self.aspect_ratio = width / height

        # move labels
        self.label_bld.y = self.height - 20
        self.label_coord.y = self.height - 40
        self.label_update.y = self.height - 60

    def on_draw(self):
        """Draw window."""
        self.clear()

        viewport = self.get_viewport_size()
        gl.glViewport(0, 0, max(1, viewport[0]), max(1, viewport[1]))

        # set projection for billiard table
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(
            self.center[0] - self.extent / 2,
            self.center[0] + self.extent / 2,
            self.center[1] - self.extent / (2 * self.aspect_ratio),
            self.center[1] + self.extent / (2 * self.aspect_ratio),
            -1,
            1,
        )

        # draw balls and obstacles
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        self.obs_batch.draw()
        self.ball_batch.draw()

        # set projection for GUI
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(0, max(1, self.width), 0, max(1, self.height), -1, 1)

        # draw GUI
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        self.gui_batch.draw()

    def update(self, dt):
        """Update the window."""
        self.frame += 1

        # smoothly update viewport coordinate system
        smooth_dt = min(dt, 0.2)  # not slower than 5 fps
        speed, zoom = self.extent, 1.0  # speed of moving and zooming
        self.center[0] += self.move[0] * speed * smooth_dt
        self.center[1] += self.move[1] * speed * smooth_dt
        self.extent *= 1 + self.move[2] * zoom * min(smooth_dt, 1 / (2 * zoom))
        assert self.extent > 0.0, (self.move[2], zoom, smooth_dt)
        if self.move[2] != 0.0:
            # need to change size of markers after zooming
            self.resize_marker(self.marker_size)

        # update simulation speed
        accelfac = 1.0  # speed of changing the simulation speed
        self.simspeed *= 1 + self.simaccel * accelfac * smooth_dt

        # update billiard simulation
        balls_position = self.bld.balls_position
        ball_models = self.ball_batch.models
        if not self.pause:
            # simulate with fixed timestep
            collisions = self.bld.evolve(self.bld.time + self.simspeed / 60)
            self.bounces.append(collisions)

            # update ball vertices
            for idx, (model_vertices, vlist) in enumerate(ball_models):
                vertices = model_vertices + balls_position[idx]
                vlist.vertices[:] = vertices.flatten()
        elif self.move[2] != 0:
            # update point particle markers after zooming, even when paused
            for idx in self.marker_indices:
                model_vertices, vlist = ball_models[idx]
                vertices = model_vertices + balls_position[idx]
                vlist.vertices[:] = vertices.flatten()

        # update gui
        txt = "Time: {:6.3} (x{:.4}), bounces: {}"
        self.label_bld.text = txt.format(self.bld.time, self.simspeed, self.bounces[-1])
        txt = "Center: ({:.1f}, {:.1f}), extent: {:.4}"
        self.label_coord.text = txt.format(self.center[0], self.center[1], self.extent)
        txt = "Frame: {}, fps: {:.1f} ({:.2f} ms)"
        self.label_update.text = txt.format(
            self.frame, pyglet.clock.get_fps(), dt * 1000
        )


def interact(bld, fullscreen=False):  # pragma: no cover
    """Interact with the billiard simulation.

    Args:
        bld: A billiard simulation.
        fullscreen (optional): Set window to fullscreen, defaults to False.

    """
    if Window is object:
        raise RuntimeError("Something went wrong with pyglet, see import warning")

    # print instructions
    print("Play/Pause: Space, move: WASD, zoom: QE, simspeed: RF, exit: Esc")

    # create window
    window = BilliardWindow(bld, width=800, height=600, resizable=True)
    if fullscreen:
        window.set_fullscreen()

    # OpenGL settings for high quality line drawing
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    gl.glEnable(gl.GL_LINE_SMOOTH)
    gl.glHint(pyglet.gl.GL_LINE_SMOOTH_HINT, gl.GL_NICEST)
    gl.glLineWidth(2)

    # show window, start simulation
    pyglet.app.run()
