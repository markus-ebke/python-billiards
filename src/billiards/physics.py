"""This module contains functions for collision detection and handling."""

from math import sqrt

try:
    from math import ulp
except ImportError:  # Python < 3.9
    from math import frexp

    def ulp(x):
        """Return the value of the least significant bit of the float x."""
        # Unit in the Last Place for 64-bit (double precision) floating point numbers
        return 2 ** (frexp(x)[1] - 53)


import numpy as np

INF = float("inf")


def toi_ball_ball(pos1, vel1, radius1, pos2, vel2, radius2, pos_unreliable_ulps=1):
    """Calculate the time of impact of two moving balls.

    If the balls are not colliding in the present or future (i.e., at a
    time >= 0.0), the returned time is infinite. Already overlapping
    balls are not considered to be colliding (because the collision has
    already occurred).

    However, due to floating-point precision issues, we may incorrectly
    conclude that two balls are overlapping when in fact they collide
    slightly in the future. I.e., if the positions were given with
    infinite precision the collision time would be >= 0.0. But due to
    the finite precision of floating point numbers, the computed
    distance of `pos1` and `pos2` may be less than the sum of `radius1`
    and `radius2` by a few ULPs (Units in the Last Place). Furthermore,
    previous calculations of the positions can introduce rounding errors
    or cancel significant digits so that multiple ULPs of the positions
    will be incorrect.

    The `pos_unreliable_ulps` parameter allows to account for these
    precision errors. By setting it to the number of least significant
    bits in the position vectors that may not be accurate, a collision
    that would be missed due to insufficient precision is now properly
    detected. Note that in such a case the returned time is negative!

    Notes:
        Two balls are colliding at a present or future time if

        - at least one of them is not a point particle,
        - they move towards each other (the dot product of
          ``pos1 - pos2`` and ``vel1 - vel2`` is >= 0),
        - they don't overlap (the distance between ``pos1`` and ``pos2``
          is larger than ``radius1 + radius2`` plus some tolerance to
          account for inaccuracies of the position vectors),
        - they don't miss and don't just touch (determined via the
          discriminant of a quadratic equation).

        If any of the above checks fails, we return infinity. Otherwise
        we compute the toi as the smaller of the two solutions to a
        quadratic equation.

    Args:
        pos1: Center of the first ball.
        vel1: Velocity of the first ball.
        radius1: Radius of the first ball.
        pos2: Center of the second ball.
        vel2: Velocity of the second ball.
        radius2: Radius of the second ball.
        pos_unreliable_ulps (optional): The number of least significant
            bits in the position vectors `pos1` and `pos2` that may not
            be accurate. The worst case error is propagated through the
            computation. If the computed overlap (= distance minus sum
            of radii) is larger than the propagated error, we can prove
            that there is no collision in the present or future and
            return infinity. Otherwise, we continue the computation and
            may return a negative time.
            To disable error propagation, use ``float("-inf")``.
            Default: 1 (i.e., only the last bit may not be accurate).

    Returns:
        Time of impact, is infinite if there is no collision at the
        present or a future time.
    """
    if radius1 == 0 and radius2 == 0:
        return INF  # point particles cannot collide with each other

    # Compute the relative position and velocity between the two balls
    dpos = np.subtract(pos1, pos2)
    dvel = np.subtract(vel1, vel2)

    # Compute the scalar products <p, v>, <v, v> = |v|^2 and <p, p> = |p|^2
    pos_dot_vel = dpos.dot(dvel)
    if pos_dot_vel >= 0:
        return INF  # no collision if the balls are not moving towards each other

    speed_sqrd = dvel.dot(dvel)  # note: speed != 0 because pos_dot_vel != 0
    dist_sqrd = dpos.dot(dpos)

    # The distance between centers of the two balls is |p + t v|, where
    # |p + t v|^2 = a t^2 + 2b t + c, with a := <v, v>, b := <p, v>, c := <p, p>
    # To compute the time of impact t we need to solve |p + t v| == radius1 + radius2.
    # By squaring both sides we see that t is a solution of the quadratic equation
    # a t^2 + 2 b t + c - (radius1 + radius2)^2 == 0.
    # Depending on the value of the discriminant delta = b'^2 - 4 a c', we can have:
    # - no solution (when the balls miss),
    # - one solution (when the balls slide past each other, this is not a collision),
    # - two solutions (and the smaller one is the time we want).
    # Here: b' = 2 <p, v>, c' = <p, p> - (radius1 + radius2)^2 and the solutions are
    # t12 = (-b' -/+ sqrt(delta)) / (2 a), where a = <v, v>.
    c_minus_r2 = dist_sqrd - (radius1 + radius2) ** 2
    delta_over_4 = pos_dot_vel * pos_dot_vel - speed_sqrd * c_minus_r2
    if delta_over_4 <= 0:
        return INF  # no collision if the balls miss or slide past each other

    # The sign of c - (radius1 + radius2)^2 determines if the balls overlap:
    # c_minus_r2 < 0: the balls overlap,
    # c_minus_r2 == 0: the balls touch,
    # c_minus_r2 > 0: there is a gap separating the balls
    # In practice, we don't want to check c_minus_r2 against zero because the least
    # significant bits of the position vectors may be inaccurate. Instead we propagate
    # the uncertainty of position 2**(pos_unreliable_ulps - 1) * ulp(pos[i]) and check
    # against the error of dist_sqrd. To propagate the absolute errors, we use
    # (x + x_err) + (y + y_err) = (x + y) + (x_err + y_err)
    # (x + x_err) - (y + y_err) = (x - y) + (x_err + y_err)
    # (x + x_err) * (y + y_err) = (x * y) + (|x| * y_err + |y| * x_err) + (negligible)
    # (x + x_err) ** n = x ** n + n * |x| * x_err + (negligible), n > 0
    # Finally, we multiply the error by (1 + eps) for some small eps to account for
    # rounding errors of the operations +, - and *.
    # I chose eps = 0.0001 / 2 to avoid a line break. In theory, a much smaller value
    # should also work.
    dpos_x_err = 2 ** (pos_unreliable_ulps - 1) * (ulp(pos1[0]) + ulp(pos2[0]))
    dpos_y_err = 2 ** (pos_unreliable_ulps - 1) * (ulp(pos1[1]) + ulp(pos2[1]))
    dist_sqrd_err = 2.0001 * (abs(dpos[0]) * dpos_x_err + abs(dpos[1]) * dpos_y_err)

    # Return infinity if we can prove that the balls will not collide in
    # the present or the future
    if c_minus_r2 < -dist_sqrd_err:  # equivalent: toi + toi_err < 0
        return INF

    # Write out the solutions t12 = (-b -+ sqrt(delta_over_4)) / a. Since t1 < t2
    # the time of impact is t1 and we don't actually need to compute t2.
    # t1 = (-pos_dot_vel - sqrt(delta_over_4)) / speed_sqrd
    # t2 = (-pos_dot_vel + sqrt(delta_over_4)) / speed_sqrd

    # A better way to compute t1 with minimal rounding error goes as follows:
    # First, compute t2 which is not affected by cancellation of significant digits
    # (because -b > 0 and sqrt(...) > 0). Then use that from
    # a (t - t1) (t - t2) = a t^2 - a (t1 + t2) t + a t1 t2 == a t^2 + 2b t + c
    # we can derive t1 = c / (a t2) when t2 is not zero.
    # Note that pos_dot_vel != sqrt(delta_over_4) because pos_dot_vel < 0
    return c_minus_r2 / (-pos_dot_vel + sqrt(delta_over_4))


