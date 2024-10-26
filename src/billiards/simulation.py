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
    """The Billiard class represents a 2-dimensional billiard table.

    The 2-dimensional world is infinite in every direction and initialized with a list
    of obstacles instanced from `billiard.obstacle.Obstacle`. Place new billiard balls
    via the `add_ball` method. Use `evolve` to advance the simulation to a given
    timestamp. Access the updated simulation state via the `time`, `balls_position` and
    `balls_velocity` attributes.

    The properties of the balls can be tweaked mid-simulation by modifying entries of
    `balls_position`, `balls_velocity`, `balls_radius` and `balls_mass`. If the
    position, velocity or radius of some balls where changed, the corresponding entries
    of the internal time-of-impact table must be recomputed with the `recompute_toi`
    method.

    The `balls_initial_time` and `balls_initial_position` attributes are the time and
    position of the last collision for each ball. The actual position at a time between
    the last collision (at `balls_initial_time.max()`) and the next collision (at
    `next_collision[0]`) is given by the formula
    `position = initial position + velocity * (time - initial time)`.

    The methods `bounce_ball_ball` and `bounce_ball_obstacle` are used during the
    execution of `evolve` to detect and resolve collisions.

    Attributes:
        time: Current simulation time.
        balls_initial_time: Numpy.ndarray of initial times, note that each entry is a
            two-dimensional vector because of numpy's broadcasting rules.
        balls_initial_position: Numpy.ndarray of 2D position of the balls' centers at
            the initial time indicated in `balls_initial_time`.
        balls_position: Numpy.ndarray of 2D position of the balls' centers at the
            current simulation time. This property is computed from initial time,
            position and velocity.
        balls_velocity: Numpy.ndarray of 2D velocities of the balls.
        balls_radius: List of numbers that represent the radii of the balls.
        balls_mass: List of numbers that represent the masses of the balls.
        obstacles: List of obstacles, i.e. instances of `billiard.obstacle.Obstacle`.
        toi_table: Lower-triangular matrix (= list of np.ndarray) of time of impacts.
    """

    def __init__(self, obstacles=None):
        """Set up a billiard table populated with the given obstacles.

        Args:
            obstacles: Iterable containing `billiards.obstacle.Obstacle` objects.

        Raises:
            TypeError: If one of the obstacles is not a `billiards.obstacle.Obstacle`
                instance.
        """
        if obstacles is None:
            obstacles = []

        # Ball properties, the shape is (num, 2) for broadcasting in self._move
        self.balls_initial_time = np.empty(shape=(0, 2), dtype=np.float64)
        self.balls_initial_position = np.empty(shape=(0, 2), dtype=np.float64)
        self.balls_radius = []
        self.balls_mass = []

        # State of the balls at a certain time of the simulation
        self.time = 0.0
        self.balls_position = np.empty(shape=(0, 2), dtype=np.float64)
        self.balls_velocity = np.empty(shape=(0, 2), dtype=np.float64)

        # time of impact records for ball-ball collisions
        self.toi_table = []  # time of impact for each ball-ball pair (triangular table)
        self._balls_toi = np.empty(shape=(0,), dtype=np.float64)  # min time in each row
        self._balls_idx = []  # Ball index (or -1) belonging to min time in each row

        # next_ball_ball_collision is the minimum of _balls_toi and the indices i and j
        # of the colliding balls in the order i > j
        # NOTE: for ball i we only check if there is a collision with balls j < i, so
        # the properties _balls_toi and _balls_idx will NOT include collisions with
        # balls j > i. If you reading them out externally, you will always miss some
        # collisions! (unless i == self.count)
        self._next_ball_ball_collision = (INF, np.int64(-1), np.int64(0))

        # check obstacles
        self.obstacles = []
        for obs in obstacles:
            if not isinstance(obs, Obstacle):
                msg = "{} must be an obstacle.Obstacle instance"
                raise TypeError(msg.format(obs))

            self.obstacles.append(obs)

        # time of impact records for ball-obstacle collisions
        # toi: time of impact with an obstacle for each ball (size == self.count)
        self._obstacles_toi = np.empty(shape=(0,), dtype=np.float64)
        self._obstacles_obs = []  # next colliding obstacle (or None) for each ball

        # next_ball_obstacle_collision is the mininum of _obstacles_toi, the ball index
        # and the obstacle along with optional arguments for the collide method
        self._next_ball_obstacle_collision = (INF, np.int64(-1), None)

    @property
    def count(self):
        """Number of balls in the billiard."""
        return self.balls_position.shape[0]

    @property
    def next_ball_ball_collision(self):
        """Next ball-ball collision as a (time, ball index, ball index)-triplet."""
        t, i, j = self._next_ball_ball_collision
        return (float(t), int(i), int(j))

    @property
    def next_ball_obstacle_collision(self):
        """Next ball-obstacle collision as (time, ball index, (obstacle, args))."""
        t, i, obs_args = self._next_ball_obstacle_collision
        return (float(t), int(i), obs_args)

    @property
    def next_collision(self):
        """Next collision as a (time, ball index, ball index or obstacle)-triplet."""
        if self._next_ball_ball_collision[0] <= self._next_ball_obstacle_collision[0]:
            t, i, j = self._next_ball_ball_collision
            return (float(t), int(i), int(j))
        else:
            t, i, obs_args = self._next_ball_obstacle_collision
            return (float(t), int(i), obs_args)

    def add_ball(self, pos, vel=(0, 0), radius=0.0, mass=1.0):
        """Add a ball at the given position with the given velocity.

        Note that balls with zero radii act like point particles and two balls with zero
        radii will never collide.

        Balls with zero mass don't push other balls around, balls with infinite mass are
        not pushed around by others. If two balls with zero mass collide this will raise
        a warning from numpy. If two balls with infinite mass collide only the first one
        is treated with infinite mass and the other one gets pushed around.

        Args:
            pos: A 2D vector that represents the center of the ball.
            vel (optional): A 2D vector that represents the velocity of the ball.
                Defaults to (0, 0), i.e. the ball is not moving.
            radius (optional): The radius of the added ball.
                Defaults to 0 in which case the ball behaves like a point particle.
            mass (optional): Ball mass, used when resolving ball-ball collisions.
                Can be 0 or infinite, defaults to 1.0.

        Returns:
            List-index where the balls' information is stored.
        """
        # Add to ball properties
        self.balls_initial_time = np.append(
            self.balls_initial_time, [(self.time, self.time)], axis=0
        )
        self.balls_initial_position = np.append(
            self.balls_initial_position, [pos], axis=0
        )
        self.balls_velocity = np.append(self.balls_velocity, [vel], axis=0)
        self.balls_radius.append(float(radius))
        self.balls_mass.append(float(mass))

        # Update self.balls_position, note that this will also update self.count
        self._move(self.time)
        idx = self.count - 1  # last added ball is at the end

        # Calculate next time of impact
        row_list = [self._detect_ball_collision(j, idx) for j in range(idx)]
        row = np.asarray(row_list, dtype=np.float64)  # new row in table is numpy array
        self.toi_table.append(row)

        if row.size > 0:
            toi_idx = row.argmin()
            self._balls_toi = np.append(self._balls_toi, row[toi_idx])
            self._balls_idx.append(toi_idx)
        else:
            # Only one ball in the scene => no collisions with other balls
            self._balls_toi = np.append(self._balls_toi, INF)
            self._balls_idx.append(np.int64(-1))

        next_idx = self._balls_toi.argmin()
        self._next_ball_ball_collision = (
            self._balls_toi[next_idx],
            self._balls_idx[next_idx],
            next_idx,
        )  # note that first ball index must be lower than second index

        # Calculate time of impact for obstacles
        t_min, obs_and_args_min = self._detect_next_obstacle(idx)
        self._obstacles_toi = np.append(self._obstacles_toi, t_min)
        self._obstacles_obs.append(obs_and_args_min)
        ball_idx = self._obstacles_toi.argmin()
        self._next_ball_obstacle_collision = (
            self._obstacles_toi[ball_idx],
            ball_idx,
            self._obstacles_obs[ball_idx],
        )

        # Consistency checks
        assert self.balls_initial_time.shape == (self.count, 2)
        assert self.balls_initial_position.shape == (self.count, 2)
        assert self.balls_position.shape == (self.count, 2)
        assert self.balls_velocity.shape == (self.count, 2)
        assert len(self.balls_radius) == self.count
        assert len(self.balls_mass) == self.count
        assert len(self.toi_table) == self.count
        assert self._balls_toi.shape == (self.count,)
        assert len(self._balls_idx) == self.count
        assert self._obstacles_toi.shape == (self.count,)
        assert len(self._obstacles_obs) == self.count

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
            indices = range(self.count)  # i.e. recompute all balls
        elif isinstance(indices, int):
            indices = [indices]  # i.e. recompute only single ball
        else:
            # try to see if iterable, if not will automatically raise TypeError
            indices = iter(indices)  # i.e. recompute a collection of balls

        # check which balls got an assigment to self.balls_position and update their
        # initial time and position
        dt = self.time - self.balls_initial_time
        original_position = self.balls_initial_position + self.balls_velocity * dt
        modified = np.any(self.balls_position != original_position, axis=1)
        for idx in np.flatnonzero(modified).tolist():
            self.balls_initial_time[idx] = self.time
            self.balls_initial_position[idx] = self.balls_position[idx]
        # TODO should we warn the user if the indices of the modified balls is not a
        # subset of the supplied list of indices?

        min_idx = self.count  # = min(indices), used later to update toi_min
        recompute_pairs = set()  # skip indices that we already recomputed
        for idx in indices:
            # update time of impact for ball-ball collisions
            for j in range(idx):
                if (idx, j) not in recompute_pairs:
                    self.toi_table[idx][j] = self._detect_ball_collision(idx, j)
                    recompute_pairs.add((idx, j))

            for i in range(idx + 1, self.count):
                if (i, idx) not in recompute_pairs:
                    self.toi_table[i][idx] = self._detect_ball_collision(i, idx)
                    recompute_pairs.add((i, idx))

            # update time of impact for the next ball-obstacle collision
            t_min, obs_and_args_min = self._detect_next_obstacle(idx)
            self._obstacles_toi[idx] = t_min
            self._obstacles_obs[idx] = obs_and_args_min

            # update minimum index
            min_idx = idx if idx < min_idx else min_idx

        # update toi_min, we skip i = 0 because self.toi_min[0] is always (INF, -1)
        for i in range(min_idx if min_idx > 0 else 1, self.count):
            row = self.toi_table[i]
            toi_idx = row.argmin()
            self._balls_toi[i] = row[toi_idx]
            self._balls_idx[i] = toi_idx

        # update next ball ball collision
        assert self._balls_toi[0] == INF  # first entry always invalid
        assert self._balls_idx[0] == np.int64(-1)
        next_idx = self._balls_toi.argmin()
        self._next_ball_ball_collision = (
            self._balls_toi[next_idx],
            self._balls_idx[next_idx],
            next_idx,
        )

        # update next ball obstacle collision
        ball_idx = self._obstacles_toi.argmin()
        self._next_ball_obstacle_collision = (
            self._obstacles_toi[ball_idx],
            ball_idx,
            self._obstacles_obs[ball_idx],
        )

    def _detect_ball_collision(self, idx1, idx2):
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

    def _detect_next_obstacle(self, idx):
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
            t, args = obs.detect_collision(pos, vel, radius)
            if t < t_min:
                t_min, obs_and_args_min = t, (obs, args)

        return self.time + t_min, obs_and_args_min

    def evolve(
        self, end_time, time_callback=None, ball_callbacks=None, obstacle_callbacks=None
    ):
        """Advance the simulation until the given time is reached.

        This method calls ``bounce_ballball`` and ``bounce_ballobstacle`` repeatedly
        (which one depends on ``next_ball_ball_collision`` and
        ``next_ball_obstacle_collision``) until reaching the given end time.

        Args:
            end_time: Time until which the billiard should be simulated.
            time_callback (optional): Is called every collision with time as argument.
            ball_callbacks (optional): Mapping from ball indices to callback functions.
                The functions must have the signature::

                    def func(time: float,
                        position: np.ndarray(shape=(2,), dtype=np.float64),
                        velocity_before: np.ndarray(shape=(2,), dtype=np.float64),
                        velocity_after: np.ndarray(shape=(2,), dtype=np.float64),
                        ball index: int or obstacle: billiard.obstacle.Obstacle) -> Any

                At every collision the index (or indices) of the colliding ball(s) are
                looked up in the mapping and, if present, the corresponding function(s)
                will be called. The last parameter is either the index of the other ball
                (in a ball-ball collision) or the obstacle instance that was hit (in a
                ball-obstacle collision). The return value of the callback is ignored.
            obstacle_callbacks (optional): Mapping from obstacle instances to callback
                functions. The functions must have the signature::

                    def func(time: float,
                        position: np.ndarray(shape=(2,), dtype=np.float64),
                        velocity_before: np.ndarray(shape=(2,), dtype=np.float64),
                        velocity_after: np.ndarray(shape=(2,), dtype=np.float64),
                        args: tuple, ball index: int) -> Any

                At every ball-obstacle collision the obstacle instance is looked up in
                the mapping and, if present, the corresponding function will be called.
                The ``args`` parameter is the argument tuple for the
                ``resolve_collision`` method of the obstacle. The return value of the
                callback is ignored.

        Returns:
            A tuple containing he number of ball-ball and ball-obstacle collisions.
        """
        if ball_callbacks is not None:
            if not isinstance(ball_callbacks, Mapping):
                raise TypeError(
                    "Argument 'ball_callbacks' must be a mapping, "
                    f"not a {type(ball_callbacks)}"
                )
            if not all(isinstance(i, int) for i in ball_callbacks.keys()):
                raise ValueError("Keys of 'ball_callbacks' must be integers")

        if obstacle_callbacks is not None:
            if not isinstance(obstacle_callbacks, Mapping):
                raise TypeError(
                    "Argument 'obstacle_callbacks' must be a mapping, "
                    f"not a {type(obstacle_callbacks)}"
                )
            if not all(isinstance(obs, Obstacle) for obs in obstacle_callbacks.keys()):
                raise ValueError(
                    "Keys of 'obstacle_callbacks' must be instances of Obstacle"
                )

        ball_collisions, obstacle_collisions = 0, 0
        while self.next_collision[0] <= end_time:
            # decide what kind of collision we are dealing with
            if (
                self._next_ball_ball_collision[0]
                <= self._next_ball_obstacle_collision[0]
            ):
                self.bounce_ball_ball(ball_callbacks)
                ball_collisions += 1
            else:
                self.bounce_ball_obstacle(ball_callbacks, obstacle_callbacks)
                obstacle_collisions += 1

            if time_callback is not None:
                time_callback(self.time)

        # go from time of last collision to the end time
        assert end_time < self.next_collision[0]
        self._move(end_time)

        return (ball_collisions, obstacle_collisions)

    def bounce_ball_ball(self, ball_callbacks=None):
        """Advance to the next ball-ball collision and handle it.

        Args:
            ball_callbacks (optional): Mapping from ball index to a callable.
        """
        t, idx1, idx2 = self._next_ball_ball_collision

        # get the balls that collide
        assert idx1 < idx2, (idx1, idx2)
        assert self._balls_toi[idx2] == t
        assert self._balls_idx[idx2] == idx1

        # advance to the next collision and handle it
        self._move(t)
        self._resolve_ball_collision(idx1, idx2, ball_callbacks)

        # update time of impact for the two balls
        self.toi_table[idx2][idx1] = INF
        assert self._detect_ball_collision(idx1, idx2) == INF

        for j in range(idx1):
            self.toi_table[idx1][j] = self._detect_ball_collision(idx1, j)
            self.toi_table[idx2][j] = self._detect_ball_collision(idx2, j)

        for i in range(idx1 + 1, idx2):
            self.toi_table[i][idx1] = self._detect_ball_collision(i, idx1)
            self.toi_table[idx2][i] = self._detect_ball_collision(idx2, i)

        for i in range(idx2 + 1, self.count):
            self.toi_table[i][idx1] = self._detect_ball_collision(i, idx1)
            self.toi_table[i][idx2] = self._detect_ball_collision(i, idx2)

        # update toi_min, we skip i = 0 because self.toi_min[0] is always (INF, -1)
        for i in range(idx1 if idx1 > 0 else 1, self.count):
            row = self.toi_table[i]
            toi_idx = row.argmin()
            self._balls_toi[i] = row[toi_idx]
            self._balls_idx[i] = toi_idx

        assert self._balls_toi[0] == INF  # first entry always invalid
        assert self._balls_idx[0] == np.int64(-1)
        next_idx = self._balls_toi.argmin()
        self._next_ball_ball_collision = (
            self._balls_toi[next_idx],
            self._balls_idx[next_idx],
            next_idx,
        )

        # update time of impact for the next ball-obstacle collision
        t_min, obs_and_args_min = self._detect_next_obstacle(idx1)
        self._obstacles_toi[idx1] = t_min
        self._obstacles_obs[idx1] = obs_and_args_min
        t_min, obs_and_args_min = self._detect_next_obstacle(idx2)
        self._obstacles_toi[idx2] = t_min
        self._obstacles_obs[idx2] = obs_and_args_min

        ball_idx = self._obstacles_toi.argmin()
        self._next_ball_obstacle_collision = (
            self._obstacles_toi[ball_idx],
            ball_idx,
            self._obstacles_obs[ball_idx],
        )

    def bounce_ball_obstacle(self, ball_callbacks=None, obstacle_callbacks=None):
        """Advance to the next ball-obstacle collision and handle it.

        Args:
            ball_callbacks (optional): Mapping from ball index to a callable.
            obstacle_callbacks (optional): Mapping from obstacle instance to a callable.
        """
        t, idx, obs_and_args = self._next_ball_obstacle_collision
        assert self._obstacles_toi[idx] == t
        assert self._obstacles_obs[idx] == obs_and_args

        # advance to the next collision and handle it
        self._move(t)
        self._resolve_obstacle_collision(
            idx, obs_and_args, ball_callbacks, obstacle_callbacks
        )

        # update time of impact for ball-ball collisions
        for j in range(idx):
            self.toi_table[idx][j] = self._detect_ball_collision(idx, j)

        for i in range(idx + 1, self.count):
            self.toi_table[i][idx] = self._detect_ball_collision(i, idx)

        # update toi_min, we skip i = 0 because self.toi_min[0] is always (INF, -1)
        for i in range(idx if idx > 0 else 1, self.count):
            row = self.toi_table[i]
            toi_idx = row.argmin()
            self._balls_toi[i] = row[toi_idx]
            self._balls_idx[i] = toi_idx

        assert self._balls_toi[0] == INF  # first entry always invalid
        assert self._balls_idx[0] == np.int64(-1)
        next_idx = self._balls_toi.argmin()
        self._next_ball_ball_collision = (
            self._balls_toi[next_idx],
            self._balls_idx[next_idx],
            next_idx,
        )

        # update time of impact for the next ball-obstacle collision
        t_min, obs_and_args_min = self._detect_next_obstacle(idx)
        self._obstacles_toi[idx] = t_min
        self._obstacles_obs[idx] = obs_and_args_min

        ball_idx = self._obstacles_toi.argmin()
        self._next_ball_obstacle_collision = (
            self._obstacles_toi[ball_idx],
            ball_idx,
            self._obstacles_obs[ball_idx],
        )

    def _move(self, time):
        # just update position, no collision handling here
        dt = time - self.balls_initial_time  # note: shape is (num, 2) for broadcasting
        self.balls_position = self.balls_initial_position + self.balls_velocity * dt
        self.time = time

    def _resolve_ball_collision(self, idx1, idx2, ball_callbacks=None):
        """Update the velocities of two colliding balls in the simulation.

        Args:
            idx1: Index of one ball.
            idx2: Index of another ball.
            ball_callbacks (optional): Mapping from ball index to a callable.
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
        if ball_callbacks is not None:
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

    def _resolve_obstacle_collision(
        self, idx, obs_and_args, ball_callbacks=None, obstacle_callbacks=None
    ):
        """Update velocity of a ball colliding with an obstacle.

        Args:
            idx: Index of the colliding ball.
            obs_and_args: The obstacle with which the ball collides and optional
                arguments for ``obstacle.resolve_collision``.
            ball_callbacks (optional): Mapping from ball index to a callable.
            obstacle_callbacks (optional): Mapping from obstacle instance to a callable.
        """
        pos = self.balls_position[idx]
        vel = self.balls_velocity[idx]
        radius = self.balls_radius[idx]

        obs, args = obs_and_args
        new_vel = obs.resolve_collision(pos, vel, radius, *args)

        # call callback here, because updating self.balls_velocity will change vel
        # note: no copy of new_vel needed, because after we assign it we never use it
        # again
        if ball_callbacks is not None and idx in ball_callbacks:
            ball_callbacks[idx](self.time, pos.copy(), vel.copy(), new_vel, obs)
        if obstacle_callbacks is not None and obs in obstacle_callbacks:
            obstacle_callbacks[obs](
                self.time, pos.copy(), vel.copy(), new_vel, args, idx
            )

        # update ball time, position and velocity
        self.balls_initial_time[idx] = self.time
        self.balls_initial_position[idx] = pos
        self.balls_velocity[idx] = new_vel
