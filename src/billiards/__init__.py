# -*- coding: utf-8 -*-
"""Billiards main module."""
__version__ = "0.1.0"

# Local
from .simulation import Simulation, elastic_collision, time_of_impact

__all__ = ["time_of_impact", "elastic_collision", "Simulation"]
