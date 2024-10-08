"""Visualize a billiard simulation using pyglet.

Usage (assuming ``bld`` is an instance of the ``Billiard`` class)::

    import pyglet
    from billiards import visualize_pyglet

    visualize_pyglet.interact(bld)

This will create a pyglet Window, print keyboard controls to the console and
call `pyglet.app.run()`.
"""

# import warnings
from collections import deque
from math import isfinite
from statistics import mean
from time import perf_counter as clock

from .simulation import Billiard

try:
    import pyglet
    from pyglet.window import key

    # from pyglet import gl
except Exception as ex:
    print(repr(ex))
    # When testing with tox this happens:
    # pyglet.canvas.xlib.NoSuchDisplayException: Cannot connect to "None"
    # I don't know how to prevent it, except with this hacky except case
#     warnings.warn(
#         f"Imported pyglet, but then something went wrong: {repr(ex)}", stacklevel=1
#     )
#     Window = object  # mock window


class BilliardWindow(pyglet.window.Window):
    """Custom window class for interacting with billiard simulations."""

    help = """
Keyboard controls:
SPACE: pause/unpause
-(MINUS): advance one frame (when paused)
+(PLUS): advance to the next collision (when paused)
.(PERIOD) and ,(COMMA): increase and decrease simulation speed
WASD: Pan camera                           QE: Zoom in and out
ESC: close window and exit"""

    def __init__(self, billiard, *args, **kwargs):
        """Create a window for showing the given billiard simulation.

        Args:
            billiard: An instance of simulation.Billiard ready to be simulated.
            *args: Further argument passed to `pyglet.window.Window`

        Keyword Args:
            camera_position: A tuple (x, y) for the center of the camera in the
                `billiard` coordinate system. Defaults to (0, 0).
            camera_width: The width of the displayed area in the `billiard`
                coordinate system. Defaults to 1.0.
            simulation_speed: The rate of change of `billiard.time` compared to
                realtime. Defaults to 1.0.
            **kwargs: Further arguments passed to `pyglet.window.Window`.

        Raises:
            TypeError: If `billiard` is not an instance of simulation.Billiard.
            ValueError: If `camera_position` is not of length 2 or does not
                contain finite numbers. If `camera_width` is not a positive
                finite number.
        """
        # Set up pyglet window, but remove unrelated keyword arguments
        camera_position = kwargs.pop("camera_position", (0, 0))
        camera_width = float(kwargs.pop("camera_width", 1.0))
        simulation_speed = kwargs.pop("simulation_speed", 1.0)
        super().__init__(*args, **kwargs)

        # Billiard attributes
        if not isinstance(billiard, Billiard):
            msg = f"Expected a simulation.Billiard instance, but got {type(billiard)}"
            raise TypeError(msg)
        self.billiard = billiard

        # Camera coordinate system
        # TODO compute size of billiard and use it as default values for camera_position
        # and camera_width
        self.camera_position = [float(c) for c in camera_position]
        if len(self.camera_position) != 2:
            msg = f"Camera position must be length 2, not {len(self.camera_position)}"
            raise ValueError(msg)
        if not all(map(isfinite, self.camera_position)):
            msg = f"Camera position contains a non-finite number {self.camera_position}"
            raise ValueError(msg)

        self.camera_width = float(camera_width)
        if not (isfinite(self.camera_width) and self.camera_width > 0.0):
            msg = f"Camera width must be positive and finite, not {self.camera_width}"
            raise ValueError(msg)

        # Presentation settings
        self.running = False
        self.advance_one_frame = False  # used when running=False
        self.advance_to_next_collision = False  # used when running=False
        self.simulation_speed = float(simulation_speed)
        self.bounces = deque(maxlen=60)  # record number of bounces in the last second

        # Timing information
        self.timing_simulate = deque(maxlen=100)
        self.timing_draw = deque(maxlen=100)

        # Information display
        self.label_info = pyglet.text.Label(
            "",
            font_name=["Ubuntu Mono", "DejaVu Sans Mono", "Lucida Console", "Consolas"],
            font_size=14,
            x=4,
            y=self.height - 4,
            anchor_x="left",
            anchor_y="top",
            multiline=True,
            width=self.width - 8,
            color=(200, 200, 200, 255),
        )

        # FPS display
        self.fps_display = pyglet.window.FPSDisplay(self, samples=60)
        fps_label = self.fps_display.label
        fps_label.x = self.width - 4
        fps_label.y = self.height
        fps_label.anchor_x = "right"
        fps_label.anchor_y = "top"

        # OpenGL settings for high quality line drawing
        # gl.glEnable(gl.GL_BLEND)
        # gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        # gl.glEnable(gl.GL_LINE_SMOOTH)
        # gl.glHint(pyglet.gl.GL_LINE_SMOOTH_HINT, gl.GL_NICEST)
        # gl.glLineWidth(2)

        # # marker for point particles
        # self.marker_size = 4  # diameter in pixels
        # self.marker_model = circle_model(radius=1 / 2, num_points=16)
        # self.marker_indices = []  # indices of the point particles in billiard

        # # setup drawing
        # self._setup_batches()
        # self._setup_gui()

        # # resize the window to include every object
        # self.autoscale()
        # self.resize_marker(self.marker_size)

        self.keyboard_state = key.KeyStateHandler()
        self.push_handlers(self.keyboard_state)

        # Schedule simulation updates at 60 fps
        pyglet.clock.schedule_interval(self.update, 1 / 60)

    # def _setup_batches(self):
    #     # batch for drawing obstacles
    #     self.obs_batch = pyglet.graphics.Batch()
    #     obs_models = []  # obstacle vertices (in model coordinates) and vlists
    #     for obs in self.bld.obstacles:
    #         vertices, indices, mode = obs.model()
    #         vlist = self.obs_batch.add_indexed(
    #             len(vertices),
    #             mode,
    #             None,
    #             indices,
    #             "v2f/static",
    #         )
    #         vlist.vertices[:] = vertices.flatten()
    #         obs_models.append([vertices, vlist])
    #     self.obs_batch.models = obs_models

    #     # add balls to pyglet batch for drawing and vlist for updating
    #     self.ball_batch = pyglet.graphics.Batch()
    #     ball_models = []  # ball vertices (in model coordinates) and vlists
    #     for idx in range(self.bld.num):
    #         radius = self.bld.balls_radius[idx]
    #         if radius > 0:
    #             # proper circle
    #             vertices, indices = circle_model(radius)
    #         else:
    #             # point particle marker
    #             vertices, indices = self.marker_model
    #             self.marker_indices.append(idx)

    #         vlist = self.ball_batch.add_indexed(
    #             len(vertices), gl.GL_LINES, None, indices, "v2f/stream"
    #         )
    #         ball_models.append([vertices, vlist])
    #     self.ball_batch.models = ball_models

    # def _setup_gui(self):
    #     # for recording statistics
    #     self.frame = 0
    #     self.bounces = []

    #     # display statistics
    #     self.gui_batch = pyglet.graphics.Batch()

    #     self.label_bld = pyglet.text.Label(
    #         text="", x=7, y=self.height - 20, batch=self.gui_batch
    #     )
    #     self.label_coord = pyglet.text.Label(
    #         text="", x=7, y=self.height - 40, batch=self.gui_batch
    #     )
    #     self.label_update = pyglet.text.Label(
    #         text="", x=7, y=self.height - 60, batch=self.gui_batch
    #     )

    # def autoscale(self):
    #     """Show the whole billiard table."""
    #     # Calculate the biggest rectangle that includes every object
    #     xmin, ymin, xmax, ymax = -1.0, -1.0, 1.0, 1.0

    #     def include(vertices):
    #         nonlocal xmin, ymin, xmax, ymax
    #         # rectangle around the object
    #         model_xmin, model_ymin = vertices.min(axis=0)
    #         model_xmax, model_ymax = vertices.max(axis=0)

    #         # update biggest rectangle
    #         xmin = min(xmin, model_xmin)
    #         ymin = min(ymin, model_ymin)
    #         xmax = max(xmax, model_xmax)
    #         ymax = max(ymax, model_ymax)

    #     # include every obstacle
    #     for vertices, _vlist in self.obs_batch.models:
    #         include(vertices)

    #     # include every (proper) ball
    #     ball_models = self.ball_batch.models
    #     balls_position = self.bld.balls_position
    #     all_balls = set(range(len(ball_models)))  # use set for fast exclusion
    #     not_proper = set(self.marker_indices)
    #     for idx in all_balls - not_proper:
    #         vertices, vlist = ball_models[idx]
    #         include(vertices + balls_position[idx])

    #     # set center and extent to show the whole rectangle
    #     self.center = [(xmin + xmax) / 2, (ymin + ymax) / 2]
    #     self.extent = max(xmax - xmin, (ymax - ymin) / self.aspect_ratio)
    #     assert self.extent > 0.0, (xmin, ymin, xmax, ymax)

    # def resize_marker(self, diameter):
    #     """Resize markers for point particles."""
    #     marker_vertices, indices = self.marker_model
    #     size_of_pixel = self.extent / self.width
    #     vertices = diameter * size_of_pixel * marker_vertices

    #     ball_models = self.ball_batch.models
    #     for idx in self.marker_indices:
    #         ball_models[idx][0] = vertices

    def on_key_press(self, symbol, modifiers):
        """Handle key press on the keyboard."""
        super().on_key_press(symbol, modifiers)

        if symbol == key.SPACE:
            self.running = not self.running
        if symbol == key.MINUS:
            self.advance_one_frame = True
        if symbol == key.PLUS:
            self.advance_to_next_collision = True

    def on_resize(self, width, height):
        """Handle window resize event."""
        super().on_key_press(width, height)

        # move labels
        self.label_info.x = 4
        self.label_info.y = self.height - 4

        fps_label = self.fps_display.label
        fps_label.x = self.width - 4
        fps_label.y = self.height

    def on_draw(self):
        """Redraw the window contents."""
        self.clear()

        # viewport = self.get_viewport_size()
        # gl.glViewport(0, 0, max(1, viewport[0]), max(1, viewport[1]))

        # # set projection for billiard table
        # gl.glMatrixMode(gl.GL_PROJECTION)
        # gl.glLoadIdentity()
        # gl.glOrtho(
        #     self.center[0] - self.extent / 2,
        #     self.center[0] + self.extent / 2,
        #     self.center[1] - self.extent / (2 * self.aspect_ratio),
        #     self.center[1] + self.extent / (2 * self.aspect_ratio),
        #     -1,
        #     1,
        # )

        # # draw balls and obstacles
        # gl.glMatrixMode(gl.GL_MODELVIEW)
        # gl.glLoadIdentity()
        # self.obs_batch.draw()
        # self.ball_batch.draw()

        # # set projection for GUI
        # gl.glMatrixMode(gl.GL_PROJECTION)
        # gl.glLoadIdentity()
        # gl.glOrtho(0, max(1, self.width), 0, max(1, self.height), -1, 1)

        # # draw GUI
        # gl.glMatrixMode(gl.GL_MODELVIEW)
        # gl.glLoadIdentity()
        # self.gui_batch.draw()

        self.label_info.draw()
        self.fps_display.draw()

    def update(self, dt):
        """Update the camera, the simulation and the GUI."""
        dt = min(dt, 0.2)  # not slower than 5 fps
        keys = self.keyboard_state

        # Update camera position
        panning_speed = 1.0 * self.camera_width
        if keys[key.A]:  # left
            self.camera_position[0] -= panning_speed * dt
        if keys[key.D]:  # right
            self.camera_position[0] += panning_speed * dt
        if keys[key.W]:  # up
            self.camera_position[1] += panning_speed * dt
        if keys[key.S]:  # down
            self.camera_position[1] -= panning_speed * dt

        # Update camera zoom
        zoom = 2.0**dt
        if keys[key.Q]:
            self.camera_width /= zoom  # decrease width = magnify / zoom in
        if keys[key.E]:
            self.camera_width *= zoom  # increase width = zoom out

        # Update simulation speed
        sim_accel = 2.0**dt
        if keys[key.PERIOD]:  # accelerate
            self.simulation_speed *= sim_accel
        if keys[key.COMMA]:  # decelerate
            self.simulation_speed /= sim_accel

        # Update simulation
        stale = False
        if self.running or self.advance_one_frame:
            tic = clock()
            end_time = self.billiard.time + self.simulation_speed * dt
            collisions = self.billiard.evolve(end_time)
            self.timing_simulate.append(clock() - tic)
            stale = True

            self.bounces.append((self.billiard.time, collisions[0], collisions[1]))
            self.advance_one_frame = False
        elif self.advance_to_next_collision:
            if self.billiard.next_collision[0] < float("inf"):
                tic = clock()
                collisions = self.billiard.evolve(self.billiard.next_collision[0])
                self.timing_simulate.append(clock() - tic)
                stale = True

                self.bounces.append((self.billiard.time, collisions[0], collisions[1]))

            self.advance_to_next_collision = False

        if stale:
            # update ball positions on GPU
            """
            balls_position = self.bld.balls_position
            ball_models = self.ball_batch.models

            # update ball vertices
            for idx, (model_vertices, vlist) in enumerate(ball_models):
                vertices = model_vertices + balls_position[idx]
                vlist.vertices[:] = vertices.flatten()

            # update point particle markers after zooming, even when paused
            for idx in self.marker_indices:
                model_vertices, vlist = ball_models[idx]
                vertices = model_vertices + balls_position[idx]
                vlist.vertices[:] = vertices.flatten()
            """

        # Update GUI

        # First line: simulation info
        timeframe, ball_bounces, obstacle_bounces = 0.0, 0, 0
        for t, b, o in self.bounces:
            timeframe += t
            ball_bounces += b
            obstacle_bounces += o
        bb_per_sec = ball_bounces / timeframe if timeframe > 0 else float("nan")
        ob_per_sec = obstacle_bounces / timeframe if timeframe > 0 else float("nan")
        info = [
            f"Time: {self.billiard.time:.3f} (x{self.simulation_speed:.4})",
            f"Bounces: {bb_per_sec:.2f}, {ob_per_sec:.2f} per second",
        ]
        first_line = "    ".join(info)

        # Second line: camera info
        cx, cy = self.camera_position
        second_line = f"Camera: [{cx:.2f}, {cy:.2f}], Width: {self.camera_width:.2f}"

        # Third line: timing info
        time_sim = mean(self.timing_simulate) if self.timing_simulate else 0.0
        time_draw = mean(self.timing_draw) if self.timing_draw else 0.0
        info = [
            f"Simulate: {time_sim * 1000:.1f} ms",
            f"Draw: {time_draw * 1000:.1f} ms",
        ]
        third_line = "    ".join(info)

        # Assemble complete text
        self.label_info.text = "\n".join([first_line, second_line, third_line])


def interact(billiard, *args, **kwargs):
    """Interact with the billiard simulation.

    Will create a pyglet window, print instructions to the console and call
    `pyglet.app.run()` (which blocks until the window is closed).

    See docstring of `BilliardWindow.__init__` for accepted arguments.
    """
    bldwin = BilliardWindow(billiard, *args, **kwargs)
    print(bldwin.help)
    pyglet.app.run()
