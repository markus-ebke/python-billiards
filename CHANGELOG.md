# Changelog

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
