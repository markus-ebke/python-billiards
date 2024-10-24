# Ideas
A list of features that might be useful, but for which I have no time or interest to actually implement them.

## Add type hints
- MonkeyType: https://monkeytype.readthedocs.io
- mypy: http://mypy-lang.org/
- flake8-typing-imports(?)
- https://www.bernat.tech/the-state-of-type-hints-in-python/

## Simulation
- Make Simulation attributes readonly / automatically recalculate toi after changing position, velocity or radius
- ParticleBilliard: Simulate point particles that only collide with the obstacles, use parallelization in evolve
- Write time-intensive functions in Cython (better: convert the whole Simulation class to Cython and use prange where possible)

## Improve documentation
- Get Sphinx autodoc to document a class's __init__ method
- Spellchecker? (sphinxcontrib.spelling is deprecated, but see cookiecutter-pylibrary for setup)
- Use a gallery page for the examples (like https://matplotlib.org/stable/gallery/index)
- Upload documentation to ReadTheDocs and extend README.md with badges and link to documentation

## Publish on PyPi
- https://packaging.python.org/guides/making-a-pypi-friendly-readme
- Figure out how to update packages to PyPi
- When writing parts of the code in Cython, how to compile for all supported operating systems?

## More control of plot
- default_fig_and_ax: supply billiard instance and compute billiard aspect ratio, then use a figsize with a similar aspect ratio (+ some space for labels)
- Draw trail behind balls (and add parameters to control the trail length)
- Improve CircleCollection.datalim (somehow rendering and `get_path_collection_extents` don't do the same thing with transform, transData and transOffset). Also compare with EllipseCollection, maybe we can assign our own get_datalim method there and remove CircleCollection?
- Slow balls: Draw velocity direction as a ">" inside the circle? See also https://github.com/CarlKCarlK/perfect-physics
- For implementing plotting of Hyperplane: use a shaded area that follows the camera (see matplotlib.lines.AxLine and https://matplotlib.org/stable/gallery/text_labels_and_annotations/angle_annotation.html for reference)
- Write tests that check different configurations for the color_scheme argument, compare with facecolors extracted from ax.lines, ax.patches, ax.artists, etc.
- If tqdm is not available, create dummy progress bar with print(".", end="")

## More versatile `visualize_pyglet.interact`
- Use mouse scroll wheel for zooming to mouse cursor position
- Use color_scheme like matplotlib (but with colors for dark mode?)
- Show/hide velocities as arrows starting at the balls center
- When paused, drag-and-drop balls around and edit velocities by dragging-and-dropping the arrow tips
- Draw balls using instancing (see documentation for pyglet.graphics.instance and pyglet.graphics.ShaderProgram.vertex_list_instanced_indexed)

## Better Testing
- How to write proper tests for matplotlib?
- How to write proper tests for pyglet (or GUIs in general)?
- Make pyglet work with tox, currently I can't access `pyglet.gl.GL_LINES` when I run the tests via tox (pyglet.canvas.xlib.NoSuchDisplayException: Cannot connect to "None"), see commented fragments in test_visualize.py
- Use TravisCI (and other internet services?)

## More obstacles
- Change "exterior" to "outside" or "outer" or use the opposite "interior", "inside", "inner"?
- Implement as class Rotation(Obstacle) with `__init__(obstacle, angle)`, in `calc_toi` and `collide` inversely rotates the ball and then call the obstacle method.
- The pos argument for Obstacle.collide is mutable. We could use this to teleport balls at collision, e.g. to create a box with periodic boundary conditions or portal objects.

Regions in 1D (collisions from both sides):
- InfiniteLine(point1, point2) and InfiniteLine(point1, None, direction)
- HalfLine(point1, point2) and HalfLine(point1, None, direction) (semi-infinite line)
- PolyLine(list of points) (last point = first point => closed polyline)
- Circle(center, radius=radius or (radius_x, radius_y)) (for circles and ellipses)
- Arc(center, radius=radius or (radius_x, radius_y), start_angle, stop_angle) (for circular and elliptic arcs)
- Reference: DynamicalBilliards.jl, https://reference.wolfram.com/language/guide/GeometricSpecialRegions.html "Regions in 1D"

Regions in 2D (exterior="outside" or "inside"):
- Hyperplane(point, normal) (normal points towards the exterior)
- Triangle(point1, point2, point3, exterior=exterior or "left" or "right")
- Rectangle(bottomleft, topright, exterior) (supports infinite corner points)
- Polygon(list of points, exterior=exterior or "left" or "right") (built from finite lines, polyline can be self-intersecting and how holes are treated depends on the value of exterior)
- RegularPolygon(center, radius, numsides, rotate, exterior)
- CenteredSquare(center, sidelength, exterior) (see https://github.com/nirnayroy/python-billiards/commit/71dcb950eac5e9eefea885e01cb74bcbfdfbe437)
- Parallelogram(origin, direction1, direction2, exterior) (implement as skewed rectangle?)
- Ellipse: Disk(center, radii=radius or (radius_x, radius_y), exterior)
- DiskSector(center, radii=radius or (radius_x, radius_y), start_angle, stop_angle, exterior) (a Wedge shape)
- DiskSegment(center, radii=radius or (radius_x, radius_y), start_angle, stop_angle, exterior) (circular arc closed by a chord)
- AnnulusSector(center, outer_radius, inner_radius, start_angle, stop_angle, exterior)
- Stadium(point1, point2, radius, exterior)
2D to 1D Conversion functions:
- create_triangle_line, create_rectangle_line, create_regular_polyline, create_centered_square_line, create_parallelogram_line -> PolyLine
- create_disk_sector_line, create_disk_segment_line, create_annulus_sector_line, create_stadium_line -> list of Polylines and Arcs with shared endpoints
- Reference: DynamicalBilliards.jl, https://reference.wolfram.com/language/guide/GeometricSpecialRegions.html "Regions in 2D"

Further changes:
- Remove InfiniteWall (equivalent to Hyperplane)
- Implement rounding of corners: Polyline -> list of Arcs and Polylines, Polygon -> shorter lines and virtual balls inside the corners?
- In README.md write "Static obstacles to construct billiard tables with arbitrary shapes"
- Helper functions: circle_through(p1, p2, p3) -> center, radius (circle through 3 points); circle_around(list of points) -> center, radius (smallest circle containing all points)

## Reduce the number of configuration files
- Move setuptools configuration from setup.cfg to pyproject.toml
- Move flake8 configuration to pyproject.toml, but the current version of Flake8 does not support this yet (workaround: https://pypi.org/project/Flake8-pyproject/)
- Pre-commit: Replace black, isort, flake8 and pydocstyle with ruff. Change VSCode formatter to ruff. Keep the old configuration for isort in pyproject.toml and for flake8 in .flake8?
- Install ruff via `$ pipenv install --dev ruff` and add to requirements_dev.txt? Or instead create a tox environment for formatters?
- Move tox configuration from tox.ini to pyproject.toml (requirements: tox>=4.21.0), remove "isolated_build = True" from tox.ini because it is the default setting for tox>=4.0.0
- Replace bump2version with newer bump-my-version, move settings from .bumpversion.cfg to pyproject.toml?

## Gravity
Make the balls fall "downwards" i.e.
- Add gravity vector (np.ndarray of size 2) to `Billiard.__init__`.
- In `Billiard._move`:
  ```python
  self.balls_position += self.balls_velocity * dt + self.gravity / 2 * dt**2
  self.balls_velocity += self.gravity * dt
  ```
- Calculate time of impact for ball-ball collisions: don't change anything because all balls fall at the same rate (if we switch to frame of reference that accelerates with gravity, then the balls are not accelerated anymore. Thanks Einstein!)
- Calculate time of impact for ball-obstacle collisions: I dont't know, it might be complicated since obstacles remain stationary (i.e. accelerate in gravity-following frame of reference)

## (Sliding) Friction and/or drag
Imagine that the balls roll on a flat horizontal table covered in cloth (this will be inconsistent with gravity but that's OK.)
Friction is a force of size F = mu * mass with a direction opposite of velocity.
We need to integrate a = mu to find the trajectory of the ball until it stops (this is a straight line which is reparameterised by a quadratic function).
Drag is a force similar to friction, but F is proportional to velocity^2 * size of ball, this is more complicated to integrate.
We can still use time of impact calculation, but we need to take care of the reparameterisation.

## Add Badges to README.md
Examples:
.. image:: https://img.shields.io/pypi/v/billiards.svg
    :target: https://pypi.python.org/pypi/billiards
    :alt: Latest PyPI version

.. image:: https://travis-ci.org/borntyping/cookiecutter-pypackage-minimal.png
   :target: https://travis-ci.org/borntyping/cookiecutter-pypackage-minimal
   :alt: Latest Travis CI build status


# Misc Notes
Conventions:
- Particles with no radius are point particles
- Particles with zero mass are massless and don't push others around
- Particles with infinite mass are not pushed around by other particles
- Obstacles always have an inside and an outside, collision happens only when a ball comes from the inside and moves towards the outside. This is because point particles on the obstacle

Links:
- Billiards in Julia: https://juliadynamics.github.io/DynamicalBilliards.jl/dev/
- Collision handling: https://en.wikipedia.org/wiki/Elastic_collision#Two-dimensional_collision_with_two_moving_objects
- https://jeffknupp.com/blog/2013/08/16/open-sourcing-a-python-project-the-right-way/
- https://dbader.org/blog/write-a-great-readme-for-your-github-project
- CI: see cookiecutter-pylibrary
- Makefile instead of tox: see cookiecutter-pypackage
