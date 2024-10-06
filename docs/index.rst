Welcome to billiards' Documentation!
====================================

**billiards** is a python library that implements a very simple physics
engine: It simulates the movement and elastic collisions of hard,
disk-shaped particles in a two-dimensional world.



Features
--------

-  Collisions are found and resolved *exactly*. No reliance on time
   steps, no tunneling of high-speed bullets!
-  Quick state updates thanks to `numpy <https://numpy.org>`__,
   especially if there are no collisions between the given start and end
   times.
-  Static obstacles to construct a proper billiard table.
-  Balls with zero radii behave like point particles, useful for
   simulating `dynamical
   billiards <https://en.wikipedia.org/wiki/Dynamical_billiards>`__
   (although this library is not optimized for point particles).
-  Optional features: plotting and animation with
   `matplotlib <https://matplotlib.org>`__, interaction with
   `pyglet <https://pyglet.org>`__.
-  Free software: GPLv3+ license.



.. toctree::
   :maxdepth: 1
   :caption: Contents

   installation
   quickstart
   usage
   examples

.. toctree::
   :maxdepth: 1
   :caption: API Reference

   api_reference/billiards
   api_reference/billiards_physics
   api_reference/billiards_simulation
   api_reference/billiards_obstacles
   api_reference/billiards_visualize


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
