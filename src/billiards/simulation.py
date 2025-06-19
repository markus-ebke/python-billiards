"""The simulation module contains the main class for billiard simulations.

Use it like::

    from billiard import Billiard
"""

from collections.abc import Mapping
from math import isinf

import numpy as np

from .obstacles import Obstacle
from .physics import elastic_collision, toi_ball_ball, toi_ball_ball_nocheck, ulp

ZERO = np.float64(0.0)
INF = np.float64("inf")


def _advance_timestamp(time_hi, time_lo, duration):
    """Compute the timestamp (s_hi, s_lo) = (time_hi, time_lo) + duration."""
    # Add duration (float) to the most significant bits of the timestamp
    # r, e = two_sum(time_hi, duration)
    r = time_hi + duration
    t = r - time_hi
    e = (time_hi - (r - t)) + (duration - t)

    # Add the least significant bits of the timestamp to the roundoff error
    # of time_hi + duration from the previous step
    e += time_lo

    # Normalize the double-double number such that ulp(r2) / 2 >= abs(e2)
    # r2, e2 = fast_two_sum(r, e)
    r2 = r + e
    e2 = e - (r2 - r)
    return r2, e2


class Billiard:
    """The Billiard class represents a 2-dimensional billiard table.

    The 2-dimensional world is infinite in all directions and initialized with a list
    of `billiard.obstacle.Obstacle` instances. New billiard balls can be added using the
    `add_ball` method. Use `evolve` to advance the simulation by a specified time
    interval. The updated simulation state can be accessed through the `time`,
    `balls_position`, and `balls_velocity` attributes.

    The properties of the balls can be modified in between simulation runs by updating
    the entries of `balls_position`, `balls_velocity`, `balls_radius`, and `balls_mass`.
    If the position, velocity, or radius of any balls is changed, the corresponding
    entries in the internal time-of-impact table must be recomputed using the
    `recompute_toi` method.

    Note:
        The `balls_initial_time` and `balls_initial_position` attributes store the time
        and position of the last collision for each ball. The actual position at a time
        between the last collision (at `balls_initial_time.max()`) and the next
        collision (at `next_collision[0]`) is calculated using the formula:
        `position = initial position + velocity * (time - initial time)`.

    Attributes:
        balls_initial_position: Numpy.ndarray of 2D position of the balls' centers at
            the initial time indicated in `balls_initial_time`.
        balls_position: Numpy.ndarray of 2D position of the balls' centers at the
            current simulation time. This property is computed from initial time,
            position and velocity.
        balls_velocity: Numpy.ndarray of 2D velocities of the balls.
        balls_radius: List of numbers that represent the radii of the balls.
        balls_mass: List of numbers that represent the masses of the balls.
        obstacles: List of obstacles, i.e. instances of `billiard.obstacle.Obstacle`.
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

        # Ball properties, not that the shape of the initial hi and lo time
        # are (count, 2) for broadcasting with velocity in self._move
        self._balls_initial_time_hi = np.empty(shape=(0, 2), dtype=np.float64)
        self._balls_initial_time_lo = np.empty(shape=(0, 2), dtype=np.float64)
        self.balls_initial_position = np.empty(shape=(0, 2), dtype=np.float64)
        self.balls_radius = []
        self.balls_mass = []

        # State of the balls at a certain time of the simulation
        self._time_hi = np.float64(0.0)
        self._time_lo = np.float64(0.0)
        self.balls_position = np.empty(shape=(0, 2), dtype=np.float64)
        self.balls_velocity = np.empty(shape=(0, 2), dtype=np.float64)

        # Time of impact records for ball-ball collisions, note that the
        # toi-table is triangular.
        self._toi_table_hi = []
        self._toi_table_lo = []

        # The _balls_toi records the minimum time in each row of the
        # toi-table and _balls_idx is the index where in the row the
        # minimum is (or -1 if the ball does not collide). This index is
        # the ball that collides with the ball associated with the row.
        self._balls_toi_hi = np.empty(shape=(0,), dtype=np.float64)
        self._balls_toi_lo = np.empty(shape=(0,), dtype=np.float64)
        self._balls_idx = np.empty(shape=(0,), dtype=np.int64)

        # next_ball_ball_collision is the minimum of _balls_toi and the indices i and j
        # of the colliding balls in the order i > j
        # NOTE: for ball i we only check if there is a collision with balls j < i, so
        # the properties _balls_toi and _balls_idx will NOT include collisions with
        # balls j > i.
        self._next_ball_ball_collision = (INF, ZERO, np.int64(-1), np.int64(0))

        # check obstacles
        self.obstacles = []
        for obs in obstacles:
            if not isinstance(obs, Obstacle):
                msg = "{} must be an obstacle.Obstacle instance"
                raise TypeError(msg.format(obs))

            self.obstacles.append(obs)

        # time of impact records for ball-obstacle collisions
        # toi: time of impact with an obstacle for each ball (size == self.count)
        self._obstacles_toi_hi = np.empty(shape=(0,), dtype=np.float64)
        self._obstacles_toi_lo = np.empty(shape=(0,), dtype=np.float64)
        self._obstacles_and_args = []  # colliding obstacle and args for each ball

        # next_ball_obstacle_collision is the minimum of _obstacles_toi, the ball index
        # and the obstacle along with optional arguments for the collide method
        self._next_ball_obstacle_collision = (INF, ZERO, np.int64(-1), None)

    @property
    def time(self):
        """Current time of the simulation."""
        return float(self._time_hi)

    @property
    def count(self):
        """Number of balls in the billiard."""
        return self.balls_position.shape[0]

    @property
    def balls_initial_time(self):
        """Initial time for each ball when it is located at balls_initial_position."""
        return self._balls_initial_time_hi[:, 0]

    @property
    def toi_table(self):
        """Time-of-impact for each ball-ball pair as a lower-triangular table."""
        return self._toi_table_hi

    @property
    def ball_ball_collisions(self):
        """Time of the next ball-ball collision for each ball."""
        balls_toi_hi = self._balls_toi_hi.copy()
        balls_toi_lo = self._balls_toi_lo.copy()
        balls_idx = self._balls_idx.copy()

        # Note that self._balls_toi[i] is only the toi of ball i with any ball j < i.
        # To include also collision times with the balls j > i we need to check the
        # entries self._toi_table[j][i] for j > i.
        for j in range(self.count):
            row_j_hi, row_j_lo = self._toi_table_hi[j], self._toi_table_lo[j]
            for i in range(len(row_j_hi)):
                toi_j_i = row_j_hi[i], row_j_lo[i]
                if toi_j_i < (balls_toi_hi[i], balls_toi_lo[i]):
                    balls_toi_hi[i] = toi_j_i[0]
                    balls_toi_lo[i] = toi_j_i[1]
                    balls_idx[i] = j

        return balls_toi_hi, balls_idx

    @property
    def ball_obstacle_collisions(self):
        """Time of the next ball-obstacle collision for each ball."""
        obs = [
            (obs_args[0] if obs_args is not None else None)
            for obs_args in self._obstacles_and_args
        ]
        return self._obstacles_toi_hi, obs

    @property
    def next_ball_ball_collision(self):
        """Next ball-ball collision as a (time, ball index, ball index)-triplet."""
        t_hi, t_lo, i, j = self._next_ball_ball_collision
        return (float(t_hi), int(i), int(j))

    @property
    def next_ball_obstacle_collision(self):
        """Next ball-obstacle collision as (time, ball index, (obstacle, args))."""
        t_hi, t_lo, i, obs_args = self._next_ball_obstacle_collision
        return (float(t_hi), int(i), obs_args)

    @property
    def next_collision(self):
        """Next collision as a (time, ball index, ball index or obstacle)-triplet."""
        if self._next_ball_ball_collision[:2] <= self._next_ball_obstacle_collision[:2]:
            return self.next_ball_ball_collision
        else:
            return self.next_ball_obstacle_collision

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
        self._balls_initial_time_hi = np.append(
            self._balls_initial_time_hi, [(self._time_hi, self._time_hi)], axis=0
        )
        self._balls_initial_time_lo = np.append(
            self._balls_initial_time_lo, [(self._time_lo, self._time_lo)], axis=0
        )
        self.balls_initial_position = np.append(
            self.balls_initial_position, [pos], axis=0
        )
        self.balls_velocity = np.append(self.balls_velocity, [vel], axis=0)
        self.balls_radius.append(float(radius))
        self.balls_mass.append(float(mass))

        # ball position is same as initial position
        self.balls_position = np.append(self.balls_position, [pos], axis=0)
        idx = self.count - 1  # last added ball is at the end

        # Calculate next time of impact
        row_list = [self._detect_ball_collision(j, idx) for j in range(idx)]
        row_hi = np.asarray([t_tl[0] for t_tl in row_list], dtype=np.float64)
        self._toi_table_hi.append(row_hi)
        row_lo = np.asarray([t_tl[1] for t_tl in row_list], dtype=np.float64)
        self._toi_table_lo.append(row_lo)

        if row_hi.size > 0:
            toi_idx = row_hi.argmin()
            self._balls_toi_hi = np.append(self._balls_toi_hi, row_hi[toi_idx])
            self._balls_toi_lo = np.append(self._balls_toi_lo, row_lo[toi_idx])
            self._balls_idx = np.append(self._balls_idx, toi_idx)
        else:
            # Only one ball in the scene => no collisions with other balls
            self._balls_toi_hi = np.append(self._balls_toi_hi, INF)
            self._balls_toi_lo = np.append(self._balls_toi_lo, ZERO)
            self._balls_idx = np.append(self._balls_idx, -1)

        next_idx = self._balls_toi_hi.argmin()
        self._next_ball_ball_collision = (
            self._balls_toi_hi[next_idx],
            self._balls_toi_lo[next_idx],
            self._balls_idx[next_idx],
            next_idx,
        )  # note that first ball index must be lower than second index

        # Calculate time of impact for obstacles
        (toi_hi, toi_lo), obs_and_args_min = self._detect_next_obstacle(idx)
        self._obstacles_toi_hi = np.append(self._obstacles_toi_hi, toi_hi)
        self._obstacles_toi_lo = np.append(self._obstacles_toi_lo, toi_lo)
        self._obstacles_and_args.append(obs_and_args_min)
        ball_idx = self._obstacles_toi_hi.argmin()
        self._next_ball_obstacle_collision = (
            self._obstacles_toi_hi[ball_idx],
            self._obstacles_toi_lo[ball_idx],
            ball_idx,
            self._obstacles_and_args[ball_idx],
        )

        # Consistency checks
        assert self._balls_initial_time_hi.shape == (self.count, 2)
        assert self._balls_initial_time_lo.shape == (self.count, 2)
        assert self.balls_initial_position.shape == (self.count, 2)
        assert self.balls_position.shape == (self.count, 2)
        assert self.balls_velocity.shape == (self.count, 2)
        assert len(self.balls_radius) == self.count
        assert len(self.balls_mass) == self.count
        assert len(self._toi_table_hi) == self.count
        assert len(self._toi_table_lo) == self.count
        assert self._balls_toi_hi.shape == (self.count,)
        assert self._balls_toi_lo.shape == (self.count,)
        assert len(self._balls_idx) == self.count
        assert self._obstacles_toi_hi.shape == (self.count,)
        assert self._obstacles_toi_lo.shape == (self.count,)
        assert len(self._obstacles_and_args) == self.count

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

        # compute original ball positions at the current time
        init_hi, init_lo = self._balls_initial_time_hi, self._balls_initial_time_lo
        dt = (self._time_hi - init_hi) + (self._time_lo - init_lo)
        original_position = self.balls_initial_position + self.balls_velocity * dt

        # check which balls got an assigment to self.balls_position and update their
        # initial time and position
        modified = np.any(self.balls_position != original_position, axis=1)
        for idx in np.flatnonzero(modified).tolist():
            self._balls_initial_time_hi[idx] = self._time_hi
            self._balls_initial_time_lo[idx] = self._time_lo
            self.balls_initial_position[idx] = self.balls_position[idx]
        # TODO should we warn the user if the indices of the modified balls is not a
        # subset of the supplied list of indices?

        min_idx = self.count  # = min(indices), used later to update toi_min
        recompute_pairs = set()  # skip indices that we already recomputed
        for idx in indices:
            # update time of impact for ball-ball collisions
            for j in range(idx):
                if (idx, j) not in recompute_pairs:
                    toi_hi, toi_lo = self._detect_ball_collision(idx, j)
                    self._toi_table_hi[idx][j] = toi_hi
                    self._toi_table_lo[idx][j] = toi_lo
                    recompute_pairs.add((idx, j))

            for i in range(idx + 1, self.count):
                if (i, idx) not in recompute_pairs:
                    toi_hi, toi_lo = self._detect_ball_collision(i, idx)
                    self._toi_table_hi[i][idx] = toi_hi
                    self._toi_table_lo[i][idx] = toi_lo
                    recompute_pairs.add((i, idx))

            # update time of impact for the next ball-obstacle collision
            (toi_hi, toi_lo), obs_and_args_min = self._detect_next_obstacle(idx)
            self._obstacles_toi_hi[idx] = toi_hi
            self._obstacles_toi_lo[idx] = toi_lo
            self._obstacles_and_args[idx] = obs_and_args_min

            # update minimum index
            min_idx = idx if idx < min_idx else min_idx

        # update toi_min, we skip i = 0 because self.toi_min[0] is always (INF, -1)
        for i in range(min_idx if min_idx > 0 else 1, self.count):
            row_hi = self._toi_table_hi[i]
            toi_idx = row_hi.argmin()
            self._balls_toi_hi[i] = row_hi[toi_idx]
            self._balls_toi_lo[i] = self._toi_table_lo[i][toi_idx]
            self._balls_idx[i] = toi_idx

        # update next ball ball collision
        assert self._balls_toi_hi[0] == INF  # first entry always invalid
        assert self._balls_idx[0] == np.int64(-1)
        next_idx = self._balls_toi_hi.argmin()
        self._next_ball_ball_collision = (
            self._balls_toi_hi[next_idx],
            self._balls_toi_lo[next_idx],
            self._balls_idx[next_idx],
            next_idx,
        )

        # update next ball obstacle collision
        ball_idx = self._obstacles_toi_hi.argmin()
        self._next_ball_obstacle_collision = (
            self._obstacles_toi_hi[ball_idx],
            self._obstacles_toi_lo[ball_idx],
            ball_idx,
            self._obstacles_and_args[ball_idx],
        )

    def _detect_ball_collision(self, idx1, idx2):
        """Calculate time of impact of two balls in the simulation.

        Args:
            idx1: Index of one ball.
            idx2: Index of another ball.

        Returns:
            Time of impact between the two balls. This time is returned in
            double-double precision!
        """
        p1 = self.balls_position[idx1]
        v1 = self.balls_velocity[idx1]
        r1 = self.balls_radius[idx1]

        p2 = self.balls_position[idx2]
        v2 = self.balls_velocity[idx2]
        r2 = self.balls_radius[idx2]

        toi = toi_ball_ball(p1, v1, r1, p2, v2, r2)
        if isinf(toi):
            return (INF, ZERO)
        else:
            return _advance_timestamp(self._time_hi, self._time_lo, toi)

    def _detect_next_obstacle(self, idx):
        """Find the closest colliding obstacle for the given ball.

        Args:
            idx: Index of ball.

        Returns:
            tuple: (time, (obstacle, args))-pair of the next collision or (INF, None) if
            ball will not impact any obstacle. Note that the time is returned in
            double-double precision!
        """
        pos = self.balls_position[idx]
        vel = self.balls_velocity[idx]
        radius = self.balls_radius[idx]

        toi_min, obs_and_args_min = INF, None
        for obs in self.obstacles:
            toi, args = obs.detect_collision(pos, vel, radius)
            if toi < toi_min:
                toi_min, obs_and_args_min = toi, (obs, args)

        if isinf(toi_min):
            return ((INF, ZERO), None)
        else:
            time = _advance_timestamp(self._time_hi, self._time_lo, toi_min)
            return (time, obs_and_args_min)

    def evolve(
        self,
        duration=None,
        until=None,
        *,
        time_callback=None,
        ball_callbacks=None,
        obstacle_callbacks=None,
    ):
        """Evolve the simulation for a given time interval or until a given timestamp.

        Either `duration` or `until` must be provided, but not both. Callback functions
        that will be called at every collision can only be given as keyword arguments.

        This method calls ``bounce_ballball`` and ``bounce_ballobstacle`` repeatedly
        (which one depends on ``next_ball_ball_collision`` and
        ``next_ball_obstacle_collision``) until the time interval `duration` has passed
        or the simulation time reached `until`.

        Note:
            Internally, all timestamps are recorded with double-double precision, i.e.
            as pairs ``(time_hi, time_lo)`` with ``abs(time_lo) <= ulp(time_hi) / 2``.
            The ``time_lo`` part tracks roundoff errors that accumulate when the
            simulation time is incremented between collision events. This ensures that
            we can recover (with high accuracy) the time intervals between collisions
            from the double-double timestamps, even at large simulation times.

        Examples:
            Usage of the `duration` and `until` parameters:

            >>> from billiards import Billiard
            >>> bld = Billiard()
            >>> bld.time
            0.0
            >>> _ = bld.evolve(1.0)  # simulate for 1 time unit
            >>> bld.time
            1.0
            >>> _ = bld.evolve(until=10.0)  # simulate for another 9 time units
            >>> bld.time
            10.0
            >>> _ = bld.evolve(duration=0.1)  # a duration, declared explicitly
            >>> bld.time
            10.1
            >>> _ = bld.evolve(None, 11)  # implicit: duration=None, until=11.0
            >>> bld.time
            11.0

        Args:
            duration: Length of the time interval to simulate. Must be non-negative if
                given.
            until: Evolve until the simulation reaches the given time, must be greater
                or equal to ``self.time`` if given.
            time_callback (optional): Is called at every collision and must have the
                signature::

                    def func(time: float, interval: float) -> Any

                where ``time`` is the timestamp of the collision and ``interval`` is the
                time since the last collision. On the first call the interval is the
                time since the start of the simulation.
            ball_callbacks (optional): Mapping from ball indices to callback functions.
                The functions must have the signature::

                    def func(time: float,
                        interval: float,
                        position: np.ndarray(shape=(2,), dtype=np.float64),
                        velocity_before: np.ndarray(shape=(2,), dtype=np.float64),
                        velocity_after: np.ndarray(shape=(2,), dtype=np.float64),
                        ball index: int or obstacle: billiard.obstacle.Obstacle) -> Any

                At every collision, the functions associated with the indices of the
                colliding balls are called. The last parameter is either the index of
                the other ball (in the case of a ball-ball collision) or the obstacle
                instance that was hit (for a ball-obstacle collision).
                The return value of the callback is ignored.
            obstacle_callbacks (optional): Mapping from obstacle instances to callback
                functions. The functions must have the signature::

                    def func(time: float,
                        position: np.ndarray(shape=(2,), dtype=np.float64),
                        velocity_before: np.ndarray(shape=(2,), dtype=np.float64),
                        velocity_after: np.ndarray(shape=(2,), dtype=np.float64),
                        ball index: int,
                        args: tuple) -> Any

                At every ball-obstacle collision, the function associated with the hit
                obstacle is called. The ``args`` parameter is the argument tuple for
                the ``resolve_collision`` method of the obstacle.
                The return value of the callback is ignored.

        Returns:
            A tuple containing the number of ball-ball and ball-obstacle collisions.

        Raises:
            ValueError: If `duration` or `until` are invalid of if the keys for the ball
                callbacks are not integers or if the keys for the obstacle callbacks are
                not `obstacle.Obstacle` instances.
            TypeError: If the ball and obstacle callbacks are not mappings.
        """
        # check "duration" and "until"
        if duration is not None:
            if until is not None:
                raise ValueError(
                    f"either 'duration' or 'until' must be given, but not both "
                    f"({duration=}, {until=})"
                )
            elif duration < 0:
                raise ValueError(f"cannot evolve backwards in time ({duration=})")
            elif isinf(duration):
                raise ValueError(f"cannot evolve for infinite time ({duration=})")

            # the 'until' timestamp that the user intended
            until_user = _advance_timestamp(self._time_hi, self._time_lo, duration)

            # in practice we will overshoot a little so that all collisions get
            # handled that are plausibly within the duration
            until_plausible = _advance_timestamp(
                until_user[0], until_user[1], ulp(duration) / 2
            )
        else:
            if until is None:
                raise ValueError("either 'duration' or 'until' must be given")
            elif until < self.time:
                raise ValueError(f"{until=} cannot be smaller than {self.time=}")
            elif isinf(until):
                raise ValueError(f"cannot evolve for infinite time ({until=})")

            # the 'until' timestamp that the user intended
            until_user = (np.float64(until), 0.0)

            # in practice we will overshoot a little so that all collisions at
            # at time_hi == until get handled, including the collisions with
            # time_lo > 0.0 (because they are plausibly within the time frame
            # that the user intended)
            until_plausible = (np.float64(until), np.float64(ulp(until) / 2))

        # check ball callbacks
        if ball_callbacks is not None:
            if not isinstance(ball_callbacks, Mapping):
                raise TypeError(
                    "Argument 'ball_callbacks' must be a mapping, "
                    f"not a {type(ball_callbacks)}"
                )
            if not all(isinstance(i, int) for i in ball_callbacks.keys()):
                raise ValueError("Keys of 'ball_callbacks' must be integers")

        # check obstacle callbacks
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

        # simulate
        ball_collisions, obstacle_collisions = 0, 0
        while True:
            bb = self._next_ball_ball_collision[:2]
            bo = self._next_ball_obstacle_collision[:2]
            # if bb > end_time and bo > end_time:
            #    break

            if bb <= bo:
                if bb > until_plausible:
                    break
                interval = self.bounce_ball_ball(ball_callbacks)
                ball_collisions += 1
            else:
                if bo > until_plausible:
                    break
                interval = self.bounce_ball_obstacle(ball_callbacks, obstacle_callbacks)
                obstacle_collisions += 1

            # call time callback after handling the collision
            if time_callback is not None:
                time_callback(self.time, interval)

        # go to the user intended 'until' timestamp
        assert until_plausible < self._next_ball_ball_collision[:2]
        assert until_plausible < self._next_ball_obstacle_collision[:2]
        self._move(until_user[0], until_user[1])

        return (ball_collisions, obstacle_collisions)

    def bounce_ball_ball(self, ball_callbacks=None):
        """Advance to the next ball-ball collision and handle it.

        Args:
            ball_callbacks (optional): Mapping from ball index to a callable.

        Returns:
            The time interval that the simulation advanced to get to the next
            ball-ball collision.
        """
        toi_hi, toi_lo, idx1, idx2 = self._next_ball_ball_collision

        # get the balls that collide
        assert idx1 < idx2, (idx1, idx2)
        assert self._balls_toi_hi[idx2] == toi_hi
        assert self._balls_toi_lo[idx2] == toi_lo
        assert self._balls_idx[idx2] == idx1

        # advance to the next collision and handle it
        interval = self._move(toi_hi, toi_lo)
        self._resolve_ball_collision(idx1, idx2, ball_callbacks)

        # update time of impact for the two balls
        self._toi_table_hi[idx2][idx1] = INF
        self._toi_table_lo[idx2][idx1] = ZERO
        assert self._detect_ball_collision(idx1, idx2)[0] == INF

        for j in range(idx1):
            toi_hi, toi_lo = self._detect_ball_collision(idx1, j)
            self._toi_table_hi[idx1][j] = toi_hi
            self._toi_table_lo[idx1][j] = toi_lo

            toi_hi, toi_lo = self._detect_ball_collision(idx2, j)
            self._toi_table_hi[idx2][j] = toi_hi
            self._toi_table_lo[idx2][j] = toi_lo

        for i in range(idx1 + 1, idx2):
            toi_hi, toi_lo = self._detect_ball_collision(i, idx1)
            self._toi_table_hi[i][idx1] = toi_hi
            self._toi_table_lo[i][idx1] = toi_lo

            toi_hi, toi_lo = self._detect_ball_collision(idx2, i)
            self._toi_table_hi[idx2][i] = toi_hi
            self._toi_table_lo[idx2][i] = toi_lo

        for i in range(idx2 + 1, self.count):
            toi_hi, toi_lo = self._detect_ball_collision(i, idx1)
            self._toi_table_hi[i][idx1] = toi_hi
            self._toi_table_lo[i][idx1] = toi_lo

            toi_hi, toi_lo = self._detect_ball_collision(i, idx2)
            self._toi_table_hi[i][idx2] = toi_hi
            self._toi_table_lo[i][idx2] = toi_lo

        # update toi_min, we skip i = 0 because self.toi_min[0] is always (INF, -1)
        for i in range(idx1 if idx1 > 0 else 1, self.count):
            row_hi = self._toi_table_hi[i]
            toi_idx = row_hi.argmin()
            self._balls_toi_hi[i] = row_hi[toi_idx]
            self._balls_toi_lo[i] = self._toi_table_lo[i][toi_idx]
            self._balls_idx[i] = toi_idx

        assert self._balls_toi_hi[0] == INF  # first entry always invalid
        assert self._balls_idx[0] == np.int64(-1)
        next_idx = self._balls_toi_hi.argmin()
        self._next_ball_ball_collision = (
            self._balls_toi_hi[next_idx],
            self._balls_toi_lo[next_idx],
            self._balls_idx[next_idx],
            next_idx,
        )

        # update time of impact for the next ball-obstacle collision
        (toi_hi, toi_lo), obs_and_args_min = self._detect_next_obstacle(idx1)
        self._obstacles_toi_hi[idx1] = toi_hi
        self._obstacles_toi_lo[idx1] = toi_lo
        self._obstacles_and_args[idx1] = obs_and_args_min

        (toi_hi, toi_lo), obs_and_args_min = self._detect_next_obstacle(idx2)
        self._obstacles_toi_hi[idx2] = toi_hi
        self._obstacles_toi_lo[idx2] = toi_lo
        self._obstacles_and_args[idx2] = obs_and_args_min

        ball_idx = self._obstacles_toi_hi.argmin()
        self._next_ball_obstacle_collision = (
            self._obstacles_toi_hi[ball_idx],
            self._obstacles_toi_lo[ball_idx],
            ball_idx,
            self._obstacles_and_args[ball_idx],
        )

        return interval

    def bounce_ball_obstacle(self, ball_callbacks=None, obstacle_callbacks=None):
        """Advance to the next ball-obstacle collision and handle it.

        Args:
            ball_callbacks (optional): Mapping from ball index to a callable.
            obstacle_callbacks (optional): Mapping from obstacle instance to a callable.

        Returns:
            The time interval that the simulation advanced to get to the next
            ball-obstacle collision.
        """
        toi_hi, toi_lo, idx, obs_and_args = self._next_ball_obstacle_collision
        assert self._obstacles_toi_hi[idx] == toi_hi
        assert self._obstacles_toi_lo[idx] == toi_lo
        assert self._obstacles_and_args[idx] == obs_and_args

        # advance to the next collision and handle it
        interval = self._move(toi_hi, toi_lo)
        self._resolve_obstacle_collision(
            idx, obs_and_args, ball_callbacks, obstacle_callbacks
        )

        # update time of impact for ball-ball collisions
        for j in range(idx):
            toi_hi, toi_lo = self._detect_ball_collision(idx, j)
            self._toi_table_hi[idx][j] = toi_hi
            self._toi_table_lo[idx][j] = toi_lo

        for i in range(idx + 1, self.count):
            toi_hi, toi_lo = self._detect_ball_collision(i, idx)
            self._toi_table_hi[i][idx] = toi_hi
            self._toi_table_lo[i][idx] = toi_lo

        # update toi_min, we skip i = 0 because self.toi_min[0] is always (INF, -1)
        for i in range(idx if idx > 0 else 1, self.count):
            row_hi = self._toi_table_hi[i]
            toi_idx = row_hi.argmin()
            self._balls_toi_hi[i] = row_hi[toi_idx]
            self._balls_toi_lo[i] = self._toi_table_lo[i][toi_idx]
            self._balls_idx[i] = toi_idx

        assert self._balls_toi_hi[0] == INF  # first entry always invalid
        assert self._balls_idx[0] == np.int64(-1)
        next_idx = self._balls_toi_hi.argmin()
        self._next_ball_ball_collision = (
            self._balls_toi_hi[next_idx],
            self._balls_toi_lo[next_idx],
            self._balls_idx[next_idx],
            next_idx,
        )

        # update time of impact for the next ball-obstacle collision
        (toi_hi, toi_lo), obs_and_args_min = self._detect_next_obstacle(idx)
        self._obstacles_toi_hi[idx] = toi_hi
        self._obstacles_toi_lo[idx] = toi_lo
        self._obstacles_and_args[idx] = obs_and_args_min

        ball_idx = self._obstacles_toi_hi.argmin()
        self._next_ball_obstacle_collision = (
            self._obstacles_toi_hi[ball_idx],
            self._obstacles_toi_lo[ball_idx],
            ball_idx,
            self._obstacles_and_args[ball_idx],
        )

        return interval

    def _move(self, time_hi, time_lo):
        """Just update self.balls_position and self.time, no collision handling here."""
        # Compute dt: duration from initial time to (time_hi, time_lo) for each ball.
        init_hi, init_lo = self._balls_initial_time_hi, self._balls_initial_time_lo
        dt = (time_hi - init_hi) + (time_lo - init_lo)
        # Note that the float subtraction x - y is exact (no rounding error), if
        # x/2 <= y <= 2*x. So dt is exact if time_hi <= 2 * initial_time_hi,
        # or equivalently, if (original duration) <= initial_time_hi. This may not be
        # true near the start of the simulation! The maximal error from this "wrong"
        # computation is ulp(time_hi) and since ulp(time_hi) = ulp(dt) (because
        # initial_time_hi < 2 * time_hi) this error only affects the least significant
        # bit of dt. This is acceptable.
        # Note: A proper subtraction of double-double numbers involves 8 arithmetic
        # operations.

        # update positions, note: shape of dt array is (num, 2) for broadcasting
        self.balls_position = self.balls_initial_position + self.balls_velocity * dt

        # update time
        interval = (time_hi - self._time_hi) + (time_lo - self._time_lo)
        self._time_hi = time_hi
        self._time_lo = time_lo

        return interval

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

        # resolve collision
        r1, r2 = self.balls_radius[idx1], self.balls_radius[idx2]
        dt = toi_ball_ball_nocheck(p1, v1, r1, p2, v2, r2)
        if not isinf(dt):
            p1_new = p1 + dt * v1
            p2_new = p2 + dt * v2
        v1_new, v2_new = elastic_collision(p1_new, v1, m1, p2_new, v2, m2)

        # call callback here, because updating self.balls_velocity will change v1 and v2
        if ball_callbacks is not None:
            if idx1 in ball_callbacks:
                interval = self._time_hi - self._balls_initial_time_hi[idx1, 0]
                interval += self._time_lo - self._balls_initial_time_lo[idx1, 0]
                ball_callbacks[idx1](
                    self.time, interval, p1_new.copy(), v1.copy(), v1_new.copy(), idx2
                )
            if idx2 in ball_callbacks:
                interval = self._time_hi - self._balls_initial_time_hi[idx2, 0]
                interval += self._time_lo - self._balls_initial_time_lo[idx2, 0]
                ball_callbacks[idx2](
                    self.time, interval, p2_new.copy(), v2.copy(), v2_new.copy(), idx1
                )

        # update ball time, position and velocity
        self._balls_initial_time_hi[idx1] = self._time_hi
        self._balls_initial_time_lo[idx1] = self._time_lo
        self.balls_initial_position[idx1] = p1_new
        self.balls_position[idx1] = p1_new
        self.balls_velocity[idx1] = v1_new

        self._balls_initial_time_hi[idx2] = self._time_hi
        self._balls_initial_time_lo[idx2] = self._time_lo
        self.balls_initial_position[idx2] = p2_new
        self.balls_position[idx2] = p2_new
        self.balls_velocity[idx2] = v2_new

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

        # let the obstacle resolve the collision
        obs, args = obs_and_args
        pos_new, vel_new = obs.resolve_collision(pos, vel, radius, *args)

        # call callback here, because updating self.balls_velocity will change vel
        if ball_callbacks is not None and idx in ball_callbacks:
            interval = self._time_hi - self._balls_initial_time_hi[idx, 0]
            interval += self._time_lo - self._balls_initial_time_lo[idx, 0]
            ball_callbacks[idx](
                self.time, interval, pos_new.copy(), vel.copy(), vel_new.copy(), obs
            )
        if obstacle_callbacks is not None and obs in obstacle_callbacks:
            obstacle_callbacks[obs](
                self.time, pos_new.copy(), vel.copy(), vel_new.copy(), idx, args
            )

        # update ball time, position and velocity
        self._balls_initial_time_hi[idx] = self._time_hi
        self._balls_initial_time_lo[idx] = self._time_lo
        self.balls_initial_position[idx] = pos_new
        self.balls_position[idx] = pos_new
        self.balls_velocity[idx] = vel_new
