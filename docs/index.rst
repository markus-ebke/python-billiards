Welcome to billiards' Documentation!
====================================

``billiards`` is a python library that implements a very simple physics engine:
It simulates the movement of hard, disk-shaped particles in a
two-dimensional world filled with static obstacles.



Features
--------

* Collision detection with time-of-impact calculation. No reliance on time
  steps, no tunneling of high-speed bullets!
* Quick state updates thanks to `numpy <https://numpy.org/>`_, especially if
  there are no collisions between the given start and end times.
* Static obstacles to construct a proper billiard table.
* Balls with zero radii behave like point particles, useful for simulating
  `dynamical billiards <https://en.wikipedia.org/wiki/Dynamical_billiards>`_
  (although this library is not optimized for point particles).
* Optional features: plotting and animation with
  `matplotlib <https://matplotlib.org/>`_, interaction with
  `pyglet <http://pyglet.org/>`_.
* Free software: GPLv3+ license



.. toctree::
   :maxdepth: 2
   :caption: Contents

   installation
   usage

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api_reference/modules


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
