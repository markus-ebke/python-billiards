.. billiards documentation master file, created by
   sphinx-quickstart on Thu Sep 12 16:39:16 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to billiards' documentation!
====================================

``billiards`` is a python library that implements a very simple physics engine:
It simulates the movement of particles that live in two dimensions.
When particles collide they behave like hard balls.
Basically the particles act like billiard balls.


Features
--------
* Collision detection with time of impact calculation: No reliance on time steps, no tunneling of fast bullets! Collisions will be correctly identified and only the necessary ones will be handled.
* Fast state updates thanks to `numpy <https://numpy.org/>`_ (especially if there are no collisions, see point above).
* Static obstacles to construct a proper billiard table.
* Balls with zero radius behave like point particles, useful for simulating `dynamical billiards <https://en.wikipedia.org/wiki/Dynamical_billiards>`_ (but this library is not optimized for simulating point particles).
* Optional features: plotting and animation with `matplotlib <https://matplotlib.org/>`_, interaction with `pyglet <http://pyglet.org/>`_.
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

