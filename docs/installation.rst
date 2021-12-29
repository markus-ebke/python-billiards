Installation
============

Requirements
------------

``billiards`` depends on ``numpy`` (it will be installed automatically).
The ``matplotlib`` and ``pyglet`` packages are used to make visualizations, but
this feature is an extra.

If you want to install these packages manually, you can use::

    $ pip install numpy matplotlib pyglet


Installing from GitHub
----------------------

Clone from git, then install::

    $ git clone https://github.com/markus-ebke/python-billiards.git
    $ pip install .[visualize]
