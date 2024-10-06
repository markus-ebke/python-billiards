"""This module contains functions for collision detection and handling."""

from math import sqrt

import numpy as np

INF = float("inf")


def toi_ball_ball(pos1, vel1, radius1, pos2, vel2, radius2, t_eps=-1e-10):
    """Calculate the time of impact for two moving balls.

    Already overlapping balls are not colliding (because the collision already
    occured), but due to rounding errors we could miss a collision of two balls
    that are very close. Adjusting t_eps will help in these situations.

    Args:
        pos1: Center of the first ball.
        vel1: Velocity of the first ball.
        radius1: Radius of the first ball.
        pos2: Center of the second ball.
        vel2: Velocity of the second ball.
        radius2: Radius of the second ball.
        t_eps (optional): Return infinity if the calculated time of collision is
            less than t_eps. Ideally we should set t_eps = 0, but due to
            rounding errors a value slightly lower than zero is more useful.
            Default: -1e-10.

    Returns:
        Time of impact, is infinite if there is no collision.
    """
    # Compute the relative position and velocity between the two balls
    dpos = np.subtract(pos2, pos1)
    dvel = np.subtract(vel2, vel1)

    # Compute the scalar products dp*dp, dp*dv and dv*dv. If dp*dv >= 0 then the
    # balls are not moving towards each other => no collision
    pos_dot_vel = dpos.dot(dvel)
    if pos_dot_vel >= 0:
        return INF

    dist_sqrd = dpos.dot(dpos)
    speed_sqrd = dvel.dot(dvel)  # note: vel_sqrd != 0
    assert speed_sqrd > 0, speed_sqrd

    # The time of impact is a solution of the quadratic equation
    # a t^2 + b t + c = 0 with a = speed_sqrd, b = pos_dot_vel and
    # c = (dist_sqrd - (radius1 + radius2)^2) / 4. Depending on the value of
    # the discriminant = b^2 - 4 a c, we can have no solution (when the balls
    # miss), one solution (when the balls slide past each other, this is not a
    # collision) or two solutions (and the smaller one is the time we want).
    c = dist_sqrd - (radius1 + radius2) ** 2
    discriminant = pos_dot_vel * pos_dot_vel - speed_sqrd * c
    if discriminant <= 0:
        # the balls miss or slide past each other
        return INF

    # Write out the solutions t12 = (-b -+ sqrt(discriminant) / a. Since t1 < t2
    # the time of impact is t1 and we don't need to compute t2.
    # t1 = (-pos_dot_vel - sqrt(discriminant)) / speed_sqrd

    # Alternative for computing t1: compute t2 = (-b + sqrt(discriminant)) / a
    # which is not affected by cancellation of significant digits (because
    # -b > 0 and sqrt(...) > 0), then use that from
    # a (t - t1) (t - t2) = a t^2 - a (t1 + t2) t + a t1 t2 == a t^2 + b t + c
    # we can derive t1 = c / (a t2).
    t1 = c / (-pos_dot_vel + sqrt(discriminant))
    assert -pos_dot_vel + sqrt(discriminant) > 0, (t1, pos_dot_vel, sqrt(discriminant))

    # Note that t2 > 0 (because -b > 0 and sqrt(b**2-c) > 0). If t1 is negative,
    # then t1 < 0 < t2 which means that the balls overlap. This doesn't count as
    # a collision, so we return infinity.
    # However, if t1 is close to zero, then a valid collision might have
    # happened and we miss it just because of rounding errors. That's why we
    # check t1 > t_eps (note t_eps < 0) instead of t1 > 0.
    return t1 if t1 >= t_eps else INF


