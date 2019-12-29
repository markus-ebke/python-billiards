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

    import pyglet
    from pyglet import gl
except ImportError as ex:  # pragma: no cover
    print("Cannot use billiards.visualize, matplotlib or pyglet is not found.")
    raise ex


class BallCollection(Collection):
    """A collection of balls (in data coordinates, like EllipseCollection)."""

    def __init__(self, centers, radii, transOffset, **kwargs):
        """Create balls with given centers and radii."""
        self.radii = np.asarray(radii)

        kwargs["offsets"] = centers
        kwargs["transOffset"] = transOffset
        Collection.__init__(self, **kwargs)

        self._unit_circle = Path.unit_circle()
        self._paths = [self._unit_circle]

    def _set_transforms(self, transData):
        self._transforms = np.zeros((len(self.radii), 3, 3))
        self._transforms[:, 0, 0] = self.radii
        self._transforms[:, 1, 1] = self.radii
        self._transforms[:, 2, 2] = 1.0

        trafo = transData.get_affine()
        m = trafo.get_matrix().copy()
        m[:2, 2:] = 0
        self.set_transform(transforms.Affine2D(m))

    def get_datalim(self, transData):
        """Get bounding box of the collection in data coordinates."""
        self._set_transforms(transData)
        transform = self.get_transform()
        self._paths = [transform.transform_path(self._unit_circle)]
        return Collection.get_datalim(self, transData)

    @allow_rasterization
    def draw(self, renderer):
        """Set transform, then draw."""
        self._set_transforms(self.axes.transData)
        self._paths = [self._unit_circle]
        Collection.draw(self, renderer)


class BallPatchCollection(Collection):
    """A collection of ball patches (in data coordinates).

    Will be slower than BallPatchCollection, but can be used for comparison.

    """

    def __init__(self, centers, radii, **kwargs):
        """Create balls with given centers and radii."""
        Collection.__init__(self, **kwargs)

        unit_circle = Path.unit_circle()
        paths = []
        for c, r in zip(centers, radii):
            transform = transforms.Affine2D().scale(r).translate(*c)
            paths.append(transform.transform_path(unit_circle))
        self._paths = paths


def _plot_frame(bld, fig, ax):
    # setup figure and axes if needed
    if fig is None:
        fig = plt.figure(figsize=(8, 6), dpi=100)
        fig.set_tight_layout(True)

    if ax is None:
        ax = fig.add_subplot(1, 1, 1, aspect="equal", adjustable="datalim")

    # simplify variables
    pos = bld.balls_position
    vel = bld.balls_velocity

    # draw balls as circles
    balls = BallCollection(
        centers=pos,
        radii=bld.balls_radius,
        transOffset=ax.transData,
        edgecolor="black",
        linewidth=1,
        zorder=0,
    )
    ax.add_collection(balls)
    ax.autoscale_view()

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
        0.02, 0.95, "Time: {:.3f}".format(bld.time), transform=ax.transAxes
    )

    return fig, ax, balls, scatter, quiver, time_text


def plot(bld, fig=None, ax=None, show=True):
    """Plot the given billiard for the current moment.

    Args:
        bld: A billiard simulation.
        fig (optional): Figure used for drawing.
            Defaults to None in which case a new figure will be created.
        ax (optional): Axes used for drawing.
            Defaults to None in which case a nex axes object will be created.
            If an axes object is supplied, use
            ax.set_aspect(self, aspect="equal", adjustable="datalim")
            for correct aspect ratio.
        show (optional): Use pyplot.show() to show the animation.

    Returns:
        matplotlib.figure.Figure: Figure used for drawing, to save the plot use
        show=False and fig.savefig("savename.png").

    """
    fig, ax, balls, scatter, quiver, time_text = _plot_frame(bld, fig, ax)

    if show:  # pragma: no cover
        plt.show()

    return fig


