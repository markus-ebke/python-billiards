"""Visualize a billiard simulation using pyglet.

Usage (assuming ``bld`` is an instance of the ``Billiard`` class)::

    import pyglet
    from billiards import visualize_pyglet

    visualize_pyglet.interact(bld)

This will create a pyglet Window, print keyboard controls to the console and
call `pyglet.app.run()`.
"""

import ctypes
from collections import deque
from math import cos, isfinite, pi, sin, sqrt
from statistics import mean
from time import perf_counter as clock

import numpy as np

from .obstacles import Disk, InfiniteWall, LineSegment
from .simulation import Billiard

try:
    import pyglet
    from pyglet import gl, shapes
    from pyglet.graphics import Group
    from pyglet.graphics.shader import Shader, ShaderProgram
    from pyglet.window import key
except Exception as ex:
    print(repr(ex))
    # When testing with tox this happens:
    # pyglet.canvas.xlib.NoSuchDisplayException: Cannot connect to "None"
    # I don't know how to prevent it, except with this hacky except case
#    import warnings
#     warnings.warn(
#         f"Imported pyglet, but then something went wrong: {repr(ex)}", stacklevel=1
#     )
#     Window = object  # mock window


###############################################################################
# Helper functions
###############################################################################


def model_circle_line(radius, segments=32):
    """Vertices and order in which to draw lines for a circle.

    Args:
        radius: Radius of the circle.
        num_points: Number of vertices of the circle.

    Returns:
        np.ndarray: Position of the vertices in a Nx2-shaped array.
        list: Indices indicating the start and endpoints of lines that will
        form the circle, has length 2N.
    """
    # Place vertices on the circle
    angles = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    xy = (np.cos(angles), np.sin(angles))
    model_verts = radius * np.stack(xy, axis=1)

    # Pair neighbouring vertices for drawing
    begin = np.arange(segments)
    end = np.roll(begin, -1)
    model_indices = np.column_stack((begin, end)).flatten()

    return model_verts, model_indices


def model_circle_fan(segments: int = 12):
    """Create a circle fan with the given number of segments.

    Args:
        segments (int): Number of segments of the circle. Defaults to 12.

    Returns:
        np.ndarray(dtype=np.float32): Two-dimensional array of vertex positions, the
            first axis has length segments + 1, the second axis has length 2. The first
            vertex is always at the origin and is used as the center of the fan.
        np.ndarray(dtype=np.uint32): One-dimensional array of indices, each set of three
            indices represents one triangle.
    """
    tau_segs = pi * 2 / segments
    model_verts, model_indices = [(0.0, 0.0)], []
    for i in range(segments):
        model_verts.append((cos(i * tau_segs), sin(i * tau_segs)))
        model_indices.extend((0, i + 1, i + 2))
    model_indices[-1] = 1

    model_verts = np.array(model_verts, dtype=np.float32)
    model_indices = np.array(model_indices, dtype=np.uint32)
    return model_verts, model_indices


def model_circle_subdiv(subdiv: int):
    """Create a circle by iteratively adding smaller triangles to the outside segments.

    Args:
        subdiv (int): Number of subdivisions. subdiv = 0 creates a triangle, increasing
            the subdivision will add exponentially more vertices.

    Returns:
        np.ndarray(dtype=np.float32): Two-dimensional array of vertex positions, the
            first axis has length 3 * 2**subdiv, the second axis has length 2.
        np.ndarray(dtype=np.uint32): One-dimensional array of indices, each set of three
            indices represents one triangle.
    """
    model_verts = [
        (1, 0),
        (cos(2 / 3 * pi), sin(2 / 3 * pi)),
        (cos(4 / 3 * pi), sin(4 / 3 * pi)),
    ]
    model_indices = [0, 1, 2]

    new_segments = [(0, 1), (1, 2), (2, 0)]  # starting indices of outer segments
    for level in range(1, subdiv + 1):
        # Subdivide segments by rotating the starting vertex by half the angle covered
        # by the segment, this is shorter than taking the midpoint of the segment and
        # normalizing its length
        angle = 2 / 3 * pi / 2**level
        r11, r12 = cos(angle), -sin(angle)
        r21, r22 = sin(angle), cos(angle)

        old_segments, new_segments = new_segments, []
        for ai, bi in old_segments:
            ax, ay = model_verts[ai]

            model_verts.append((ax * r11 + ay * r12, ax * r21 + ay * r22))
            ci = len(model_verts) - 1  # index of the newly added vertex
            model_indices.extend((ai, ci, bi))
            new_segments.append((ai, ci))
            new_segments.append((ci, bi))

    model_verts = np.array(model_verts, dtype=np.float32)
    model_indices = np.array(model_indices, dtype=np.uint32)
    return model_verts, model_indices


