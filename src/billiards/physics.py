"""This module contains functions for collision detection and handling.

To detect a collision between a ball and an obstacle, we compute the
*time of impact* (toi) and check that it is non-negative. Note that due
to floating-point issues the computed time of impact can be negative in
certain pathological cases (usually when the two balls or a ball and an
obstacle touch). Since these cases occur quite often (because a ball and
obstacles touch after resolving a previous collision), we allow for some
uncertainty of the ball position. See the documentation of
`set_pos_accuracy` for details.
"""

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

POS_RELIABLE_BITS = 52 - 20  # assume that the last 20 bits are inaccurate
POS_SCALE_ULPS = 2 ** (52 - POS_RELIABLE_BITS - 1)


def set_pos_accuracy(num_bits):
    """Specify the expected accuracy of the ball position in bits.

    By default, the ball coordinates are recorded as 64-bit
    floating-point numbers. Since these numbers have only a finite
    precision, arithmetic operations can introduce rounding errors or
    cancel significant digits, decreasing the accuracy of the final
    result.

    This is a problem because the toi-functions should compute a time
    that is not in the past, and we would like to implement this via
    a statement ``return INF if toi < 0 else toi``. However, if the ball
    position is slightly inaccurate such that the ball accidentally
    overlaps an obstacle, then the computed time of impact will be
    negative.

    To correct for such floating-point issues, we keep track of the
    uncertainty in the position and if the amount of overlap is within
    the propagated uncertainty, we will return the (negative) toi
    anyway. (The minimal allowed time is roughly the time it takes the
    ball to traverse the uncertainty range at the given velocity.)

    Args:
        num_bits: The number of bits in the ball position coordinates
            that are expected to be accurate. The maximum is 52, since
            64-bit floating point numbers use a 52-bit mantissa.

            To indicate that the last four bits may be inaccurate, use
            ``num_bits = 52 - 4``.

            To set the uncertainty via a given relative tolerance (e.g.
            ``rel_tol = 1e-9``), use ``num_bits = -log2(rel_tol) - 1``.
    """
    global POS_RELIABLE_BITS, POS_SCALE_ULPS
    POS_RELIABLE_BITS = min(num_bits, 52)
    POS_SCALE_ULPS = 2 ** (52 - POS_RELIABLE_BITS - 1)
    # POS_REL_TOL = 2 ** (-POS_RELIABLE_BITS - 1)


