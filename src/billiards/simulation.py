# -*- coding: utf-8 -*-
"""The simulation module contains the main code for a billiard simulation."""
from math import isinf

import numpy as np

from .physics import elastic_collision, time_of_impact

INF = float("inf")


class Billiard(object):
    """The billiard class represent a billiard world.

    By default the 2-dimensional world is infinite in every direction.
    To populate it use the `add_ball` method.

    Attributes:
        time: Current simulation time.
        num: Number of simulated balls.
        balls_position: List of 2D position of the balls' centers.
        balls_velocity: List of 2D velocities of the balls.
        balls_radius: List of numbers that represent the radii of the balls.
        balls_mass: List of number that represent the masses of the balls.
        toi_table: Lower-triangular matrix (= nested lists) of time of impacts.
        toi_min: List of time-index pairs of the next collision for each ball.
        toi_next: Time-index-index triple for the next collision.

    """

    def __init__(self):
        """Create an empty world."""
        self.time = 0.0
        self.num = 0

        # ball properties
        self.balls_position = np.empty(shape=(0, 2), dtype=np.float64)
        self.balls_velocity = np.empty(shape=(0, 2), dtype=np.float64)
        self.balls_radius = []
        self.balls_mass = []

        # time of impact table
        self.toi_table = []
        self.toi_min = []
        self.toi_next = (INF, -1, 0)

    def add_ball(self, pos, vel, radius=0.0, mass=1.0):
        """Add a ball at the given position with the given velocity.

        Note that balls with zero radius act like point particles and two balls
        with zero radius will never collide.

        Balls with zero mass don't push other balls around, balls with infinite
        mass are not pushed around themselves. If two balls with zero mass
        collide this will raise a warning from numpy. If two balls with
        infinite mass collide only the first one is treated with infinite mass
        and the other one gets pushed around.

        Args:
            pos: A 2D vector that represents the center of the ball.
            vel: A 2D vector that represents the velocity of the ball.
            radius (optional): The radius of the added ball.
                Defaults to 0 in which case the ball behaves like a point
                particle.
            mass (optional): Ball mass, defaults to 1, can be 0 or inf.

        Returns:
            List-index where the balls' information is stored.

        """
        # add ball properties
        self.balls_position = np.append(self.balls_position, [pos], axis=0)
        self.balls_velocity = np.append(self.balls_velocity, [vel], axis=0)
        self.balls_radius.append(float(radius))
        self.balls_mass.append(float(mass))

        # update ball count and calculate index
        self.num += 1
        idx = self.num - 1  # last added ball is at the end

        # calculate next time of impact
        row = [self.calc_toi(j, idx) for j in range(idx)]
        self.toi_table.append(row)

        toi_pairs = ((t, j) for (j, t) in enumerate(row))
        toi_idx = min(toi_pairs, default=(INF, -1))
        self.toi_min.append(toi_idx)

        self.toi_next = min((t, j, i) for i, (t, j) in enumerate(self.toi_min))

        # sanity checks
        assert self.balls_position.shape[0] == self.num
        assert self.balls_velocity.shape[0] == self.num
        assert len(self.balls_radius) == self.num
        assert len(self.balls_mass) == self.num
        assert len(self.toi_table) == self.num

        return idx

    def calc_toi(self, idx1, idx2):
        """Calculate time of impact of two balls in the simulation.

        Args:
            idx1: Index of one ball.
            idx2: Index of another ball.

        Returns:
            Time of impact between the two balls.

        """
        p1 = self.balls_position[idx1]
        v1 = self.balls_velocity[idx1]
        r1 = self.balls_radius[idx1]

        p2 = self.balls_position[idx2]
        v2 = self.balls_velocity[idx2]
        r2 = self.balls_radius[idx2]

        return self.time + time_of_impact(p1, v1, r1, p2, v2, r2)

    def collide_balls(self, idx1, idx2):
        """Update the velocities of two colliding balls in the simulation.

        Args:
            idx1: Index of one ball.
            idx2: Index of another ball.

        """
        p1 = self.balls_position[idx1]
        v1 = self.balls_velocity[idx1]
        m1 = self.balls_mass[idx1]

        p2 = self.balls_position[idx2]
        v2 = self.balls_velocity[idx2]
        m2 = self.balls_mass[idx2]

        # collision with infinite masses: the other mass is effectively zero
        if isinf(m1):
            m1, m2 = (1, 0)
        elif isinf(m2):
            m1, m2 = (0, 1)

        v1, v2 = elastic_collision(p1, v1, m1, p2, v2, m2)
        self.balls_velocity[idx1] = v1
        self.balls_velocity[idx2] = v2

    def evolve(self, end_time):
        """Advance the simulation until the given time is reached.

        Args:
            end_time: Time until which the billiard should be simulated.

        """
        while self.toi_next[0] <= end_time:
            self.bounce()

        assert end_time < self.toi_next[0]
        self._move(end_time)

    def bounce(self):
        """Advance to the next collision and handle it."""
        t, idx1, idx2 = self.toi_next

        # advance to the next collision
        self._move(t)

        # get the balls that collide
        assert idx1 < idx2, (idx1, idx2)
        assert self.toi_min[idx2] == (t, idx1)

        # handle collision between balls with index idx1 and idx2
        self.collide_balls(idx1, idx2)

        # update time of impact for the two balls
        self.toi_table[idx2][idx1] = INF
        assert self.calc_toi(idx1, idx2) == INF

        for j in range(idx1):
            self.toi_table[idx1][j] = self.calc_toi(idx1, j)
            self.toi_table[idx2][j] = self.calc_toi(idx2, j)

        for i in range(idx1 + 1, idx2):
            self.toi_table[i][idx1] = self.calc_toi(i, idx1)
            self.toi_table[idx2][i] = self.calc_toi(idx2, i)

        for i in range(idx2 + 1, self.num):
            self.toi_table[i][idx1] = self.calc_toi(i, idx1)
            self.toi_table[i][idx2] = self.calc_toi(i, idx2)

        # update toi_min
        for i in range(idx1, self.num):
            row = self.toi_table[i]
            toi_pairs = ((t, j) for (j, t) in enumerate(row))
            toi_idx = min(toi_pairs, default=(INF, -1))
            self.toi_min[i] = toi_idx

        self.toi_next = min((t, i, j) for j, (t, i) in enumerate(self.toi_min))

    def _move(self, time):
        # just update position, no collision handling here
        dt = time - self.time
        self.balls_position += self.balls_velocity * dt
        self.time = time
