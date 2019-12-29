# -*- coding: utf-8 -*-
"""Billiards top-level module.

You can import the ``Billiard`` class from here for convenience::

    from billiard import Billiard

"""
__version__ = "0.3.0"


# Local
from . import obstacles, physics, simulation, visualize
from .simulation import Billiard

__all__ = ["obstacles", "physics", "simulation", "visualize", "Billiard"]
