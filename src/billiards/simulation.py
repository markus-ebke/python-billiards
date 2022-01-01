"""The simulation module contains the main class for billiard simulations.

Use it like::

    from billiard import Billiard

"""
from math import isinf

import numpy as np

from .obstacles import Obstacle
from .physics import elastic_collision, time_of_impact

INF = float("inf")


class Billiard:
    """The Billiard class represents a billiard table.

    The 2-dimensional world is infinite in every direction and initialized with
    a list of obstacles. Billiard balls are placed via the `add_ball` method.
    Using Billiard.evolve the simulation is advanced to the given timestamp.
    The other methods are used to detect and resolve collisions during the
    execution of evolve.

    Attributes:
        time: Current simulation time.
        num: Number of simulated balls.
        balls_position: List of 2D position of the balls' centers.
        balls_velocity: List of 2D velocities of the balls.
        balls_radius: List of numbers that represent the radii of the balls.
        balls_mass: List of numbers that represent the masses of the balls.
        toi_table: Lower-triangular matrix (= list of np.array) of time of impacts.
        toi_min: List of time-index pairs of the next collision for each ball.
        toi_next: Time-index-index triple for the next collision.
        obstacles: List of obstacles on the table.
        obstacles_toi: time-obstacle pairs for each ball.
        obstacles_next: Time-index-obstacle pair of the next obstacle impact.

    """

    def __init__(self, obstacles=None):
        """Set up a billiard table populated with the given obstacles.

        Args:
            obstacles: Iterable containing billiards.obstacle.Obstacle objects.

        Raises:
            TypeError: If one of the obstacles is not a
            billiards.obstacle.Obstacle instance.
        """
        if obstacles is None:
            obstacles = []

        # initalize time and number of balls to 0
        self.time = 0.0
        self.num = 0

        # ball properties
        self.balls_position = np.empty(shape=(0, 2), dtype=np.float64)
        self.balls_velocity = np.empty(shape=(0, 2), dtype=np.float64)
        self.balls_radius = []
        self.balls_mass = []

        # time of impact table for ball-ball collisions
        self.toi_table = []  # time of impact for each ball-ball pair
        self.toi_min = []  # next time of impact for each ball
        self.toi_next = (INF, -1, 0)  # next ball-ball collision

        # check obstacles
        self.obstacles = []
        for obs in obstacles:
            if not isinstance(obs, Obstacle):
                msg = "{} must be an obstacle.Obstacle instance"
                raise TypeError(msg.format(obs))

            self.obstacles.append(obs)

        # time of impact list for ball-obstacle collisions
        self.obstacles_toi = []  # next time of impact for each ball
        self.obstacles_next = (INF, -1, None)  # next ball-obstacle collision

    def add_ball(self, pos, vel, radius=0.0, mass=1.0):
        """Add a ball at the given position with the given velocity.

        Note that balls with zero radii act like point particles and two balls
        with zero radii will never collide.

        Balls with zero mass don't push other balls around, balls with infinite
        mass are not pushed around by others. If two balls with zero mass
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
        row_gen = (self.calc_toi(j, idx) for j in range(idx))
        row = np.fromiter(row_gen, dtype=np.float64)
        self.toi_table.append(row)

        if row.size > 0:
            toi_idx = row.argmin()
            self.toi_min.append((row[toi_idx], toi_idx))
        else:
            # only one ball in the scene => no collisions with other balls
            self.toi_min.append((INF, -1))  # use invalid index

        self.toi_next = min((t, j, i) for i, (t, j) in enumerate(self.toi_min))

        # calculate time of impact for obstacles
        self.obstacles_toi.append(self.calc_next_obstacle(idx))
        self.obstacles_next = min(
            (t, i, obs) for i, (t, obs) in enumerate(self.obstacles_toi)
        )

        # sanity checks
        assert self.balls_position.shape[0] == self.num
        assert self.balls_velocity.shape[0] == self.num
        assert len(self.balls_radius) == self.num
        assert len(self.balls_mass) == self.num
        assert len(self.toi_table) == self.num
        assert len(self.obstacles_toi) == self.num

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

    def calc_next_obstacle(self, idx):
        """Find the closest colliding obstacle for the given ball.

        Args:
            idx: Index of ball.

        Returns:
            tuple: (time, obstacle)-pair of the next collision or (INF, None)
            if ball will not impact any obstacle.
        """
        pos = self.balls_position[idx]
        vel = self.balls_velocity[idx]
        radius = self.balls_radius[idx]

        t_min, obs_min = INF, None
        for obs in self.obstacles:
            t = obs.calc_toi(pos, vel, radius)
            if t < t_min:
                t_min, obs_min = t, obs

        return self.time + t_min, obs_min

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

    def collide_obstacle(self, idx, obs):
        """Update velocity of a ball colliding with an obstacle.

        Args:
            idx: Index of the colliding ball.
            obs: The obstacle with which the ball collides.

        """
        pos = self.balls_position[idx]
        vel = self.balls_velocity[idx]
        radius = self.balls_radius[idx]

        new_vel = obs.collide(pos, vel, radius)
        self.balls_velocity[idx] = new_vel

    def evolve(self, end_time):
        """Advance the simulation until the given time is reached.

        Will call bounce_ballball and bounce_ballobstacle repeatetly (which one
        depends on self.toi_next and self.obstacles_next) until the end_time
        is reached.

        Args:
            end_time: Time until which the billiard should be simulated.

        Returns:
            list: List of collisions, each item is a (float, int, int)-triplet
            where the first number is the time of impact and the next two
            integers are the indices of the balls that collided. If a ball
            collided with an obstacle, the obstacle is returned as the third
            element.

        """
        collisions = []
        while min(self.toi_next[0], self.obstacles_next[0]) <= end_time:
            # decide what kind of collision we are dealing with
            if self.toi_next[0] <= self.obstacles_next[0]:
                coll = self.bounce_ballball()
            else:
                coll = self.bounce_ballobstacle()

            collisions.append(coll)

        assert end_time < min(self.toi_next[0], self.obstacles_next[0])
        self._move(end_time)

        return collisions

    def bounce_ballball(self):
        """Advance to the next ball-ball collision and handle it.

        Returns:
            float: Time of impact of the just handled collision.
            int: Index of one ball that collided.
            int: Index of the other ball.

        """
        t, idx1, idx2 = self.toi_next

        # get the balls that collide
        assert idx1 < idx2, (idx1, idx2)
        assert self.toi_min[idx2] == (t, idx1)

        # advance to the next collision and handle it
        self._move(t)
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

        # update toi_min, we skip i = 0 because self.toi_min[0] is always (INF, -1)
        for i in range(idx1 if idx1 > 0 else 1, self.num):
            row = self.toi_table[i]
            toi_idx = row.argmin()
            self.toi_min[i] = (row[toi_idx], toi_idx)

        assert self.toi_min[0] == (INF, -1)  # first entry always invalid
        self.toi_next = min((t, i, j) for j, (t, i) in enumerate(self.toi_min))

        # update time of impact for the next ball-obstacle collision
        self.obstacles_toi[idx1] = self.calc_next_obstacle(idx1)
        self.obstacles_toi[idx2] = self.calc_next_obstacle(idx2)

        self.obstacles_next = min(
            (t, i, obs) for i, (t, obs) in enumerate(self.obstacles_toi)
        )

        return (t, idx1, idx2)

    def bounce_ballobstacle(self):
        """Advance to the next ball-obstacle collision and handle it.

        Returns:
            float: Time of impact of the just handled collision.
            int: Index of the ball that collided.
            billiards.obstacle.Obstacle: Obstacle that the ball collided with.

        """
        t, idx, obs = self.obstacles_next
        assert self.obstacles_toi[idx] == (t, obs)

        # advance to the next collision and handle it
        self._move(t)
        self.collide_obstacle(idx, obs)

        # update time of impact for ball-ball collisions
        for j in range(idx):
            self.toi_table[idx][j] = self.calc_toi(idx, j)

        for i in range(idx + 1, self.num):
            self.toi_table[i][idx] = self.calc_toi(i, idx)

        # update toi_min, we skip i = 0 because self.toi_min[0] is always (INF, -1)
        for i in range(idx if idx > 0 else 1, self.num):
            row = self.toi_table[i]
            toi_idx = row.argmin()
            self.toi_min[i] = (row[toi_idx], toi_idx)

        assert self.toi_min[0] == (INF, -1)  # first entry always invalid
        self.toi_next = min((t, i, j) for j, (t, i) in enumerate(self.toi_min))

        # update time of impact for the next ball-obstacle collision
        self.obstacles_toi[idx] = self.calc_next_obstacle(idx)

        self.obstacles_next = min(
            (t, i, obs) for i, (t, obs) in enumerate(self.obstacles_toi)
        )

        return (t, idx, obs)

    def _move(self, time):
        # just update position, no collision handling here
        dt = time - self.time
        self.balls_position += self.balls_velocity * dt
        self.time = time