def toi_ball_point(pos, vel, radius, point, pos_unreliable_ulps=1):
    """Calculate the time of impact of a moving ball and a static point.

    This function is similar to (but slightly faster than)
    ``toi_ball_ball(pos, vel, radius, point, (0, 0), 0, pos_unreliable_ulps)``
    except that here we assume that all digits of `point` are accurate.
    See the documentation of `toi_ball_ball` for more information.

    Args:
        pos: Center of the ball.
        vel: Velocity of the ball.
        radius: Radius of the ball.
        point: Position of the point.
        pos_unreliable_ulps (optional): The number of least significant
            bits in the position vector `pos` that may not be accurate.
            Default: 1 (i.e., only the last bit may not be accurate).

    Returns:
        Time of impact, is infinite if there is no collision at the
        present or a future time.
    """
    if radius == 0:
        return INF  # point particles cannot collide with a point

    # Compute the relative position between the ball and the point
    dpos = np.subtract(pos, point)
    vel = np.asarray(vel)

    # Compute the scalar products <p, v>, <v, v> = |v|^2 and <p, p> = |p|^2
    pos_dot_vel = dpos.dot(vel)
    if pos_dot_vel >= 0:
        return INF  # no collision if the ball is not moving towards the point

    speed_sqrd = vel.dot(vel)  # note: speed != 0 because pos_dot_vel != 0
    dist_sqrd = dpos.dot(dpos)

    # Solve for t: |p + t v| == ball radius
    # For explanation, see comments in the toi_ball_ball function
    c_minus_r2 = dist_sqrd - radius**2
    delta_over_4 = pos_dot_vel * pos_dot_vel - speed_sqrd * c_minus_r2
    if delta_over_4 <= 0:
        return INF

    # Progate uncertainty of pos, analogous to toi_ball_ball
    dpos_x_err = 2 ** (pos_unreliable_ulps - 1) * ulp(pos[0])
    dpos_y_err = 2 ** (pos_unreliable_ulps - 1) * ulp(pos[1])
    dist_sqrd_err = 2.0001 * (abs(dpos[0]) * dpos_x_err + abs(dpos[1]) * dpos_y_err)

    # Return infinity if we can prove that the ball will not collide in
    # the present or the future
    if c_minus_r2 < -dist_sqrd_err:  # equivalent: toi + toi_err < 0
        return INF

    return c_minus_r2 / (-pos_dot_vel + sqrt(delta_over_4))


