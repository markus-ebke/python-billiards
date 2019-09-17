billiards - A 2D physics engine for simulating dynamical billiards
==================================================================

* Free software: GPLv3+ license


Quickstart
==========

Clone the repository and install using setuptools::

    $ git clone https://github.com/markus-ebke/billiards.git
    $ python setup.py install

Note that ``billiards`` depends on ``numpy``, setuptools will install it automatically.

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


Authors
=======

* Markus Ebke - https://github.com/markus-ebke