def toi_ball_point(pos, vel, radius, point, t_eps=-1e-10):
    """Calculate the time of impact for a moving ball and a static point.

    If the point is inside the ball no collision will be returned (because the
    collision already occured), but due to rounding errors we could miss a
    collision if the point is very close to the ball's surface. Adjusting t_eps
    will help in these situations.

    Args:
        pos: Center of the ball.
        vel: Velocity of the ball.
        radius: Radius of the ball.
        point: Position of the point.
        t_eps (optional): Return infinity if the calculated time of collision is
            less than t_eps. Ideally we should set t_eps = 0, but due to
            rounding errors a value slightly lower than zero is more useful.
            Default: -1e-10.

    Returns:
        Time of impact, is infinite if there is no collision.
    """
    # Compute the relative position between the ball and the point
    dpos = np.subtract(pos, point)
    vel = np.asarray(vel)

    # Compute the scalar products dp*dp, dp*dv and dv*dv. If dp*dv >= 0 then the
    # balls are not moving towards each other => no collision
    pos_dot_vel = dpos.dot(vel)
    if pos_dot_vel >= 0:
        return INF

    dist_sqrd = dpos.dot(dpos)
    speed_sqrd = vel.dot(vel)  # note: vel_sqrd != 0
    assert speed_sqrd > 0, speed_sqrd

    # The time of impact is a solution of the quadratic equation
    # a t^2 + b t + c = 0 with a = speed_sqrd, b = pos_dot_vel and
    # c = (dist_sqrd - radius^2) / 4. Depending on the value of the
    # discriminant = b^2 - 4 a c, we can have no solution (when the balls miss),
    # one solution (when the balls slide past each other, this is not a
    # collision) or two solutions (and the smaller one is the time we want).
    c = dist_sqrd - radius**2
    discriminant = pos_dot_vel * pos_dot_vel - speed_sqrd * c
    if discriminant <= 0:
        # the balls miss or slide past each other
        return INF

    # Write out the solutions t12 = (-b -+ sqrt(discriminant) / a. Since t1 < t2
    # the time of impact is t1 and we don't need to compute t2.
    # t1 = (-pos_dot_vel - sqrt(discriminant)) / speed_sqrd

    # Alternative for computing t1: compute t2 = (-b + sqrt(discriminant)) / a
    # which is not affected by cancellation of significant digits (because
    # -b > 0 and sqrt(...) > 0), then use that from
    # a (t - t1) (t - t2) = a t^2 - a (t1 + t2) t + a t1 t2 == a t^2 + b t + c
    # we can derive t1 = c / (a t2).
    t1 = c / (-pos_dot_vel + sqrt(discriminant))
    assert -pos_dot_vel + sqrt(discriminant) > 0, (t1, pos_dot_vel, sqrt(discriminant))

    # Note that t2 > 0 (because -b > 0 and sqrt(b**2-c) > 0). If t1 is negative,
    # then t1 < 0 < t2 which means that the balls overlap. This doesn't count as
    # a collision, so we return infinity.
    # However, if t1 is close to zero, then a valid collision might have
    # happened and we miss it just because of rounding errors. That's why we
    # check t1 > t_eps (note t_eps < 0) instead of t1 > 0.
    return t1 if t1 >= t_eps else INF


def toi_and_param_ball_segment(
    pos, vel, radius, line_start, covector, normal, t_eps=-1e-10
):
    """Calculate the time of impact for a moving ball and an open line segment.

    Will also return the line parameter for the collision point. If there is no
    collision (time is infinite) but the line parameter is 0 or 1, then the ball may
    collide with one the endpoints (0: test ``line_start``, 1: test ``line_end``). If
    the line parameter is None, there will be no collision with any endpoint.

    If the ball and the segment overlap, no collision will be returned (because
    the collision already occured), but (due to rounding errors) we could miss a
    collision if the ball's surface is very close to the segment. Adjusting ``t_eps``
    will help in these situations.

    The segment is defined by ``line_start`` and `line_end`, however instead of the
    enpoint we require ``covector`` and ``normal`` which can be computed as follows::

        direction = np.subtract(line_end, line_start)
        length_sqrd = direction.dot(direction)
        covector = direction / length_sqrd
        normal = np.asarray([-direction[1], direction[0]]) / sqrt(length_sqrd)

    Since ``covector`` and ``normal`` depend only on the line segment, they need to be
    computed only once when we define the line.

    This function does not need to know the endpoint of the line since the information
    is contained in ``covector`` and ``normal``.

    Args:
        pos: Center of the ball.
        vel: Velocity of the ball.
        radius: Radius of the ball.
        line_start: Starting point of the line segment.
        covector: Equal to (line_end - line_start) / line_length**2.
        normal: Normalized vector perpendicular to the line.
        t_eps (optional): Return infinity if the calculated time of collision is
            less than t_eps. Ideally we should set t_eps = 0, but due to
            rounding errors a value slightly lower than zero is more useful.
            Default: -1e-10.

    Returns:
        A tuple ``(t, u)`` where ``t`` is the time of impact (a float) and ``u`` is the
        line parameter for the impact location (a float or an integer). If ``t`` is
        finite, the ball will touch the line at ``line_start + u * line_end``. If ``t``
        is infinite and ``u`` is None, the ball will not collide with the segment or any
        of its endpoints. However if ``t`` is infinite and ``u`` is an integer (0 or 1),
        the ball may collide with the first endpoint (if ``u = 0``) or the second
        endpoint (if ``u = 1``). To test if there is a collision, use the
        ``toi_ball_point`` function.

    Notes:
        A ball-segment intersection problem is equivalent to a particle-capsule
        intersection problem (via Minkowski addition).
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
    """Compute velocities after a perfectly elastic collision between 2 balls.

    Args:
        pos1: Center of the first ball.
        vel1: Velocity of the first ball.
        mass1: Mass of the first ball.
        pos2: Center of the second ball.
        vel2: Velocity of the second ball.
        mass2: Mass of the second ball.

    Returns:
        The two velocities after the collision.

    Raises:
        ValueError: When the two balls are not moving towards each other.
    """
    # switch to coordinate system of ball 1
    pos_diff = np.subtract(pos2, pos1)
    vel_diff = np.subtract(vel2, vel1)

    pos_dot_vel = pos_diff.dot(vel_diff)
    if pos_dot_vel > 1e-15:
        msg = f"Balls are not moving towards each other: pos * vel = {pos_dot_vel} > 0"
        raise ValueError(msg)

    impulse = 2 * (pos_dot_vel * pos_diff) / ((mass1 + mass2) * pos_diff.dot(pos_diff))
    return vel1 + mass2 * impulse, vel2 - mass1 * impulse