def toi_ball_disk_exterior(
    pos, vel, radius, disk_center, disk_radius, pos_unreliable_ulps=1
):
    """Calculate the time of impact of a moving ball and the exterior of a disk.

    Balls can collide with the exterior of the disk only from the inside
    of the disk and only if they fit inside it (i.e., if ball radius <
    disk radius).

    Args:
        pos: Center of the ball.
        vel: Velocity of the ball.
        radius: Radius of the ball.
        disk_center: Center of the disk.
        disk_radius: Radius of the disk.
        pos_unreliable_ulps (optional): The number of least significant
            bits in the position vector `pos` that may not be accurate.
            We assume that all bits of `disk_center` are accurate.
            For an explanation see the documentation of `toi_ball_ball`.
            Default: 1 (i.e., only the last bit may not be accurate).

    Returns:
        Time of impact, is infinite if there is no collision at the
        present or a future time.
    """
    if disk_radius <= radius:
        return INF  # no collision if the ball is larger than the disk

    # Compute the relative position between the ball and the disk
    dpos = np.subtract(pos, disk_center)
    vel = np.asarray(vel)

    # Compute the scalar products <p, v>, <v, v> = |v|^2 and <p, p> = |p|^2
    speed_sqrd = vel.dot(vel)
    if speed_sqrd == 0:
        return INF  # no collision if vel == (0, 0)

    pos_dot_vel = dpos.dot(vel)
    dist_sqrd = dpos.dot(dpos)

    # Solve for t: |p + t v| == disk radius - ball radius
    # If there are two solutions, only the LARGER t is a valid collision
    # For explanation, see comments in the toi_ball_ball function
    c_minus_r2 = dist_sqrd - (disk_radius - radius) ** 2
    delta_over_4 = pos_dot_vel * pos_dot_vel - speed_sqrd * c_minus_r2
    if delta_over_4 <= 0:
        return INF

    # Compute t2, choosing the algorithm which gives the most significant digits.
    # t1 = (-pos_dot_vel - sqrt(delta_over_4)) / speed_sqrd
    # t2 = (-pos_dot_vel + sqrt(delta_over_4)) / speed_sqrd
    # If abs(t2) < abs(t1), then more digits have cancelled in the t2-computation than
    # in the t1-computation => t1 has more significant digits

    if pos_dot_vel <= 0:  # equivalent: abs(t1) < abs(t2)
        # Note that due to the sign of pos_dot_vel and sqrt the collision time is
        # guaranteed to be >= 0.0
        return (-pos_dot_vel + sqrt(delta_over_4)) / speed_sqrd
    else:
        # Progate uncertainty of pos, analogous to toi_ball_ball
        dpos_x_err = 2 ** (pos_unreliable_ulps - 1) * ulp(pos[0])
        dpos_y_err = 2 ** (pos_unreliable_ulps - 1) * ulp(pos[1])
        dist_sqrd_err = 2.0001 * (abs(dpos[0]) * dpos_x_err + abs(dpos[1]) * dpos_y_err)

        # Return infinity if we can prove that the ball will not collide in
        # the present or the future
        if c_minus_r2 > dist_sqrd_err:  # equivalent: toi + toi_err < 0
            return INF

        # Use the t2 = c / (a t1) trick to get the same number of significant digits
        # as in t1
        return c_minus_r2 / (-pos_dot_vel - sqrt(delta_over_4))