###############################################################################
# Obstacles
###############################################################################


obstacle_shape_functions = {}
"""dict: The model functions for obstacles. Each key is an obstacle class
(e.g., ``Disk``, ``InfiniteLine``), the corresponding value is a function with
signature::

    model_func(obs: obstacle.Obstacle) -> (vertices, indices, mode)

* vertices (np.ndarray): A Nx2-array of vertex positions,
* indices (list): Indices for the above array of length 2N,
* mode: OpenGL drawing mode.

The vertices, indices and mode are used for drawing of indexed vertex
lists created from a pyglet.graphics.Batch (the vertex array will be
flattened later).
"""

# OpenGL settings for high quality line drawing
# gl.glEnable(gl.GL_LINE_SMOOTH)
# gl.glHint(pyglet.gl.GL_LINE_SMOOTH_HINT, gl.GL_NICEST)
# gl.glLineWidth(2)


def model_disk(obs, batch):
    """Vertices, indices and drawing mode for OpenGL drawing the disk."""
    assert isinstance(obs, Disk), type(obs)

    # vertices, indices = create_circle_line(obs.radius)
    # vertices += obs.center
    # return (vertices, indices, gl.GL_LINES)

    x, y = obs.center
    color = (20, 100, 30, 255)
    shape = shapes.Circle(x, y, obs.radius, segments=64, color=color, batch=batch)
    return shape


obstacle_shape_functions[Disk] = model_disk


def model_infinite_wall(obs, batch):
    """Vertices, indices and drawing mode for OpenGL drawing the wall."""
    assert isinstance(obs, InfiniteWall), type(obs)

    # vertices = np.asarray([obs.start_point, obs.end_point])
    # indices = [0, 1]
    # return (vertices, indices, gl.GL_LINES)

    color = (20, 100, 30, 255)
    shape = shapes.Line(
        *obs.start_point, *obs.end_point, width=0.01, color=color, batch=batch
    )
    return shape


obstacle_shape_functions[InfiniteWall] = model_infinite_wall


def model_line_segment(obs, batch):
    """Vertices, indices and drawing mode for OpenGL drawing the line segment."""
    assert isinstance(obs, LineSegment), type(obs)

    # vertices = np.asarray([obs.start_point, obs.end_point])
    # indices = [0, 1]
    # return (vertices, indices, gl.GL_LINES)

    color = (20, 100, 30, 255)
    shape = shapes.Line(
        *obs.start_point, *obs.end_point, width=0.01, color=color, batch=batch
    )
    return shape


obstacle_shape_functions[LineSegment] = model_line_segment


###############################################################################
# Billiard balls
###############################################################################


# Vertex shader source code
vertex_source = """#version 150 core
in vec2 position;
in vec2 offset;
in vec4 color;
in float scale;

out vec4 vertex_color;

uniform WindowBlock {
    mat4 projection;
    mat4 view;
} window;

void main() {
    gl_Position = window.projection * window.view * vec4(scale * position + offset, 0.0, 1.0);
    vertex_color = color;
}
"""  # noqa: E501


# Fragment shader source code
fragment_source = """#version 150 core
in vec4 vertex_color;

out vec4 final_color;

void main() {
    final_color = vertex_color;
}
"""


