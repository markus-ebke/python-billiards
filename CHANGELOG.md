# Changelog

**v1.0.0.dev0**
- Many API changes, mostly to make method and function names more descriptive
- Split visualization into a matplotlib and a pyglet file. Add more customization for plotting with matplotlib (including a color scheme for billiard objects). Rewrite the pyglet visualization for pyglet version 2.0, add camera controls.
- Implement LineSegment obstacle, collisions at the end-points are handled as if they are rounded
- The obstacle.detect_collision method returns some more info about the collision location which is used when resolving collisions. This should prevent unnecessary re-computations for more complex obstacles.
- Implement selective recalculation of internal time-of-impact tables, now changing the balls position, velocity or radius is possible in the middle of the simulation
- Derive the balls' positions at the current time from the variables `balls_initial_time` and `balls_initial_position`, these are only updated when the ball collides and changes direction. This fixes a floating point issue when stopping and resuming simulations (for complicated billiards the end result of `visualize.animate`, which calls `Billiard.evolve` multiple times, would be different from calling `Billiard.evolve` once).
- Add callbacks to `Billiard.evolve` to keep track of simulation progress or to observe certain balls or obstacles
- Adopt a modern packaging workflow: Use a `pyproject.toml` file for configuration, place all metadata in the `setup.cfg` file and remove the now empty `setup.py` file. Also remove nonessential development packages and rework the development workflow (refactor tox environments, decide on versioning scheme of the form `N.N.N[.devN]`, don't include example pictures and videos in source distribution).
- Change to MIT license

**v0.5.0**
- Use numpy's `argmin`-function for finding next collision, billiards with many ball-ball collisions are now up to 3x faster!
- Visualization improvements: Use progress bar in `animate`, scale/disable velocity indicators in `plot` and `animate`, plot `InfiniteWall` as an infinite line (duh! 🤦)
- Rework documentation and include more examples: ideal gas in a box, compute pi from pool (now the standard example in README.md)
- Change imports: Obstacles can be imported from top-level module, `visualize` module must be imported manually (better if the visualize feature is not wanted)
- Add pre-commit and automatically apply code formatting and linting on every commit

**v0.4.0**
- Add basic obstacles (disk and infinite wall)
- Add interaction with simulations via pyglet
- Add examples

**v0.3.0**
- Add visualizations with matplotlib (plot and animate)

**v0.2.0**
- Implement time of impact calculation and collision handling

**v0.1.0**
- Setup package files, configure tools and add basic functionality
