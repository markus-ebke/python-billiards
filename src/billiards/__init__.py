"""Billiards top-level module.

For convenience, you can import the following classes from here::

    from billiard import Billiard, Disk, InfiniteWall

To use the visualize module, you need to import it separately::

    import billiard.visualize

"""
__version__ = "0.4.0"


# Local
from . import obstacles, physics, simulation
from .obstacles import Disk, InfiniteWall
from .simulation import Billiard

__all__ = ["obstacles", "physics", "simulation", "Billiard", "Disk", "InfiniteWall"]