def toi_ball_ball(pos1, vel1, radius1, pos2, vel2, radius2):
    """Calculate the time of impact of two moving balls.

    If the balls are not colliding in the present or future, the
    returned time is infinite. Already overlapping balls are not
    considered to be colliding (because the collision has already
    happened).

    Note that the returned time may be negative! See the documentation
    of `set_pos_accuracy` for an explanation.

    Notes:
        Two balls are colliding at a present or future time if

        - at least one of them is not a point particle,
        - they move towards each other (the dot product of
          ``pos1 - pos2`` and ``vel1 - vel2`` is >= 0),
        - they don't overlap (the distance between ``pos1`` and ``pos2``
          is larger than ``radius1 + radius2`` plus some tolerance to
          account for the floating-point inaccuracy of the position),
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

    Returns:
        Time of impact, is infinite if there is no collision at the
        present or a future time.
    """
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
    # Note that delta / 4 = <p, v>^2 - <v, v> * (<p, p> - (r1 + r2)^2).
    # If the directions of p and v are very similar (as usually happens when two balls
    # are on a collision course), then <p, v>^2 - <v, v> * <p, p> will suffer from
    # cancellation of significant digits. Using the identity
    # <p, v>^2 - <p, p> * <v, v> = - ||p x v||^2
    # is numerically more stable.
    rsum_sqrd = (radius1 + radius2) * (radius1 + radius2)
    cross = dpos[0] * dvel[1] - dpos[1] * dvel[0]
    delta_over_4 = speed_sqrd * rsum_sqrd - cross * cross
    if delta_over_4 <= 0:
        return INF  # no collision if the balls miss or slide past each other

    # The sign of c - (radius1 + radius2)^2 determines if the balls overlap:
    # c_minus_r2 < 0: the balls overlap,
    # c_minus_r2 == 0: the balls touch,
    # c_minus_r2 > 0: there is a gap separating the balls
    c_minus_r2 = dist_sqrd - rsum_sqrd

    # In practice, we don't want to check c_minus_r2 against zero because the least
    # significant bits of the position vectors may be inaccurate. Instead we propagate
    # the uncertainty of the position and check against the error of dist_sqrd.
    # We assume that the uncertainty of pos[i] is POS_SCALE_ULPS * ulp(pos[i]) and the
    # uncertainty of other quantities is ulp(x) / 2, i.e. all present bits are accurate.
    # To propagate absolute errors, we use the linear approximations
    # (x + x_err) + (y + y_err) = (x + y) + (x_err + y_err)
    # (x + x_err) - (y + y_err) = (x - y) + (x_err + y_err)
    # (x + x_err) * (y + y_err) = (x * y) + (|x| * y_err + |y| * x_err) + (negligible)
    # (x + x_err) ** n = x ** n + n * |x| ** (n - 1) * x_err + (negligible), n > 0
    dpos_x_err = POS_SCALE_ULPS * (ulp(pos1[0]) + ulp(pos2[0]))
    dpos_y_err = POS_SCALE_ULPS * (ulp(pos1[1]) + ulp(pos2[1]))
    dist_sqrd_err = 2 * (abs(dpos[0]) * dpos_x_err + abs(dpos[1]) * dpos_y_err)
    rsum_sqrd_err = 2 * (radius1 + radius2) * (ulp(radius1) + ulp(radius2)) / 2

    if c_minus_r2 < -(dist_sqrd_err + rsum_sqrd_err):
        return INF  # No collision because we can prove that the balls already overlap

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


def toi_ball_disk(pos, vel, radius, disk_center, disk_radius):
    """Calculate the time of impact of a moving ball and a disk.

    Args:
        pos: Center of the ball.
        vel: Velocity of the ball.
        radius: Radius of the ball.
        disk_center: Center of the disk.
        disk_radius: Radius of the disk.

    Returns:
        Time of impact, is infinite if there is no collision at the
        present or a future time.
    """
    # Compute the relative position between the ball and the disk
    dpos = np.subtract(pos, disk_center)
    vel = np.asarray(vel)

    # Compute the scalar products <p, v>, <v, v> = |v|^2 and <p, p> = |p|^2
    pos_dot_vel = dpos.dot(vel)
    if pos_dot_vel >= 0:
        return INF  # no collision if the ball is not moving towards the disk

    speed_sqrd = vel.dot(vel)  # note: speed != 0 because pos_dot_vel != 0
    dist_sqrd = dpos.dot(dpos)

    # Solve for t: |p + t v| == ball radius + disk radius
    # For explanation, see comments in the toi_ball_ball function
    rsum_sqrd = (radius + disk_radius) * (radius + disk_radius)
    cross = dpos[0] * vel[1] - dpos[1] * vel[0]
    delta_over_4 = speed_sqrd * rsum_sqrd - cross * cross
    if delta_over_4 <= 0:
        return INF  # no collision if the ball misses or slides past the disk

    # The sign of c - (radius + disk radius)^2 determines if the ball overlaps the disk
    c_minus_r2 = dist_sqrd - rsum_sqrd

    # Progate uncertainty of pos, analogous to toi_ball_ball
    dpos_x_err = POS_SCALE_ULPS * ulp(pos[0]) + ulp(disk_center[0]) / 2
    dpos_y_err = POS_SCALE_ULPS * ulp(pos[1]) + ulp(disk_center[1]) / 2
    dist_sqrd_err = 2 * (abs(dpos[0]) * dpos_x_err + abs(dpos[1]) * dpos_y_err)
    rsum_sqrd_err = 2 * (radius + disk_radius) * (ulp(radius) + ulp(disk_radius)) / 2

    if c_minus_r2 < -(dist_sqrd_err + rsum_sqrd_err):
        # No collision because we can prove that the ball already overlaps the disk
        return INF

    return c_minus_r2 / (-pos_dot_vel + sqrt(delta_over_4))