class ShapeCollection:
    """A collection of shapes created by duplicating the same template.

    To set up the collection, provide a template shape (a list of vertices, a
    list of indices and the OpenGL draw mode), the (maximum) number of
    instances and a batch (optional).
    The scale, offset (i.e. position on screen) and uniform color of the drawn
    shapes can be set later via the corresponding methods. To make shapes
    invisible, set their scale to zero.
    To draw the collection, use the draw method of the batch.

    Attributes (read-only):
        num_verts (int): Number of vertices of the template shape.
        count (int): Number of shapes in the collection.
        program (ShaderProgram): The shader program that is used to draw the shapes.
        vlist (IndexedVertexList): The vertex list that contains the data for all shape
            instances.
    """

    def __init__(
        self,
        shape_vertices,
        shape_indices,
        draw_mode: int,
        count: int,
        batch: pyglet.graphics.Batch | None = None,
        group: Group | None = None,
    ):
        """Set up the collection with a template shape.

        Args:
            shape_vertices (iterable): Two-dimensional array of vertex positions of the
                template shape, should be of the form [(x1, y1), (x2, y2), ...].
            shape_indices (iterable): List of non-negative integers indexing the
                vertices, such that each set of three integers represents a triangle.
            draw_mode (int): OpenGL draw mode, e.g. gl.GL_LINES or gl.GL_TRIANGLES.
            count (int): Total number of instances in the collection.
            batch (pyglet.batch.Batch, optional): Graphics batch for rendering.
        """
        shape_vertices = np.asarray(shape_vertices, dtype=np.float32)
        shape_indices = np.asarray(shape_indices, dtype=np.uint32)

        self.num_verts = shape_vertices.shape[0]
        self.count = int(count)
        print(self.num_verts, shape_indices.shape[0], self.count)

        # Create shader program
        vert_shader = Shader(vertex_source, "vertex")
        frag_shader = Shader(fragment_source, "fragment")
        self.program = ShaderProgram(vert_shader, frag_shader)
        self.group = pyglet.shapes._ShapeGroup(
            gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA, self.program, group
        )

        # Create one vertex list to manage all shapes in the collection
        self.batch = batch
        self.draw_mode = int(draw_mode)
        indices = np.tile(shape_indices, self.count) + np.repeat(
            self.num_verts * np.arange(self.count), shape_indices.size
        )
        self.vertex_list = self.program.vertex_list_indexed(
            self.num_verts * self.count,
            self.draw_mode,
            indices,
            self.batch,
            self.group,
            color="Bn",
        )

        # Set position of vertices
        # NOTE: using ctypes.memmove is faster than vlist.attr[:] = np_array
        verts = np.tile(shape_vertices.flatten(), self.count)
        ctypes.memmove(self.vertex_list.position, verts.ctypes.data, verts.nbytes)

        # Set attributes to default values
        self.set_scale(1.0)
        self.set_offset((0.0, 0.0))
        self.set_color((255, 255, 255, 255))

    def set_scale(self, scale):
        """Set the scale of the draw shapes.

        Args:
            scale (int or iterable): A single number for all shapes or a list of
                numbers, one for each shape to be drawn (must have length self.count).
        """
        scale = np.ascontiguousarray(scale, dtype=np.float32)
        if len(scale.shape) == 0:  # same scale for all shapes
            scales = np.repeat(scale, self.num_verts * self.count)
        else:  # one scale for each shape
            scales = np.repeat(scale, self.num_verts)
        ctypes.memmove(self.vertex_list.scale, scales.ctypes.data, scales.nbytes)

    def set_offset(self, offset):
        """Set the position on screen of the shapes.

        Args:
            offset (iterable): A list of two numbers will set all shapes to this
                position, a list with dimensions (self.count, 2) will position each
                shape individually.
        """
        offset = np.ascontiguousarray(offset, dtype=np.float32)
        if len(offset.shape) == 1:  # same offset for all shapes
            offsets = np.repeat(offset, self.num_verts * self.count)
        else:  # one offset for each shape
            offsets = np.tile(offset, self.num_verts).flatten()
        ctypes.memmove(self.vertex_list.offset, offsets.ctypes.data, offsets.nbytes)

    def set_color(self, color):
        """Set the color of the shapes.

        A color is a tuple of three or four integers in the range 0-255 (inclusive). The
        fourth component is interpreted as the opaqueness (alpha channel), if not given
        it defaults to 255 (completely opaque). Setting individual vertex colors is not
        possible, each shape will have a uniform color.

        Args:
            color (iterable): A single color for all shapes or a list of colors, one for
                each shape. A list of colors either must have no alpha channel (i.e.
                dimension (self.count, 3)) or every color in the list must have an alpha
                channel (i.e. dimension (self.count, 4)).
        """
        color = np.ascontiguousarray(color, dtype=np.ubyte)
        if len(color.shape) == 1:  # same color for all shapes
            if color.shape[0] == 3:  # append alpha
                color = np.append(color, 255)
            colors = np.repeat(color, self.num_verts * self.count)
        else:  # one color for each shape
            assert color.shape[1] in [3, 4], color.shape
            if color.shape[1] == 3:  # append alpha column
                alpha = np.full(self.count, 255, dtype=np.ubyte)
                color = np.column_stack((color, alpha))
            colors = np.tile(color, self.num_verts).flatten()
        ctypes.memmove(self.vertex_list.color, colors.ctypes.data, colors.nbytes)

    def draw(self) -> None:
        """Draw the collection.

        Avoid this inefficient method for everyday use! Regular drawing should add
        shapes to a ``Batch`` and call its ``Batch.draw`` method.
        """
        self.group.set_state_recursive()
        self.vertex_list.draw(self.draw_mode)
        self.group.unset_state_recursive()


