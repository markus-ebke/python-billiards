# billiards

> A 2D physics engine for simulating dynamical billiards

_billiards_ is a python library that implements a very simple physics engine:
It simulates the movement of hard, disk-shaped particles in a two-dimensional world filled with static obstacles.



## Features

- Collision detection with time-of-impact calculation. No reliance on time steps, no tunneling of high-speed bullets!
- Quick state updates thanks to [numpy](https://numpy.org/), especially if there are no collisions between the given start and end times.
- Static obstacles to construct a proper billiard table.
- Balls with zero radii behave like point particles, useful for simulating [dynamical billiards](https://en.wikipedia.org/wiki/Dynamical_billiards) (although this library is not optimized for point particles).
- Optional features: plotting and animation with [matplotlib](https://matplotlib.org/), interaction with [pyglet](https://pyglet.org/).
- Free software: GPLv3+ license.



## Quickstart

Clone the repository from GitHub and install the package (requires _numpy_ and, for visualization, _matplotlib_ and _pyglet_):

```shell
git clone https://github.com/markus-ebke/python-billiards.git
pip install .[visualize]
```

Import the library and setup an empty billiard table:

```pycon
>>> import billiards
>>> bld = billiards.Billiard()

```

Add one ball at position (2, 0) with velocity (4, 0):

```pycon
>>> idx = bld.add_ball((2, 0), (4, 0), radius=1)
>>> print(idx)
0

```

The `add_ball` method will return an index that we can use later to retrieve the data of this ball from the simulation.
To see where the ball is at time = 10 units:

```pycon
>>> bld.evolve(end_time=10.0)
[]
>>> print("({}, {})".format(*bld.balls_position[idx]))
(42.0, 0.0)
>>> print("({}, {})".format(*bld.balls_velocity[idx]))
(4.0, 0.0)
>>> import matplotlib.pyplot as plt
>>> billiards.visualize.plot(bld)
<Figure size 800x600 with 1 Axes>
>>> plt.show()
```

![One ball](docs/_images/quickstart_1.svg)

Now add another ball in a collision course:

```pycon
>>> bld.add_ball((50, 18), (0, -9), radius=1, mass=2)
1
>>> print("t={:.7}, idx1={}, idx2={}".format(*bld.toi_next))
t=11.79693, idx1=0, idx2=1
```

![Two balls before a collision](docs/_images/quickstart_2.svg)

The collision happens around t=11.8, let's see how the scene looks later:

```pycon
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
>>> plt.show()
```

![Two balls after the collision](docs/_images/quickstart_3.svg)

The collision changed the direction of both balls!
Note that the upper ball is heavier and faster, so both balls are moving down now.
The collision is elastic, i.e. it preserves the total kinetic energy:

```pycon
>>> (1 * 4.0**2) / 2 + (2 * (-9.0)**2) / 2  # kinetic energy = m v^2 / 2
89.0
>>> v_squared = (bld.balls_velocity**2).sum(axis=1)
>>> (bld.balls_mass * v_squared).sum() / 2  # kinetic energy now
89.0
```

## Examples

Setup:

```pycon
>>> from math import cos, pi, sin, sqrt
>>> import matplotlib.pyplot as plt
>>> import numpy as np
>>> import billiards
>>> from billiards.obstacle import Disk, InfiniteWall
```



### Pool

Construct the billiard table:

```pycon
>>> width, length = 112, 224
bounds = [
    InfiniteWall((0, 0), (length, 0)),  # bottom side
    InfiniteWall((length, 0), (length, width)),  # right side
    InfiniteWall((length, width), (0, width)),  # top side
    InfiniteWall((0, width), (0, 0))  # left side
]
bld = billiards.Billiard(obstacles=bounds)
```

Arrange the balls in a pyramid shape:

```pycon
>>> radius = 2.85
>>> for i in range(5):
>>>     for j in range(i + 1):
>>>         x = 0.75 * length + radius * sqrt(3) * i
>>>         y = width / 2 + radius * (2 * j - i)
>>>         bld.add_ball((x, y), (0, 0), radius)
```

Add the white ball and give it a push, then start the animation:

```pycon
>>> bld.add_ball((0.25 * length, width / 2), (length / 3, 0), radius)
>>> anim = billiards.visualize.animate(bld, end_time=10)
>>> anim._fig.set_size_inches((10, 5.5))
>>> plt.show()
```

See [pool.mp4](./examples/pool.mp4)



### Sinai billiard

Construct the billiard table: A square with a disk removed from its center.

```pycon
>>> obs = [
>>>     InfiniteWall((-1, -1), (1, -1)),  # bottom side
>>>     InfiniteWall((1, -1), (1, 1)),  # right side
>>>     InfiniteWall((1, 1), (-1, 1)),  # top side
>>>     InfiniteWall((-1, 1), (-1, -1)),  # left side
>>>     billiards.obstacles.Disk((0, 0), radius=0.5)  # disk in the middle
>>> ]
>>> bld = Billiard(obstacles=obs)
```

Distribute particles uniformly in the square, moving in random directions but with the same speed:

```pycon
>>> for i in range(300):
>>>     pos = np.random.uniform((-1, -1), (1, 1))
>>>     angle = np.random.uniform(0, 2 * pi)
>>>     vel = [cos(angle), sin(angle)]
>>>     bld.add_ball(pos, vel, radius=0)
>>> bld.balls_velocity /= 5  # slow down
```

and watch the simulation

```pycon
>>> anim = billiards.visualize.animate(bld, end_time=20)
>>> anim._fig.set_size_inches((6, 6))
>>> plt.show()
```

See [sinai_billiard.mp4](./examples/sinai_billiard.mp4)



## Authors

- Markus Ebke - <https://github.com/markus-ebke>