def toi_ball_circle(pos, vel, radius, circle_center, circle_radius, t_eps=0.0):
    """Calculate the time of impact of a moving ball and a circle.

    Balls can collided from the outside or the inside of the circle, a
    ball overlapping the circle is not colliding with it.

    Args:
        pos: Center of the ball.
        vel: Velocity of the ball.
        radius: Radius of the ball.
        circle_center: Center of the circle.
        circle_radius: Radius of the circle.
        t_eps (optional): Return infinity if the calculated time of
            impact is less than ``t_eps``. Ideally we should use
            ``t_eps = 0.0``, but to account for rounding errors a value
            slightly lower than zero may be more useful in practice.
            Default: 0.0.

    Returns:
        Time of impact, which is infinite if there is no collision at or
        after the time ``t_eps``.
    """
    dpos = np.subtract(pos, circle_center)
    dist_sqrd = dpos.dot(dpos)

    # Keep track of absolute errors in floating point computations
    dpos_x_err = 2 * 2**-53 * max(abs(pos[0]), abs(circle_center[0]))
    dpos_y_err = 2 * 2**-53 * max(abs(pos[1]), abs(circle_center[1]))
    dist_sqrd_err = 2 * max(abs(dpos[0]) * dpos_x_err, abs(dpos[1]) * dpos_y_err)

    # Decide how the ball will collide with the circle
    if dist_sqrd - (circle_radius + radius) ** 2 > 2 * dist_sqrd_err:
        # Ball is outside => circle is equivalent to disk
        return toi_ball_ball(
            pos, vel, radius, circle_center, (0, 0), circle_radius, t_eps
        )
    elif (
        dist_sqrd - (circle_radius - radius) ** 2 > -2 * dist_sqrd_err
        and dpos.dot(vel) > 0
    ):
        # Ball overlaps the circle but moves away => no collision
        return INF
    else:
        # Ball is inside (or partly inside) => circle is equivalent to disk exterior
        return toi_ball_disk_exterior(
            pos, vel, radius, circle_center, circle_radius, t_eps
        )


