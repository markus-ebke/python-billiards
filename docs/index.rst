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
This type of dynamical system is also known as `dynamical billiards`_.

* Free software: GPLv3+ license


Quickstart
==========

Clone the repository from GitHub and install the package with setuptools::

    $ git clone https://github.com/markus-ebke/billiards.git
    $ pip install .[visualize]

Note that ``billiards`` depends on ``numpy`` (and matplotlib for
visualization), setuptools will install it automatically.

Import the library and setup an empty billiard world:

.. doctest::

    >>> import billiards
    >>> bld = billiards.Billiard()

Add one ball at position (2, 0) with velocity (4, 0):

.. doctest::

    >>> idx = bld.add_ball((2, 0), (4, 0), radius=1)
    >>> print(idx)
    0

The ``add_ball`` method will return an index that we can use later to retrieve
the data of this ball from the simulation.
To see where the ball is at time = 10 units:

.. doctest::

    >>> bld.evolve(end_time=10.0)
    []
    >>> print("({}, {})".format(*bld.balls_position[idx]))
    (42.0, 0.0)
    >>> print("({}, {})".format(*bld.balls_velocity[idx]))
    (4.0, 0.0)
    >>> billiards.visualize.plot(bld, show=False)
    <Figure size 800x600 with 1 Axes>


.. image:: _images/quickstart_1.svg
    :alt: One ball

Now add another ball that will collide with the first one:

.. doctest::

    >>> bld.add_ball((50, 18), (0, -9), radius=1, mass=2)
    1
    >>> print("t={:.7}, idx1={}, idx2={}".format(*bld.toi_next))
    t=11.79693, idx1=0, idx2=1
    >>> bld.evolve(14.0)
    [(11.796930766973276, 0, 1)]
    >>> print(bld.time)
    14.0
    >>> print(bld.balls_position)
    [[ 46.25029742 -26.4368308 ]
     [ 55.87485129  -4.7815846 ]]
    >>> print(bld.balls_velocity)
    [[ -1.33333333 -12.        ]
     [  2.66666667  -3.        ]]
    >>> billiards.visualize.plot(bld)
    <Figure size 800x600 with 1 Axes>


.. image:: _images/quickstart_2.svg
    :alt: Two balls after collision

The collision changed the course of both balls!
Note that the collision is elastic, i.e. it preserves the total kinetic energy.


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
