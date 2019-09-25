# -*- coding: utf-8 -*-
"""Main code for billiard simulation."""
from math import isinf, sqrt

import numpy as np

INF = float("inf")


def time_of_impact(pos1, vel1, radius1, pos2, vel2, radius2):
    """Calculate the time of impact of two moving balls.

    Args:
        pos1: Center of the first ball.
        vel1: Velocity of the first ball.
        radius1: Radius of the first ball.
        pos2: Center of the second ball.
        vel2: Velocity of the second ball.
        radius2: Radius of the second ball.

    Return:
        Non-negative time until impact, is infinite if there is no impact.

    """
    # switch to coordinate system of ball 1
    pos_diff = np.subtract(pos2, pos1)
    vel_diff = np.subtract(vel2, vel1)

    pos_dot_vel = np.dot(pos_diff, vel_diff)
    if pos_dot_vel >= 0:
        # balls are moving apart, no impact
        return INF
    else:
        pos_sqrd = np.dot(pos_diff, pos_diff)

        dist_sqrd = pos_sqrd - (radius1 + radius2) ** 2
        if dist_sqrd < 0:
            # one ball is inside the other, but don't count this as an impact
            return INF

        # time of impact is given as the solution of the quadratic equation
        # t^2 + b t + c = 0 with b and c below
        vel_sqrd = np.dot(vel_diff, vel_diff)  # note vel_sqrd != 0
        assert vel_sqrd > 0, vel_sqrd
        b = pos_dot_vel / vel_sqrd  # note b < 0
        assert b < 0, b
        c = dist_sqrd / vel_sqrd  # note c >= 0
        assert c >= 0, c

        discriminant = b ** 2 - c
        if discriminant <= 0:
            # the balls miss or slide past each other
            return INF

        # when writing the solution of the quadratic equation use that
        # c = t1 t2
        t1 = -b + sqrt(discriminant)  # note t1 > 0
        assert t1 > 0, (t1, b, sqrt(discriminant))
        t2 = c / t1  # note t2 >= 0, is zero if c = 0, i.e. balls are touching
        assert t2 >= 0, (t2, c)
        return min(t1, t2)


def elastic_collision(pos1, vel1, mass1, pos2, vel2, mass2):
    """Perfectly elastic collision between 2 balls.

    Args:
        pos1: Center of the first ball.
        vel1: Velocity of the first ball.
        mass1: Mass of the first ball.
        pos2: Center of the second ball.
        vel2: Velocity of the second ball.
        mass2: Mass of the second ball.

    Return:
        Two velocities after the collision.

    """
    # switch to coordinate system of ball 1
    pos_diff = np.subtract(pos2, pos1)
    vel_diff = np.subtract(vel2, vel1)

    pos_dot_vel = np.dot(pos_diff, vel_diff)
    assert pos_dot_vel < 0  # colliding balls do not move apart

    dist_sqrd = np.dot(pos_diff, pos_diff)

    bla = 2 * (pos_dot_vel * pos_diff) / ((mass1 + mass2) * dist_sqrd)
    vel1 += mass2 * bla
    vel2 -= mass1 * bla

    return vel1, vel2


class Simulation(object):
    """The simulation object represent a billiard world.

    Attributes:
        time: Current simulation time.
        num: Number of simulated balls.
        balls_position: List of 2D position of the balls' centers.
        balls_velocity: List of 2D velocities of the balls.
        balls_radius: List of numbers that represent the radii of the balls.
        toi_table: Lower-triangular matrix (= nested lists) of time of impacts
        toi_min: List of time-index pairs of the next collision for each ball
        toi_next: Time-index pair for the next collision

    """

    def __init__(self):
        """Create an empty world."""
        self.time = 0
        self.num = 0

        # ball properties
        self.balls_position = np.empty(shape=(0, 2), dtype=np.float64)
        self.balls_velocity = np.empty(shape=(0, 2), dtype=np.float64)
        self.balls_radius = []
        self.balls_mass = []

        # time of impact table
        self.toi_table = []
        self.toi_min = []
        self.toi_next = (INF, -1)

    def add_ball(self, pos, vel, radius=0, mass=1):
        """Add a ball at the given position with the given velocity.

        Args:
            pos: A 2D vector that represents the center of the ball.
            vel: A 2D vector that represents the velocity of the ball.
            radius (optional): The radius of the added ball.
                Defaults to 0 in which case the ball behaves like a point
                particle.

        Returns:
            List-index where the balls' information is stored.

        """
        # add ball properties
        self.balls_position = np.append(self.balls_position, [pos], axis=0)
        self.balls_velocity = np.append(self.balls_velocity, [vel], axis=0)
        self.balls_radius.append(radius)
        self.balls_mass.append(mass)

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

    def collision(self, idx1, idx2):
        """Update the velocities of two balls in the simulation that collide.

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

    def step(self, dt):
        """Advance the simulation by the given timestep.

        Args:
            dt: Size of the timestep.

        """
        end = self.time + dt
        while self.toi_next[0] <= end:
            # advance to the next collision
            self._move(self.toi_next[0])

            # get the balls that collide
            idx1 = self.toi_next[1]
            idx2 = self.toi_next[2]
            assert idx1 < idx2, (idx1, idx2)
            assert self.toi_min[idx2][0] == self.toi_next[0]
            assert self.toi_min[idx2][1] == idx1

            # handle collision between balls with index idx1 and idx2
            self.collision(idx1, idx2)

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

            self.toi_next = min(
                (t, i, j) for j, (t, i) in enumerate(self.toi_min)
            )

        assert end < self.toi_next[0]
        self._move(end)

    def _move(self, time):
        # just update position, no collision handling here
        dt = time - self.time
        self.balls_position += self.balls_velocity * dt
        self.time = time