###############################################################################
# Billiard window
###############################################################################


# Adapted from pyglet examples/window/camera.py
class CenteredCamera:
    """A simple 2D camera that contains zoom and scrolling speed."""

    def __init__(self, window, position=(0, 0), zoom=1.0, scroll_speed=1.0):
        """Set up the camera position, zoom and scroll speed."""
        self._window = window
        self.scroll_speed = scroll_speed
        self.x, self.y = position
        self.zoom = zoom
        self._stashed_view = None  # for storing the old window view matrix

    @property
    def extent(self):
        """Size of the viewing bounding box in world units."""
        return 1 / self.zoom, 1 / (self.zoom * self._window.aspect_ratio)

    @property
    def position(self):
        """Query the current offset."""
        return (self.x, self.y)

    @position.setter
    def position(self, new_position):
        """Set the scroll offset directly."""
        self.x, self.y = new_position

    def move(self, axis_x, axis_y):
        """Move axis direction with scroll_speed.

        Example: Move left -> move(-1, 0)
        """
        self.x += self.scroll_speed * axis_x / self.zoom
        self.y += self.scroll_speed * axis_y / self.zoom

    def __enter__(self):
        """Apply zoom and camera offset to view matrix."""
        width, height = self._window.size
        zoom_pixels = width * self.zoom

        # Translate with added center offset
        wx = -width // 2 + self.x * zoom_pixels
        wy = -height // 2 + self.y * zoom_pixels
        view_matrix = self._window.view.translate((-wx, -wy, 0))

        # Scale by zoom level
        view_matrix = view_matrix.scale((zoom_pixels, zoom_pixels, 1))

        # Stash current view matrix and set new view
        self._stashed_view = self._window.view
        self._window.view = view_matrix

    def __exit__(self, exception_type, exception_value, traceback):
        """Restore old view matrix."""
        assert self._stashed_view is not None
        self._window.view = self._stashed_view
        self._stashed_view = None


