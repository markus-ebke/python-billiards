"""Billiards top-level module.

For convenience, you can import the following classes from here::

    from billiards import Billiard, Disk, InfiniteWall, LineSegment

To use the visualization modules, you need to import them separately::

    from billiards import visualize_matplotlib, visualize_pyglet
"""

__version__ = "0.5.0"


# Local
from . import obstacles, physics, simulation
from .obstacles import Disk, InfiniteWall, LineSegment
from .simulation import Billiard

__all__ = [
    "obstacles",
    "physics",
    "simulation",
    "Billiard",
    "Disk",
    "InfiniteWall",
    "LineSegment",
]