def animate(bld, end_time, fps=30, fig=None, ax=None, show=True):
    """Animate the billiard plot.

    Note that you have to assign the returned anim object to a variable,
    otherwise it gets garbage collected and the animation does not update.

    Args:
        bld: A billiard simulation.
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
        matplotlib.figure.Figure: Figure used for drawing.
        matplotlib.animation.FuncAnimation: Animation object, to save the
        animation use show=False and anim.save("savename.mp4").

    """
    frames = int(fps * end_time)

    # precompute the simulation
    time = []
    positions = []
    velocities = []
    for i in range(frames):
        bld.evolve(i / fps)

        time.append(bld.time)
        positions.append(bld.balls_position.copy())
        velocities.append(bld.balls_velocity.copy())

    # setup plot
    fig, ax, balls, scatter, quiver, time_text = _plot_frame(bld, fig, ax)

    def init():
        balls.set_offsets(np.empty(shape=(0, 2)))
        scatter.set_offsets(np.empty(shape=(0, 2)))
        quiver.set_offsets(np.empty(shape=(0, 2)))
        quiver.set_UVC(np.empty(shape=(0, 1)), np.empty(shape=(0, 1)))

        time_text.set_text("")

        return (balls, scatter, quiver, time_text)

    # animate will play the precomputed simulation
    def animate(i):
        t = time[i]
        pos = positions[i]
        vel = velocities[i]

        balls.set_offsets(pos)
        scatter.set_offsets(pos)
        quiver.set_offsets(pos)
        quiver.set_UVC(vel[:, 0], vel[:, 1])

        time_text.set_text("time = {:.2f}s".format(t))

        return (balls, scatter, quiver, time_text)

    anim = FuncAnimation(
        fig, animate, frames, interval=1000 / fps, blit=True, init_func=init,
    )

    if show:  # pragma: no cover
        plt.show()

    return (fig, anim)


def _circle_model(radius, num_points=16):
    """Vertices and order in which to draw lines for a circle."""
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


def interact(bld, fullscreen=False):  # pragma: no cover
    """Interact with the billiard simulation.

    Args:
        bld: A billiard simulation.
        fullscreen (optional): Set window to fullscreen, defaults to False.

    """
    # create window
    window = pyglet.window.Window(width=800, height=600, visible=False)
    if fullscreen:
        window.set_fullscreen()

    # OpenGL settings for high quality line drawing
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    gl.glEnable(gl.GL_LINE_SMOOTH)
    gl.glHint(pyglet.gl.GL_LINE_SMOOTH_HINT, gl.GL_NICEST)
    gl.glLineWidth(2)

    # add balls to pyglet batch for drawing and vlist for updating
    balls_batch = pyglet.graphics.Batch()
    balls_model = []
    for idx in range(bld.num):
        vertices, indices = _circle_model(bld.balls_radius[idx])

        vlist = balls_batch.add_indexed(
            len(vertices), gl.GL_LINES, None, indices, "v2f/stream"
        )
        balls_model.append([vertices, vlist])

    # for recording statistics
    frame = 0
    elapsed = 0.0
    bounces = []

    # display statistics
    gui_batch = pyglet.graphics.Batch()
    frame_template = "Frame: {} ({:.2f} s)"
    frame_label = pyglet.text.Label(
        text=frame_template, x=2, y=window.height - 20, batch=gui_batch
    )
    time_template = "dt: {:.2f} ms, fps: {:.1f}"
    time_label = pyglet.text.Label(
        text=time_template, x=2, y=window.height - 40, batch=gui_batch
    )
    bld_template = "Time: {:.3f}, bounces: {}"
    bld_label = pyglet.text.Label(
        text=bld_template, x=2, y=window.height - 60, batch=gui_batch
    )

    # window coordinate system
    center = np.asarray([window.width, window.height]) / 2
    zoom = 10

    # interaction
    paused = False

    def update(dt):
        nonlocal frame, elapsed
        frame += 1
        elapsed += dt

        if not paused:
            # simulate with fixed timestep
            collisions = bld.evolve(bld.time + 1 / 60)
            bounces.append(len(collisions))

        # update ball vertices
        for idx, (vertices, vlist) in enumerate(balls_model):
            pos = bld.balls_position[idx]
            verts = zoom * (vertices + pos) + center
            vlist.vertices[:] = verts.flatten()

        # draw statistics
        fps = pyglet.clock.get_fps()
        frame_label.text = frame_template.format(frame, elapsed)
        time_label.text = time_template.format(dt * 1000, fps)
        bld_label.text = bld_template.format(bld.time, bounces[-1])

    key = pyglet.window.key

    @window.event
    def on_key_press(symbol, modifiers):
        nonlocal paused, center, zoom
        speed = window.height / 20
        mag = 2 ** 0.5

        if symbol == key.SPACE:
            paused = not paused
            print("Pause" if paused else "Unpause")
        elif symbol == key.W:
            center[1] -= speed
        elif symbol == key.S:
            center[1] += speed
        elif symbol == key.A:
            center[0] += speed
        elif symbol == key.D:
            center[0] -= speed
        elif symbol == key.Q:
            zoom *= mag
        elif symbol == key.E:
            zoom /= mag

    @window.event
    def on_draw():
        window.clear()
        balls_batch.draw()
        gui_batch.draw()

    # shedule updates at 60 fps or as fast as the screen updates
    if window.vsync:
        pyglet.clock.schedule(update)  # will be called only once per frame
    else:
        pyglet.clock.schedule_interval(update, 1 / 60)

    # show window, start simulation
    window.set_visible()
    pyglet.app.run()