class BilliardWindow(pyglet.window.Window):
    """Custom window class for interacting with billiard simulations."""

    help = """
Keyboard controls:
SPACE: Pause/unpause simulation
.(PERIOD): Advance one frame (when paused)
,(COMMA): Advance to the next collision (when paused)
+(PLUS) and -(MINUS): Increase/decrease simulation speed
WASD: Pan camera up/left/down/right
QE: Zoom in and out
ESC: Close window and exit"""

    def __init__(
        self,
        billiard,
        *args,
        simulation_speed=1.0,
        camera_position=(0.0, 0.0),
        camera_zoom=1.0,
        particle_size=20.0,
        **kwargs,
    ):
        """Create a window for showing the given billiard simulation.

        Args:
            billiard: An instance of ``simulation.Billiard`` ready to be simulated.
            *args: Further arguments passed to ``pyglet.window.Window``

        Keyword Args:
            simulation_speed: The rate of change of ``billiard.time`` compared to
                realtime. Defaults to 1.0.
            camera_position: A tuple (x, y) for the center of the camera in the
                ``billiard`` coordinate system. Defaults to (0, 0).
            camera_zoom: Size of the billiard coordinate system compared to the width
                of the viewport. Smaller values mean we zoom out, large values mean
                we zoom in. Defaults to 1.0 (the width of the viewport measures 1 unit).
            particle_size: Size of particles (balls with zero radius) in pixels**2.
                Defaults to 20.0 (~4.5 pixels diameter).
            **kwargs: Further keyword arguments passed to ``pyglet.window.Window``.

        Raises:
            TypeError: If ``billiard`` is not an instance of ``simulation.Billiard``.
            ValueError: If ``camera_position`` is not a two-dimensional vector or
                does not contain finite numbers. If ``camera_zoom`` is not a positive
                finite number.
        """
        # Set up pyglet window
        super().__init__(*args, **kwargs)

        # Billiard attributes
        if not isinstance(billiard, Billiard):
            msg = f"Expected a simulation.Billiard instance, but got {type(billiard)}"
            raise TypeError(msg)
        self.billiard = billiard
        self.particle_size = float(particle_size)

        # Set up camera
        cam_pos = [float(c) for c in camera_position]
        if len(cam_pos) != 2:
            msg = f"Camera position must be length 2, not {len(cam_pos)}"
            raise ValueError(msg)
        if not all(map(isfinite, cam_pos)):
            msg = f"Camera position contains a non-finite number {cam_pos}"
            raise ValueError(msg)

        cam_zoom = float(camera_zoom)
        if not (isfinite(cam_zoom) and cam_zoom > 0.0):
            msg = f"Camera zoom must be positive and finite, not {cam_zoom}"
            raise ValueError(msg)

        # cam_pos, cam_zoom = self.autoscale()
        self.camera = CenteredCamera(self, cam_pos, cam_zoom, scroll_speed=0.5)

        # Presentation settings
        self.running = False
        self.advance_one_frame = False  # used when running=False
        self.advance_to_next_collision = False  # used when running=False
        self.simulation_speed = float(simulation_speed)

        # Timing information
        self.timing_simulate = deque(maxlen=60)
        self.timing_draw = deque(maxlen=60)

        self._setup_billiard_drawing()
        self._setup_gui()

        self.keyboard_state = key.KeyStateHandler()
        self.push_handlers(self.keyboard_state)

        # Schedule simulation updates at 60 fps
        pyglet.clock.schedule_interval(self.update, 1 / 60)

    def _resize_markers(self):
        pass

    def _setup_billiard_drawing(self):
        # Setup obstacles
        self.obs_batch = pyglet.graphics.Batch()
        self.obstacle_shapes = []
        for obs in self.billiard.obstacles:
            func = obstacle_shape_functions[type(obs)]
            self.obstacle_shapes.append(func(obs, self.obs_batch))

        # Setup balls
        self.ball_batch = pyglet.graphics.Batch()
        verts, indices = model_circle_subdiv(4)
        self.ball_collection = ShapeCollection(
            verts,
            indices,
            gl.GL_TRIANGLES,
            count=self.billiard.num,
            batch=self.ball_batch,
        )

        # Set ball positions
        self.ball_collection.set_offset(self.billiard.balls_position)

        # Set ball radii and particle marker radii
        new_diameter = sqrt(self.particle_size) / (self.width * self.camera.zoom)
        scale = np.asarray(self.billiard.balls_radius)
        scale[scale == 0] = new_diameter / 2
        self.ball_collection.set_scale(scale)

        # Set ball colors
        colors = (90, 120, 225)
        # colors = np.tile(colors, (self.billiard.num, 1))
        colors += np.random.randint(0, 30, size=(self.billiard.num, 3), dtype=np.ubyte)
        self.ball_collection.set_color(colors)

    def _setup_gui(self):
        # For recording statistics
        self.bounces_list = deque(maxlen=60)
        self.bounces_count = [0, 0]

        # For displaying the GUI
        self.gui_batch = pyglet.graphics.Batch()

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
            batch=self.gui_batch,
        )

        # FPS display
        self.fps_display = pyglet.window.FPSDisplay(self, samples=60)
        fps_label = self.fps_display.label
        fps_label.x = self.width - 4
        fps_label.y = self.height
        fps_label.anchor_x = "right"
        fps_label.anchor_y = "top"

    def autoscale(self):
        """Show the whole billiard table."""
        # Calculate the bounding box of all balls including their radii
        bmin = self.billiard.balls_position.T - self.billiard.balls_radius
        xmin, ymin = bmin.min(axis=1)
        bmax = self.billiard.balls_position.T + self.billiard.balls_radius
        xmax, ymax = bmax.max(axis=1)

        # Adjust for obstacles
        # for obs in self.billiard.obstacles:
        #     # figure out how to get the extent/bounding box for an arbitrary obstacle
        #     # and update xmin, ymin, xmax, ymax

        # Old code for including the obstacles: we saved the location of the vertices
        # for the obstacle models in a list that we assigned to self.obs_batch.models
        # for vertices, _vlist in self.obs_batch.models:
        #     # rectangle around the object
        #     model_xmin, model_ymin = vertices.min(axis=0)
        #     model_xmax, model_ymax = vertices.max(axis=0)

        #     # update biggest rectangle
        #     xmin = min(xmin, model_xmin)
        #     ymin = min(ymin, model_ymin)
        #     xmax = max(xmax, model_xmax)
        #     ymax = max(ymax, model_ymax)

        # Place the camera at the center of the bounding box
        pos = ((xmin + xmax) / 2, (ymin + ymax) / 2)

        # Zoom out so that we can see the whole box
        cam_zoom = self.camera.zoom
        zx = 1 / (xmax - xmin) if xmax > xmin else cam_zoom
        zy = 1 / ((ymax - ymin) * self.aspect_ratio) if ymax > ymin else cam_zoom
        zoom = min(zx, zy)

        return pos, zoom

    def on_key_press(self, symbol, modifiers):
        """Handle key press on the keyboard."""
        super().on_key_press(symbol, modifiers)

        if symbol == key.SPACE:
            self.running = not self.running
        if symbol == key.PERIOD:
            self.advance_one_frame = True
        if symbol == key.COMMA:
            self.advance_to_next_collision = True

    def on_resize(self, width, height):
        """Handle window resize event."""
        super().on_resize(width, height)

        # move labels
        self.label_info.x = 4
        self.label_info.y = height - 4

        self.fps_display.label.x = width - 4
        self.fps_display.label.y = height

    def on_draw(self):
        """Redraw the window contents."""
        tic = clock()
        self.clear()

        # draw billiard objects
        with self.camera:
            self.obs_batch.draw()
            self.ball_batch.draw()

        # draw GUI
        self.gui_batch.draw()
        self.fps_display.draw()

        toc = clock()
        self.timing_draw.append(toc - tic)

    def update(self, dt):
        """Update the camera, the simulation and the GUI."""
        # Update using keystate, i.e. which keys are currently pressed down
        stale_scale = self._update_keyboard(dt=min(dt, 0.2))  # not slower than 5 fps

        # If we zoom, then also update the particle radii on the GPU
        if stale_scale:
            new_diameter = sqrt(self.particle_size) / (self.width * self.camera.zoom)
            scale = np.asarray(self.billiard.balls_radius)
            scale[scale == 0] = new_diameter / 2
            self.ball_collection.set_scale(scale)

        # Update simulation, send new positions to GPU
        tic = clock()
        stale_position = self._update_simulation(dt=1 / 60)  # always update at 60fps
        if stale_position:
            self.ball_collection.set_offset(self.billiard.balls_position)
        toc = clock()
        self.timing_simulate.append(toc - tic)

        # Update GUI
        self._update_gui(dt)

    def _update_keyboard(self, dt):
        keys = self.keyboard_state
        stale_scale = False  # check if we need to update the particle marker radius

        # Update camera position
        if keys[key.A]:  # left
            self.camera.move(-dt, 0)
        if keys[key.D]:  # right
            self.camera.move(dt, 0)
        if keys[key.W]:  # up
            self.camera.move(0, dt)
        if keys[key.S]:  # down
            self.camera.move(0, -dt)

        # Update camera zoom
        if keys[key.Q]:
            self.camera.zoom *= 2.0**dt
            stale_scale = True
        if keys[key.E]:
            self.camera.zoom /= 2.0**dt
            stale_scale = True

        # Update simulation speed
        if keys[key.PLUS]:  # inccrease speed
            self.simulation_speed *= 2.0**dt
        if keys[key.MINUS]:  # decrease speed
            self.simulation_speed /= 2.0**dt

        return stale_scale

    def _update_simulation(self, dt):
        stale_position = False  # check if we need to update ball positions on the GPU

        if self.running or self.advance_one_frame:
            timestep = self.simulation_speed * dt
            collisions = self.billiard.evolve(self.billiard.time + timestep)

            self.bounces_count[0] += collisions[0]
            self.bounces_count[1] += collisions[1]
            self.bounces_list.append((timestep, *collisions))

            self.advance_one_frame = False
            stale_position = True
        elif self.advance_to_next_collision:
            if self.billiard.next_collision[0] < float("inf"):
                start_time = self.billiard.time
                collisions = self.billiard.evolve(self.billiard.next_collision[0])

                self.bounces_count[0] += collisions[0]
                self.bounces_count[1] += collisions[1]
                self.bounces_list.append((self.billiard.time - start_time, *collisions))

                stale_position = True

            self.advance_to_next_collision = False

        return stale_position

    def _update_gui(self, dt):
        # First line: billiard info
        bb_count, ob_count = self.bounces_count
        timeframe = sum(t for t, _, _ in self.bounces_list)
        ball_bounces = sum(b for _, b, _ in self.bounces_list)
        obstacle_bounces = sum(o for _, _, o in self.bounces_list)
        bb_per_sec = ball_bounces / timeframe if timeframe > 0 else float("nan")
        ob_per_sec = obstacle_bounces / timeframe if timeframe > 0 else float("nan")
        info = [
            f"Time: {self.billiard.time:.3f} (x{self.simulation_speed:.5})",
            f"Bounces: {bb_count} (+{bb_per_sec:.0f}/s)  "
            f"{ob_count} (+{ob_per_sec:.0f}/s)",
        ]
        first_line = "    ".join(info)

        # Second line: camera info
        cx, cy = self.camera.position
        second_line = f"Camera: [{cx:.4}, {cy:.4}]  Zoom: {self.camera.zoom:.5}"

        # Third line: timing info
        time_sim = mean(self.timing_simulate) if self.timing_simulate else 0.0
        time_draw = mean(self.timing_draw) if self.timing_draw else 0.0
        info = [
            f"dt: {1000 * dt:.1f}ms",
            f"Simulate: {time_sim * 1000:.2f}ms",
            f"Draw: {time_draw * 1000:.2f}ms",
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
    # Configures the buffer for multisampling (MSAA)
    kwargs.setdefault("config", gl.Config(sample_buffers=1, samples=4))  # alpha_size=8
    kwargs.setdefault("resizable", True)

    bldwin = BilliardWindow(billiard, *args, **kwargs)
    print(bldwin.help)
    pyglet.app.run()
