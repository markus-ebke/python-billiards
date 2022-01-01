Installation
============

Requirements
------------

**billiards** depends on `numpy <https://numpy.org>`__. Additionally,
billiard systems can be visualized with
`matplotlib <https://matplotlib.org>`__ and
`pyglet <http://pyglet.org>`__ (and `tqdm <https://tqdm.github.io>`__ to
display progress in ``visualize.animate``). But this feature is
optional.


If you want to install these packages manually, you can use:

.. code:: shell

    $ pip install numpy matplotlib tqdm pyglet




Installing from GitHub
----------------------

Clone the repository from GitHub and install the package:

.. code:: shell

   git clone https://github.com/markus-ebke/python-billiards.git
   pip install .[visualize]
