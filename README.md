# billiards
> A 2D physics engine for simulating dynamical billiards

_billiards_ is a python library that implements a very simple physics engine:
It simulates the movement of particles that live in two dimensions.
When particles collide they behave like hard balls.
Basically the particles act like billiard balls.
This type of dynamical system is also known as [dynamical billiards](https://en.wikipedia.org/wiki/Dynamical_billiards).


- Free software: GPLv3+ license, see `LICENSE` for more information.


## Quickstart

Clone the repository from GitHub and install the package with setuptools:
```shell
$ git clone https://github.com/markus-ebke/billiards.git
$ python setup.py install
```

Note that _billiards_ depends on _numpy_, setuptools will install it
automatically.

To simulate one ball use:
```python
import billiards

# create empty world
sim = billiards.Simulation()

# add one ball at position (2, 0) with velocity (4, 0)
idx = sim.add_ball((2, 0), (4, 0))

# advance simulation by 10 time units
sim.step(10)

# print the position of the ball
print(sim.balls_position[idx])
```

The output is:
```python
[42.0, 0.0]
```


## Authors

- Markus Ebke - <https://github.com/markus-ebke>