def toi_and_param_ball_segment(
    pos, vel, radius, line_start, covector, normal, t_eps=-1e-10
):
    """Calculate the time of impact of a moving ball and an open line segment.

    This function will also return the line parameter for the collision
    point. If there is no collision (time is infinite) but the line
    parameter is 0 or 1, then the ball may collide with one the
    endpoints (0: test ``line_start``, 1: test ``line_end``). If the
    line parameter is None, there will be no collision with any
    endpoint.

    A ball already overlapping the segment is not colliding with it.
    But due to rounding errors, we could miss a collision if the ball is
    very close to the segment. Setting ``t_eps`` to a small negative
    value will catch this potential collision.

    A segment is defined by two points ``line_start`` and ``line_end``,
    but instead of the endpoints this functions requires the
    ``covector`` and the ``normal`` which can be computed as follows::

        direction = np.subtract(line_end, line_start)
        length_sqrd = direction.dot(direction)
        covector = direction / length_sqrd
        normal = np.asarray([-direction[1], direction[0]]) / sqrt(length_sqrd)

    Since ``covector`` and ``normal`` depend only on the endpoints, they
    can be computed when defining the line and then reused. (We don't
    acutally need to know the endpoints of the line since this
    information can be deduced from ``covector`` and ``normal``.)

    Args:
        pos: Center of the ball.
        vel: Velocity of the ball.
        radius: Radius of the ball.
        line_start: Starting point of the line segment.
        covector: Equal to ``(line_end - line_start) / line_length**2``.
        normal: Normalized vector perpendicular to the line.
        t_eps (optional): Return infinity if the calculated time of
            impact is less than ``t_eps``. Ideally we should use
            ``t_eps = 0.0``, but to account for rounding errors a value
            slightly lower than zero is more useful in practice.
            Default: -1e-10.

    Returns:
        A tuple ``(t, u)``, where ``t`` is the time of impact (a float)
        and ``u`` is the line parameter for the impact location (a float
        or an integer). If ``t`` is finite, the ball will touch the line
        at ``line_start + u * line_end``. If ``t`` is infinite and ``u``
        is None, the ball will not collide with the segment or its its
        endpoints. However, if ``t`` is infinite and ``u`` is an integer
        (0 or 1), then the ball *may* collide with the first endpoint
        (if ``u = 0``) or the second endpoint (if ``u = 1``). To check
        if there is a collision, use the `toi_ball_point` function.

    Notes:
        A ball-segment intersection problem is equivalent to a
        particle-capsule intersection problem (via Minkowski addition).
    """
    # The ball can collide with the line segment in four different places:
    # face-on from the left or from the right or with one of the endpoints.

    # Shift the position into the past by t_eps, later we only need to compare
    # the collision time to zero but correct for t_eps before we return it.

    # Switch to line coordinate system by projecting the relative position of
    # the ball onto the line direction and the normal direction, in this frame
    # the line segment has coordinates 0 <= dpos_line <= 1, dpos_normal == 0.
    dpos = np.subtract(pos, line_start) + t_eps * np.asarray(vel)
    dpos_line = covector.dot(dpos)
    dpos_normal = normal.dot(dpos)

    # If the distance in normal direction is smaller than the radius, then the
    # ball can only collide with one of the endpoints.
    if abs(dpos_normal) <= radius:
        # The sign of line_project indicates if the ball is behind (< 0) or
        # ahead (> 0) of line_start
        if dpos_line < 0:
            return INF, 0
        elif dpos_line > 1:
            return INF, 1
        else:
            # ball must overlap the line
            return INF, None

    # Next, we figure out where along the path of the ball it will hit the line.
    # Note that dpos_normal is the signed distance to the infinite line, we
    # divide it by the velocity in normal direction to get the collision time.
    vel_normal = normal.dot(vel)
    if vel_normal == 0:
        # ball moves parallel to the line and distance to the line is greater
        # than radius => no collision
        return INF, None

    # Compute the time when the distance to the line becomes equal to the radius
    t = -(dpos_normal + (-radius if dpos_normal > 0 else radius)) / vel_normal
    if t < 0:
        # ball is moving away
        return INF, None

    # Compute the line parameter u of the collision point. If 0 <= u <= 1, then
    # the collision point lies inside the segment. Otherwise the ball might
    # still hit one of the endpoints.
    u = dpos_line + t * covector.dot(vel)
    if 0 <= u <= 1:  # test u < 0, then u > 1 (one test fewer, faster?)
        return t + t_eps, u
    elif u < 0:
        return INF, 0
    else:
        return INF, 1


def elastic_collision(pos1, vel1, mass1, pos2, vel2, mass2):
    """Compute the velocities after a perfectly elastic collision of two balls.

    Args:
        pos1: Center of the first ball.
        vel1: Velocity of the first ball.
        mass1: Mass of the first ball.
        pos2: Center of the second ball.
        vel2: Velocity of the second ball.
        mass2: Mass of the second ball.

    Returns:
        A tuple ``(w1, w2)``, where ``w1`` is the velocity of the first
        ball and ``w2`` is the velocity of the second ball after the
        collision.

    Raises:
        ValueError: When the balls are not moving towards each other.
    """
    # Switch to coordinate system of ball 2
    dpos = np.subtract(pos1, pos2)
    dvel = np.subtract(vel1, vel2)

    # Make sure that impulse will be positive
    pos_dot_vel = dpos.dot(dvel)
    if pos_dot_vel > 1e-15:
        msg = f"Balls are not moving towards each other: pos * vel = {pos_dot_vel} > 0"
        raise ValueError(msg)

    # Compute the change in velocity (mass * impuls)
    impulse = 2 * (pos_dot_vel * dpos) / ((mass1 + mass2) * dpos.dot(dpos))
    return vel1 - mass2 * impulse, vel2 + mass1 * impulse
