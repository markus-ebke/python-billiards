Usage
=====

To use ``billiards`` in a project:

.. doctest::

    >>> import billiards
    >>> bld = billiards.Billiard()


Example: Newton's cradle
------------------------

Place 5 balls in a row and give the leftmost ball a push to the right:

.. doctest::

    >>> bld.add_ball((0, 0), (1, 0), 1)
    0
    >>> bld.add_ball((3, 0), (0, 0), 1)
    1
    >>> bld.add_ball((5.1, 0), (0, 0), 1)
    2
    >>> bld.add_ball((7.2, 0), (0, 0), 1)
    3
    >>> bld.add_ball((9.3, 0), (0, 0), 1)
    4
    >>> billiards.visualize.animate(bld, end_time=5)
    <matplotlib.animation.FuncAnimation object at 0x...>

.. raw:: html

    <video width="100%" height="auto" controls>
    <source src="_static/newtons_cradle.mp4" type="video/mp4">
    Your browser does not support the video tag.
    </video>
