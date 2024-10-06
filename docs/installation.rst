Installation
============

Requirements
------------

**billiards** is a library for Python 3. It only depends on
`numpy <https://numpy.org>`__.

Billiard systems can be visualized using `matplotlib <https://matplotlib.org>`__
(and `tqdm <https://tqdm.github.io>`__ to display progress in
``visualize.animate``). Interaction with the simulation is possible via
`pyglet <https://pyglet.org>`__ . These visualization features are optional.


If you want to install all these packages manually, you can use:

.. code:: shell

    $ pip install numpy matplotlib tqdm pyglet




Installing from GitHub
----------------------

Clone the repository from GitHub and install the package:

.. code:: shell

   git clone https://github.com/markus-ebke/python-billiards.git
   cd python-billiards/
   pip install .[visualize]
