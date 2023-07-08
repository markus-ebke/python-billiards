"""The simulation module contains the main class for billiard simulations.

Use it like::

    from billiard import Billiard

"""
from collections.abc import Mapping
from math import isinf

import numpy as np

from .obstacles import Obstacle
from .physics import elastic_collision, toi_ball_ball

INF = float("inf")


class Billiard:
    """The Billiard class represents a billiard table.

    The 2-dimensional world is infinite in every direction and initialized with a list
    of obstacles. Billiard balls are placed via the `add_ball` method. Using `evolve`
    the simulation advances to the given timestamp. The ball positions and velocities
    can then be read out from the `balls_position` and `balls_velocity` attributes.

    Note that the `balls_initial_time` and `balls_initial_position` attributes are the
    time and position of the last collision for each ball. The actual position is
    calculated via pos = initial pos + vel * (time - initial time) and saved in
    `balls_position`.

    The properties of the balls can be tweaked mid-simulation by modifying
    `balls_position`, `balls_velocity` or `balls_radius`. If any of them were changed,
    the internal time-of-impact table must be recomputed via the `recompute_toi` method.

    The other methods are used to detect and resolve collisions during the execution of
    `evolve`.

    Attributes:
        balls_initial_time: Numpy.ndarray of initial times, note that each entry is a
            two-dimensional vector because of numpy's broadcasting rules.
        balls_initial_position: Numpy.ndarray of 2D position of the balls' centers at
            the initial time indicated in `balls_initial_time`.
        balls_radius: List of numbers that represent the radii of the balls.
        balls_mass: List of numbers that represent the masses of the balls.
        num: Number of simulated balls.
        time: Current simulation time.
        balls_position: Numpy.ndarray of 2D position of the balls' centers at the
            current simulation time. This property is computed from initial time,
            position and velocity.
        balls_velocity: Numpy.ndarray of 2D velocities of the balls.
        toi_table: Lower-triangular matrix (= list of np.ndarray) of time of impacts.
        next_ball_ball_collision: (time, index, index)-triple for the next collision.
        obstacles: List of obstacles on the table.
        next_ball_obstacle_collision: (time, index, obstacle) for next collision.
    """

    def __init__(self, obstacles=None):
        """Set up a billiard table populated with the given obstacles.

        Args:
            obstacles: Iterable containing billiards.obstacle.Obstacle objects.

        Raises:
            TypeError: If one of the obstacles is not a billiards.obstacle.Obstacle
                instance.
        """
        if obstacles is None:
            obstacles = []

        # ball properties
        self.balls_initial_time = np.empty(shape=(0, 2), dtype=np.float64)
        self.balls_initial_position = np.empty(shape=(0, 2), dtype=np.float64)
        self.balls_radius = []
        self.balls_mass = []
        self.num = 0

        # ball properties at a certain time of the simulation
        self.time = 0.0
        self.balls_position = np.empty(shape=(0, 2), dtype=np.float64)
        self.balls_velocity = np.empty(shape=(0, 2), dtype=np.float64)

        # time of impact records for ball-ball collisions
        self.toi_table = []  # time of impact for each ball-ball pair (triangular table)
        self._balls_toi = np.empty(shape=(0,), dtype=np.float64)  # min time in each row
        self._balls_idx = []  # Ball index (or -1) belonging to min time in each row
        self.next_ball_ball_collision = (INF, -1, 0)  # min of _balls_toi with indices
        # NOTE: for ball i we only check if there is a collision with balls j < i, so
        # the properties _balls_toi and _balls_idx will NOT include collisions with
        # balls j > i. If you reading them out externally, you will always miss some
        # collisions! (unless i == self.num)

        # check obstacles
        self.obstacles = []
        for obs in obstacles:
            if not isinstance(obs, Obstacle):
                msg = "{} must be an obstacle.Obstacle instance"
                raise TypeError(msg.format(obs))

            self.obstacles.append(obs)

        # time of impact records for ball-obstacle collisions
        # toi: time of impact with an obstacle for each ball (size == self.num)
        self._obstacles_toi = np.empty(shape=(0,), dtype=np.float64)
        self._obstacles_obs = []  # impacted obstacle (or None) for each ball
        self.next_ball_obstacle_collision = (INF, -1, (None, ()))  # min _obstacles_toi

    @property
    def next_collision(self):
        """Next collision as a (time, ball index, ball index or obstacle)-triplet."""
        if self.next_ball_ball_collision[0] <= self.next_ball_obstacle_collision[0]:
            return self.next_ball_ball_collision
        else:
            return self.next_ball_obstacle_collision

    def add_ball(self, pos, vel, radius=0.0, mass=1.0):
        """Add a ball at the given position with the given velocity.

        Note that balls with zero radii act like point particles and two balls with zero
        radii will never collide.

        Balls with zero mass don't push other balls around, balls with infinite mass are
        not pushed around by others. If two balls with zero mass collide this will raise
        a warning from numpy. If two balls with infinite mass collide only the first one
        is treated with infinite mass and the other one gets pushed around.

        Args:
            pos: A 2D vector that represents the center of the ball.
            vel: A 2D vector that represents the velocity of the ball.
            radius (optional): The radius of the added ball.
                Defaults to 0 in which case the ball behaves like a point particle.
            mass (optional): Ball mass, defaults to 1, can be 0 or inf.

        Returns:
            List-index where the balls' information is stored.

        """
        # add ball properties
        self.balls_initial_time = np.append(
            self.balls_initial_time, [(self.time, self.time)], axis=0
        )  # note that the shape is (num, 2) for broadcasting in self._move
        self.balls_initial_position = np.append(
            self.balls_initial_position, [pos], axis=0
        )
        self.balls_velocity = np.append(self.balls_velocity, [vel], axis=0)
        self.balls_radius.append(float(radius))
        self.balls_mass.append(float(mass))

        # update self.balls_position
        self._move(self.time)

        # update ball count and calculate index
        self.num += 1
        idx = self.num - 1  # last added ball is at the end

        # calculate next time of impact
        row_list = [self.calc_toi(j, idx) for j in range(idx)]
        row = np.asarray(row_list, dtype=np.float64)  # new row in table is numpy array
        self.toi_table.append(row)

        if row.size > 0:
            toi_idx = row.argmin()
            self._balls_toi = np.append(self._balls_toi, row[toi_idx])
            self._balls_idx.append(toi_idx)
        else:
            # only one ball in the scene => no collisions with other balls
            self._balls_toi = np.append(self._balls_toi, INF)
            self._balls_idx.append(-1)

        next_idx = self._balls_toi.argmin()
        self.next_ball_ball_collision = (
            self._balls_toi[next_idx],
            self._balls_idx[next_idx],
            next_idx,
        )  # note that first ball index must be lower than second index

        # calculate time of impact for obstacles
        t_min, obs_and_args_min = self.calc_next_obstacle(idx)
        self._obstacles_toi = np.append(self._obstacles_toi, t_min)
        self._obstacles_obs.append(obs_and_args_min)
        ball_idx = self._obstacles_toi.argmin()
        self.next_ball_obstacle_collision = (
            self._obstacles_toi[ball_idx],
            ball_idx,
            self._obstacles_obs[ball_idx],
        )

        # sanity checks
        assert self.balls_initial_time.shape == (self.num, 2)
        assert self.balls_initial_position.shape == (self.num, 2)
        assert self.balls_position.shape == (self.num, 2)
        assert self.balls_velocity.shape == (self.num, 2)
        assert len(self.balls_radius) == self.num
        assert len(self.balls_mass) == self.num
        assert len(self.toi_table) == self.num
        assert self._balls_toi.shape == (self.num,)
        assert len(self._balls_idx) == self.num
        assert self._obstacles_toi.shape == (self.num,)
        assert len(self._obstacles_obs) == self.num

        return idx

    def recompute_toi(self, indices=None):
        """Recompute the time-of-impact for the given ball(s).

        Must be called after modifying `balls_position`, `balls_velocity` or
        `balls_radius`. If only one ball was touched, supply the index of the ball to
        update only its entries in the time-of-impact table. If several balls were
        touched, supply a list of indices. If no indices are given, will recompute table
        for all balls.

        Args:
            indices (optional): Index of a ball whose time of impact entries should be
                recomputed. If an iterator is given, recompute entries for all indicated
                balls (iterator elements must be valid indices). If no indices are
                given, recompute for all balls.

        Raises:
            TypeError: if indices is not None or not int or not iterable.

        """
        # check type of indices
        if indices is None:
            indices = range(self.num)  # i.e. recompute all balls
        elif isinstance(indices, int):
            indices = [indices]  # i.e. recompute only single ball
        else:
            # try to see if iterable, if not will automatically raise TypeError
            indices = iter(indices)  # i.e. recompute a collection of balls

        # check which balls got an assigment to self.balls_position and update their
        # initial time and position
        dt = self.time - self.balls_initial_position
        original_position = self.balls_initial_position + self.balls_velocity * dt
        modified = np.any(self.balls_position != original_position, axis=1)
        for idx in np.flatnonzero(modified).tolist():
            self.balls_initial_time[idx] = self.time
            self.balls_initial_position[idx] = self.balls_position[idx]
        # TODO should we warn the user if the indices of the modified balls is not a
        # subset of the supplied list of indices?

        min_idx = self.num  # = min(indices), used later to update toi_min
        recompute_pairs = set()  # skip indices that we already recomputed
        for idx in indices:
            # update time of impact for ball-ball collisions
            for j in range(idx):
                if (idx, j) not in recompute_pairs:
                    self.toi_table[idx][j] = self.calc_toi(idx, j)
                    recompute_pairs.add((idx, j))

            for i in range(idx + 1, self.num):
                if (i, idx) not in recompute_pairs:
                    self.toi_table[i][idx] = self.calc_toi(i, idx)
                    recompute_pairs.add((i, idx))

            # update time of impact for the next ball-obstacle collision
            t_min, obs_and_args_min = self.calc_next_obstacle(idx)
            self._obstacles_toi[idx] = t_min
            self._obstacles_obs[idx] = obs_and_args_min

            # update minimum index
            min_idx = idx if idx < min_idx else min_idx

        # update toi_min, we skip i = 0 because self.toi_min[0] is always (INF, -1)
        for i in range(min_idx if min_idx > 0 else 1, self.num):
            row = self.toi_table[i]
            toi_idx = row.argmin()
            self._balls_toi[i] = row[toi_idx]
            self._balls_idx[i] = toi_idx

        # update next ball ball collision
        assert self._balls_toi[0] == INF  # first entry always invalid
        assert self._balls_idx[0] == -1
        next_idx = self._balls_toi.argmin()
        self.next_ball_ball_collision = (
            self._balls_toi[next_idx],
            self._balls_idx[next_idx],
            next_idx,
        )

        # update next ball obstacle collision
        ball_idx = self._obstacles_toi.argmin()
        self.next_ball_obstacle_collision = (
            self._obstacles_toi[ball_idx],
            ball_idx,
            self._obstacles_obs[ball_idx],
        )

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

        return self.time + toi_ball_ball(p1, v1, r1, p2, v2, r2)

    def calc_next_obstacle(self, idx):
        """Find the closest colliding obstacle for the given ball.

        Args:
            idx: Index of ball.

        Returns:
            tuple: (time, (obstacle, args))-pair of the next collision or (INF, None) if
            ball will not impact any obstacle.
        """
        pos = self.balls_position[idx]
        vel = self.balls_velocity[idx]
        radius = self.balls_radius[idx]

        t_min, obs_and_args_min = INF, None
        for obs in self.obstacles:
            t, args = obs.calc_toi(pos, vel, radius)
            if t < t_min:
                t_min, obs_and_args_min = t, (obs, args)

        return self.time + t_min, obs_and_args_min

    def evolve(self, end_time, time_callback=None, ball_callbacks=None):
        """Advance the simulation until the given time is reached.

        Will call bounce_ballball and bounce_ballobstacle repeatedly (which one depends
        on self.next_ball_ball_collision and self.next_ball_obstacle_collision) until
        the time = end_time is reached.

        Args:
            end_time: Time until which the billiard should be simulated.
            time_callback (optional): Is called every collision with time as argument.
            ball_callbacks (optional): Mapping from ball index to a callable. The
                function is called at every collision of the indicated ball and should
                have the signature func(time: float,
                position: np.ndarray(shape=(2,), dtype=np.float64),
                velocity before: np.ndarray(shape=(2,), dtype=np.float64),
                velocity after: np.ndarray(shape=(2,), dtype=np.float64),
                ball index: int or obstacle: billiard.obstacle.Obstacle)

        Returns:
            number of ball-ball and ball-obstacle collisions as a tuple.

        """
        if ball_callbacks is None:
            ball_callbacks = {}  # empty dict
        elif not isinstance(ball_callbacks, Mapping):
            raise TypeError(
                "Argument 'ball_callbacks' must be a mapping, "
                f"not a {type(ball_callbacks)}"
            )

        ball_collisions, obstacle_collisions = 0, 0
        while self.next_collision[0] <= end_time:
            # decide what kind of collision we are dealing with
            if self.next_ball_ball_collision[0] <= self.next_ball_obstacle_collision[0]:
                self.bounce_ballball(ball_callbacks)
                ball_collisions += 1
            else:
                self.bounce_ballobstacle(ball_callbacks)
                obstacle_collisions += 1

            if time_callback is not None:
                time_callback(self.time)

        # go from time of last collision to the end time
        assert end_time < self.next_collision[0]
        self._move(end_time)

        return (ball_collisions, obstacle_collisions)

    def bounce_ballball(self, ball_callbacks):
        """Advance to the next ball-ball collision and handle it.

        Args:
            ball_callbacks: Mapping from ball index to a callable.

        """
        t, idx1, idx2 = self.next_ball_ball_collision

        # get the balls that collide
        assert idx1 < idx2, (idx1, idx2)
        assert self._balls_toi[idx2] == t
        assert self._balls_idx[idx2] == idx1

        # advance to the next collision and handle it
        self._move(t)
        self._collide_balls(idx1, idx2, ball_callbacks)

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
            self._balls_toi[i] = row[toi_idx]
            self._balls_idx[i] = toi_idx

        assert self._balls_toi[0] == INF  # first entry always invalid
        assert self._balls_idx[0] == -1
        next_idx = self._balls_toi.argmin()
        self.next_ball_ball_collision = (
            self._balls_toi[next_idx],
            self._balls_idx[next_idx],
            next_idx,
        )

        # update time of impact for the next ball-obstacle collision
        t_min, obs_and_args_min = self.calc_next_obstacle(idx1)
        self._obstacles_toi[idx1] = t_min
        self._obstacles_obs[idx1] = obs_and_args_min
        t_min, obs_and_args_min = self.calc_next_obstacle(idx2)
        self._obstacles_toi[idx2] = t_min
        self._obstacles_obs[idx2] = obs_and_args_min

        ball_idx = self._obstacles_toi.argmin()
        self.next_ball_obstacle_collision = (
            self._obstacles_toi[ball_idx],
            ball_idx,
            self._obstacles_obs[ball_idx],
        )

    def bounce_ballobstacle(self, ball_callbacks):
        """Advance to the next ball-obstacle collision and handle it.

        Args:
            ball_callbacks: Mapping from ball index to a callable.

        """
        t, idx, obs_and_args = self.next_ball_obstacle_collision
        assert self._obstacles_toi[idx] == t
        assert self._obstacles_obs[idx] == obs_and_args

        # advance to the next collision and handle it
        self._move(t)
        self._collide_obstacle(idx, obs_and_args, ball_callbacks)

        # update time of impact for ball-ball collisions
        for j in range(idx):
            self.toi_table[idx][j] = self.calc_toi(idx, j)

        for i in range(idx + 1, self.num):
            self.toi_table[i][idx] = self.calc_toi(i, idx)

        # update toi_min, we skip i = 0 because self.toi_min[0] is always (INF, -1)
        for i in range(idx if idx > 0 else 1, self.num):
            row = self.toi_table[i]
            toi_idx = row.argmin()
            self._balls_toi[i] = row[toi_idx]
            self._balls_idx[i] = toi_idx

        assert self._balls_toi[0] == INF  # first entry always invalid
        assert self._balls_idx[0] == -1
        next_idx = self._balls_toi.argmin()
        self.next_ball_ball_collision = (
            self._balls_toi[next_idx],
            self._balls_idx[next_idx],
            next_idx,
        )

        # update time of impact for the next ball-obstacle collision
        t_min, obs_and_args_min = self.calc_next_obstacle(idx)
        self._obstacles_toi[idx] = t_min
        self._obstacles_obs[idx] = obs_and_args_min

        ball_idx = self._obstacles_toi.argmin()
        self.next_ball_obstacle_collision = (
            self._obstacles_toi[ball_idx],
            ball_idx,
            self._obstacles_obs[ball_idx],
        )

    def _move(self, time):
        # just update position, no collision handling here
        dt = time - self.balls_initial_time  # note: shape is (num, 2) for broadcasting
        self.balls_position = self.balls_initial_position + self.balls_velocity * dt
        self.time = time

    def _collide_balls(self, idx1, idx2, ball_callbacks):
        """Update the velocities of two colliding balls in the simulation.

        Args:
            idx1: Index of one ball.
            idx2: Index of another ball.
            ball_callbacks: Mapping from ball index to a callable.

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

        # compute new velocites
        vnew1, vnew2 = elastic_collision(p1, v1, m1, p2, v2, m2)

        # call callback here, because updating self.balls_velocity will change v1 and v2
        # note: no copy of vnew1 and nvew2 needed, because after we assign it we never
        # use it again
        if idx1 in ball_callbacks:
            ball_callbacks[idx1](self.time, p1.copy(), v1.copy(), vnew1, idx2)
        if idx2 in ball_callbacks:
            ball_callbacks[idx2](self.time, p2.copy(), v2.copy(), vnew2, idx1)

        # update ball time, position and velocity
        self.balls_initial_time[idx1] = self.time
        self.balls_initial_time[idx2] = self.time
        self.balls_initial_position[idx1] = p1
        self.balls_initial_position[idx2] = p2
        self.balls_velocity[idx1] = vnew1
        self.balls_velocity[idx2] = vnew2

    def _collide_obstacle(self, idx, obs_and_args, ball_callbacks):
        """Update velocity of a ball colliding with an obstacle.

        Args:
            idx: Index of the colliding ball.
            obs_and_args: The obstacle with which the ball collides and optional
                arguments for obstacle.collide.
            ball_callbacks: Mapping from ball index to a callable.

        """
        pos = self.balls_position[idx]
        vel = self.balls_velocity[idx]
        radius = self.balls_radius[idx]

        obs, args = obs_and_args
        new_vel = obs.collide(pos, vel, radius, *args)

        # call callback here, because updating self.balls_velocity will change vel
        # note: no copy of new_vel needed, because after we assign it we never use it
        # again
        if idx in ball_callbacks:
            ball_callbacks[idx](self.time, pos.copy(), vel.copy(), new_vel, obs)

        # update ball time, position and velocity
        self.balls_initial_time[idx] = self.time
        self.balls_initial_position[idx] = pos
        self.balls_velocity[idx] = new_vel
