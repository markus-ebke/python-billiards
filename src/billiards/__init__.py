"""Billiards top-level module.

For convenience, you can import the following classes from here::

    from billiards import Billiard, Disk, InfiniteWall, LineSegment

The visualization modules have to be imported on their own::

    from billiards import visualize_matplotlib, visualize_pyglet
"""

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


__version__ = "0.5.0"


def _parse_to_version_info(version_str):
    """Parse the version string and return a tuple analogous to sys.version_info."""
    # Source: https://packaging.python.org/en/latest/specifications/version-specifiers
    # In particular, see Appendix: Parsing version strings with regular expressions
    import re
    from collections import namedtuple

    # pattern: {major}.{minor}.{patch} and {major}.{minor}.{patch}.{dev_l}{dev_n}
    regex = re.compile(
        r"(?P<release>[0-9]+(?:\.[0-9]+)*)"
        r"(?P<dev>\.(?P<dev_l>dev)(?P<dev_n>[0-9]+)?)?"
    )

    # Validate the version and parse it into pieces
    match = regex.search(version_str)
    if not match:
        raise ValueError(f"Invalid version: '{version_str}'")

    major, minor, micro = tuple(int(i) for i in match.group("release").split("."))
    dev_label, dev_number = match.group("dev_l"), match.group("dev_n")

    # Set release level, if none given use "final"
    if dev_label == "dev":
        releaselevel, serial = "dev", int(dev_number)
    else:
        assert dev_label is None, dev_label
        releaselevel, serial = "final", "0"

    # Assemble version info tuple analogous to sys.version_info
    VersionInfo = namedtuple(
        "VersionInfo", ["major", "minor", "micro", "releaselevel", "serial"]
    )
    return VersionInfo(major, minor, micro, releaselevel, serial)


__version__info__ = _parse_to_version_info(__version__)