def toi_ball_point(pos, vel, radius, point):
    """Calculate the time of impact of a moving ball and a static point.

    This function is similar to (but slightly faster than)
    ``toi_ball_disk(pos, vel, radius, point, 0)``.

    Args:
        pos: Center of the ball.
        vel: Velocity of the ball.
        radius: Radius of the ball.
        point: Position of the point.

    Returns:
        Time of impact, is infinite if there is no collision at the
        present or a future time.
    """
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
    radius_sqrd = radius * radius
    cross = dpos[0] * vel[1] - dpos[1] * vel[0]
    delta_over_4 = speed_sqrd * radius_sqrd - cross * cross
    if delta_over_4 <= 0:
        return INF  # no collision if the ball misses or slides past the point

    # The sign of c - radius^2 determines if the ball overlaps the point
    c_minus_r2 = dist_sqrd - radius_sqrd

    # Progate uncertainty of pos, analogous to toi_ball_ball
    dpos_x_err = POS_SCALE_ULPS * ulp(pos[0]) + ulp(point[0]) / 2
    dpos_y_err = POS_SCALE_ULPS * ulp(pos[1]) + ulp(point[1]) / 2
    dist_sqrd_err = 2 * (abs(dpos[0]) * dpos_x_err + abs(dpos[1]) * dpos_y_err)
    radius_sqrd_err = 2 * radius * (ulp(radius) / 2)

    if c_minus_r2 < -(dist_sqrd_err + radius_sqrd_err):
        # No collision because we can prove that the ball already overlaps the point
        return INF

    return c_minus_r2 / (-pos_dot_vel + sqrt(delta_over_4))


def toi_ball_disk_exterior(pos, vel, radius, disk_center, disk_radius):
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
    # For details, see comments in the toi_ball_ball function
    rsum_sqrd = (disk_radius - radius) * (disk_radius - radius)
    cross = dpos[0] * vel[1] - dpos[1] * vel[0]
    delta_over_4 = speed_sqrd * rsum_sqrd - cross * cross
    if delta_over_4 <= 0:
        return INF  # no collision if the balls misses or slide past the disk outline
    c_minus_r2 = dist_sqrd - rsum_sqrd

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
        dpos_x_err = POS_SCALE_ULPS * ulp(pos[0]) + ulp(disk_center[0]) / 2
        dpos_y_err = POS_SCALE_ULPS * ulp(pos[1]) + ulp(disk_center[1]) / 2
        dist_sqrd_err = 2 * (abs(dpos[0]) * dpos_x_err + abs(dpos[1]) * dpos_y_err)
        rsum_sqrd_err = (
            2 * (disk_radius - radius) * (ulp(radius) + ulp(disk_radius)) / 2
        )

        if c_minus_r2 > dist_sqrd_err + rsum_sqrd_err:
            # No collision because we can prove that the ball already overlaps the
            # exterior of the disk (and because pos_dot_vel > 0 so it can only move
            # further away from the center)
            return INF

        # Use the t2 = c / (a t1) trick to get the same number of significant digits
        # as in t1
        return c_minus_r2 / (-pos_dot_vel - sqrt(delta_over_4))


