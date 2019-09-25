.. billiards documentation master file, created by
   sphinx-quickstart on Thu Sep 12 16:39:16 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to billiards' documentation!
====================================

`billiards` is a python library that implements a very simple physics engine:
It simulates the movement of particles that live in two dimensions.
When particles collide they behave like hard balls.
Basically the particles act like billiard balls.
This type of dynamical system is also known as `dynamical billiards`_.

* Free software: GPLv3+ license


Quickstart
==========

Clone the repository from GitHub and install the package with setuptools::

    $ git clone https://github.com/markus-ebke/billiards.git
    $ python setup.py install

Note that ``billiards`` depends on ``numpy``, setuptools will install it
automatically.

To simulate one ball use::

    import billiards

    # create empty world
    sim = billiards.Simulation()

    # add one ball at position (2, 0) with velocity (4, 0)
    idx = sim.add_ball((2, 0), (4, 0))

    # advance simulation by 10 time units
    sim.step(10)

    # print the position of the ball
    print(sim.balls_position[idx])

The output is::

    [42.0, 0.0]


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

.. _dynamical billiards: https://en.wikipedia.org/wiki/Dynamical_billiards