def toi_ball_circle(pos, vel, radius, circle_center, circle_radius):
    """Calculate the time of impact of a moving ball and a circle.

    Balls can collide from the outside or the inside of the circle, a
    ball overlapping the circle and moving away from the center is not
    colliding with the circle. If instead the ball is moving towards the
    center, it may collide with the circle's boundary from the inside.

    Args:
        pos: Center of the ball.
        vel: Velocity of the ball.
        radius: Radius of the ball.
        circle_center: Center of the circle.
        circle_radius: Radius of the circle.

    Returns:
        Time of impact, is infinite if there is no collision at the
        present or a future time.
    """
    # Compute distance of ball center to circle center
    dpos = np.subtract(pos, circle_center)
    dist_sqrd = dpos.dot(dpos)

    # Keep track of absolute errors in floating point computations
    dpos_x_err = POS_SCALE_ULPS * ulp(pos[0]) + ulp(circle_center[0]) / 2
    dpos_y_err = POS_SCALE_ULPS * ulp(pos[1]) + ulp(circle_center[1]) / 2
    dist_sqrd_err = 2 * (abs(dpos[0]) * dpos_x_err + abs(dpos[1]) * dpos_y_err)
    radius_sqrd_err = circle_radius * ulp(circle_radius) / 2

    # Figure out how the ball collides with the circle
    dist_sqrd_minus_radius_sqrd = dist_sqrd - circle_radius**2
    dist_sqrd_minus_radius_sqrd_err = dist_sqrd_err + radius_sqrd_err
    if dist_sqrd_minus_radius_sqrd > dist_sqrd_minus_radius_sqrd_err:
        # Ball is outside => circle is equivalent to disk
        return toi_ball_disk(pos, vel, radius, circle_center, circle_radius)
    elif (
        dist_sqrd_minus_radius_sqrd > -dist_sqrd_minus_radius_sqrd_err
        and dpos.dot(vel) > 0
    ):
        # Ball overlaps the circle and moves away => no collision
        return INF
    else:
        # Ball is inside (or partly inside) => circle is equivalent to disk exterior
        return toi_ball_disk_exterior(pos, vel, radius, circle_center, circle_radius)


def toi_and_param_ball_line_onesided(pos, vel, radius, line_point, line_normal):
    """Calculate the time of impact of a moving ball and a halfplane.

    The halfplane is an infinite line that detects collisions only from
    one side.

    Args:
        pos: Center of the ball.
        vel: Velocity of the ball.
        radius: Radius of the ball.
        line_point: A point on the boundary of the halfplane. Ideally,
            it should be a point that is close to the origin (to
            minimize rounding errors).
        line_normal: The normal vector perpendicular to the boundary,
            pointing towards the outside (the allowed area) of the
            halfplane. The input vector must be normalized (have a
            euclidean length of 1), otherwise the computed time is not
            correct.

    Returns:
        Time of impact, is infinite if there is no collision at the
        present or a future time.
    """
    # vel_normal: speed away from the wall, is negative if the ball
    # moves toward the no-go area and positive if it moves away from it
    vel_normal = line_normal.dot(vel)
    if vel_normal >= 0:
        # No collision if the ball doesn't move towards the halfplane
        return INF, (vel_normal,)

    # Compute the relative position between the ball and the halfplane
    dpos = np.subtract(pos, line_point)
    dpos_x_err = POS_RELIABLE_BITS * ulp(pos[0]) + ulp(line_point[0]) / 2
    dpos_y_err = POS_RELIABLE_BITS * ulp(pos[1]) + ulp(line_point[1]) / 2

    dpos_normal = line_normal.dot(dpos)
    dpos_normal_err = (
        abs(line_normal[0]) * dpos_x_err
        + ulp(line_normal[0]) / 2 * abs(dpos[0])
        + abs(line_normal[1]) * dpos_y_err
        + ulp(line_normal[1]) / 2 * abs(dpos[1])
    )

    if dpos_normal - radius < -(dpos_normal_err + ulp(radius) / 2):
        # No collision because we can prove that the ball already overlaps the halfplane
        return INF, (vel_normal,)

    # The ball collides with the wall when the gap between ball and
    # wall becomes equal to the ball radius:
    # <normal, dpos + t * vel> == radius
    # Rearranged: <normal, dpos> - radius == - t * <normal, vel>,
    # note that <normal, dpos> - radius is the size of the gap and
    # -<normal, vel> is the speed of closing the gap.
    return -(dpos_normal - radius) / vel_normal, (vel_normal,)


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
