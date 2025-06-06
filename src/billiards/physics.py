"""This module contains functions for collision detection and handling.

To detect a collision between a ball and an obstacle, we compute the
*time of impact* (toi) and check that it is non-negative. Note that due
to floating-point issues, a ball and obstacle (or two balls) may
erronously overlap, causing the toi to be negative. To handle such
issues, we allow for some uncertainty of the ball position.

The size of this uncertainty range is controlled by the module-level
variables `REL_TOL` and `ABS_TOL`. The uncertainty of the x-coordinate
of a ball is ``max(REL_TOL * abs(x), ABS_TOL)`` (and similar for the
y-coordinate). If there is a position within this range such that the
ball and obstacle do not overlap, then we assume that the ball and the
obstacle do not touch and return the computed toi (which my be negative).

Attributes:
    REL_TOL (float): Relative tolerance for position uncertainty.
        The default value is ``2 ** (-53 + 10)``, i.e. we assume that
        the last 10 bits of a float64 number are inaccurate.
    ABS_TOL (float): Absolute tolerance for position uncertainty.
        The default value is ``0.0``
"""

from math import fabs, sqrt

try:
    from math import ulp
except ImportError:  # pragma: no cover
    # Python < 3.9 does not contain math.ulp, so we need to define it ourselves
    from math import frexp

    def ulp(x):
        """Return the value of the least significant bit of the float x."""
        # Unit in the Last Place for 64-bit (double precision) floating point numbers
        return 2 ** (frexp(x)[1] - 53)


import numpy as np

INF = float("inf")
REL_TOL = 2 ** (-53 + 10)  # assume that the last 10 bits of a float64 are inaccurate
ABS_TOL = 0.0


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
        Time of impact, is infinite if there is no collision now or in
        the future.
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
    # We assume that the uncertainty of pos[i] is max(REL_TOL * fabs(pos[i]), ABS_TOL)
    # and the uncertainty of other quantities is ulp(x) / 2, i.e. all present bits are
    # accurate.
    # To propagate absolute errors, we use the linear approximations
    # (x + x_err) + (y + y_err) = (x + y) + (x_err + y_err)
    # (x + x_err) - (y + y_err) = (x - y) + (x_err + y_err)
    # (x + x_err) * (y + y_err) = (x * y) + (|x| * y_err + |y| * x_err) + (negligible)
    # (x + x_err) ** n = x ** n + n * |x| ** (n - 1) * x_err + (negligible), n > 0
    dpos_x_err = max(REL_TOL * (fabs(pos1[0]) + fabs(pos2[0])), ABS_TOL)
    dpos_y_err = max(REL_TOL * (fabs(pos1[1]) + fabs(pos2[1])), ABS_TOL)
    dist_sqrd_err = 2 * (fabs(dpos[0]) * dpos_x_err + fabs(dpos[1]) * dpos_y_err)
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
        Time of impact, is infinite if there is no collision now or in
        the future.
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
    dpos_x_err = max(REL_TOL * fabs(pos[0]), ABS_TOL) + ulp(disk_center[0]) / 2
    dpos_y_err = max(REL_TOL * fabs(pos[1]), ABS_TOL) + ulp(disk_center[1]) / 2
    dist_sqrd_err = 2 * (fabs(dpos[0]) * dpos_x_err + fabs(dpos[1]) * dpos_y_err)
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
        Time of impact, is infinite if there is no collision now or in
        the future.
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
    dpos_x_err = max(REL_TOL * fabs(pos[0]), ABS_TOL) + ulp(point[0]) / 2
    dpos_y_err = max(REL_TOL * fabs(pos[1]), ABS_TOL) + ulp(point[1]) / 2
    dist_sqrd_err = 2 * (fabs(dpos[0]) * dpos_x_err + fabs(dpos[1]) * dpos_y_err)
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
        Time of impact, is infinite if there is no collision now or in
        the future.
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
        dpos_x_err = max(REL_TOL * fabs(pos[0]), ABS_TOL) + ulp(disk_center[0]) / 2
        dpos_y_err = max(REL_TOL * fabs(pos[1]), ABS_TOL) + ulp(disk_center[1]) / 2
        dist_sqrd_err = 2 * (fabs(dpos[0]) * dpos_x_err + fabs(dpos[1]) * dpos_y_err)
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
    inside, it may collide with the circle's boundary from within.

    If it is unclear if the ball is outside of the circle (due to
    numerical inaccuracy of the position vector), treat it as an overlap
    and test for collision from the inside.

    Args:
        pos: Center of the ball.
        vel: Velocity of the ball.
        radius: Radius of the ball.
        circle_center: Center of the circle.
        circle_radius: Radius of the circle.

    Returns:
        Time of impact, is infinite if there is no collision now or in
        the future.
    """
    # Compute distance of ball center to circle center
    dpos = np.subtract(pos, circle_center)
    dist_sqrd = dpos.dot(dpos)

    # Keep track of absolute errors in floating point computations
    dpos_x_err = max(REL_TOL * fabs(pos[0]), ABS_TOL) + ulp(circle_center[0]) / 2
    dpos_y_err = max(REL_TOL * fabs(pos[1]), ABS_TOL) + ulp(circle_center[1]) / 2
    dist_sqrd_err = 2 * (fabs(dpos[0]) * dpos_x_err + fabs(dpos[1]) * dpos_y_err)
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


def toi_args_ball_line_onesided(pos, vel, radius, line_point, line_normal):
    """Calculate the time of impact of a moving ball and an infinite line.

    The infinite line is one-sided; it detects collisions only from the
    side toward which ``line_normal`` points.

    Args:
        pos: Center of the ball.
        vel: Velocity of the ball.
        radius: Radius of the ball.
        line_point: A point that lies on the line (preferably near the
            origin to minimize numerical errors).
        line_normal: The unit vector that is perpendicular to the line
            and pointing *away* from the blocked area.

    Returns:
        A tuple ``(t, args)``, where ``t`` is the collision time (a
        float) and ``args`` is a tuple of arguments that can be used
        when resolving a collision. The time is infinite if there is no
        collision now or in the future. The ``args`` tuple contains a
        single entry which is ``line_normal.dot(vel)`` (the component of
        the ball's velocity perpendicular to the line, is negative if
        the ball is moving toward the blocked area).
    """
    # vel_normal: the component of the ball's velocity perpendicular to
    # the line, is negative if the ball is moving toward the blocked area
    vel_normal = line_normal.dot(vel)
    if vel_normal >= 0.0:
        # No collision if the ball doesn't move towards the blocked area
        return INF, (vel_normal,)

    # Compute the relative position between the ball and the blocked area
    dpos = np.subtract(pos, line_point)
    dpos_x_err = max(REL_TOL * fabs(pos[0]), ABS_TOL) + ulp(line_point[0]) / 2
    dpos_y_err = max(REL_TOL * fabs(pos[1]), ABS_TOL) + ulp(line_point[1]) / 2

    dpos_normal = line_normal.dot(dpos)
    dpos_normal_err = (
        fabs(line_normal[0]) * dpos_x_err
        + ulp(line_normal[0]) / 2 * fabs(dpos[0])
        + fabs(line_normal[1]) * dpos_y_err
        + ulp(line_normal[1]) / 2 * fabs(dpos[1])
    )

    if dpos_normal - radius < -(dpos_normal_err + ulp(radius) / 2):
        # No collision because we can prove that the ball already overlaps the blocked
        # area
        return INF, (vel_normal,)

    # The ball collides with the line when the gap between ball and
    # blocked area becomes equal to the ball radius:
    # <normal, dpos + t * vel> == radius
    # Rearranged: <normal, dpos> - radius == - t * <normal, vel>,
    # note that <normal, dpos> - radius is the size of the gap and
    # -<normal, vel> is the speed of closing the gap.
    return -(dpos_normal - radius) / vel_normal, (vel_normal,)


def toi_args_ball_segment_onesided(
    pos, vel, radius, line_start, line_end, line_normal, line_covector
):
    """Calculate the time of impact of a moving ball and a line segment.

    The line segment is one-sided; it detects collisions only from the
    side toward which ``line_normal`` points.

    A segment is defined by two points ``line_start`` and ``line_end``,
    but this functions also requires the ``covector`` and the ``normal``
    which can be computed as follows::

        direction = np.subtract(line_end, line_start)
        length_sqrd = direction.dot(direction)
        covector = direction / length_sqrd
        normal = np.asarray([-direction[1], direction[0]]) / sqrt(length_sqrd)

    Since ``covector`` and ``normal`` depend only on the endpoints, they
    only need to be computed once (when defining the line) and reused
    for each function call.

    Args:
        pos: Center of the ball.
        vel: Velocity of the ball.
        radius: Radius of the ball.
        line_start: Starting point of the segment.
        line_end: Endpoint of the segment.
        line_normal: The unit vector that is perpendicular to the line
            and pointing *away* from the blocked area.
        line_covector: The vector in the direction of the line, but with
            a euclidean length of ``1 / length``, where ``length`` is
            the length of the segment (the distance between
            ``line_start`` and ``line_end``).

    Returns:
        A tuple ``(t, args)``, where ``t`` is the collision time (a
        float) and ``args`` is a tuple of arguments that can be used
        when resolving a collision. The time is infinite if there is no
        collision now or in the future. The ``args`` tuple contains two
        entries: ``line_normal.dot(vel)`` (the component of the ball's
        velocity perpendicular to the line, is negative if the ball is
        moving toward the blocked area) and ``u`` (the line parameter
        for the impact location). If the time of impact is finite, then
        ``line_start + u * line_end`` is the position where the ball
        will touch the line (and ``0 <= u <= 1``). If ``u`` is an
        integer, then the ball collides with the endpoint at
        ``line_start`` (when ``u == 0``) or the endpoint at ``line_end``
        (when ``u == 1``). Use this information to resolve the collision
        accordingly.
    """
    # vel_normal: the component of the ball's velocity perpendicular to
    # the line, is negative if the ball is moving toward the blocked area
    vel_normal = line_normal.dot(vel)
    if vel_normal >= 0.0:
        # No collision if the ball doesn't move towards the blocked area
        return INF, (vel_normal, None)

    # Compute the time of impact with the infinite line
    dpos = np.subtract(pos, line_start)
    dpos_normal = line_normal.dot(dpos)
    t = -(dpos_normal - radius) / vel_normal

    # Compute the line parameter u of the collision point. If 0 <= u <= 1,
    # then the collision point lies inside the segment. Otherwise the ball
    # might still hit one of the endpoints.
    u = line_covector.dot(dpos) + t * line_covector.dot(vel)
    if u < 0.0:
        return toi_ball_point(pos, vel, radius, line_start), (vel_normal, 0)
    elif u > 1.0:
        return toi_ball_point(pos, vel, radius, line_end), (vel_normal, 1)
    else:  # 0 <= u <= 1
        dpos_x_err = max(REL_TOL * fabs(pos[0]), ABS_TOL) + ulp(line_start[0]) / 2
        dpos_y_err = max(REL_TOL * fabs(pos[1]), ABS_TOL) + ulp(line_start[1]) / 2
        dpos_normal_err = (
            fabs(line_normal[0]) * dpos_x_err
            + ulp(line_normal[0]) / 2 * fabs(dpos[0])
            + fabs(line_normal[1]) * dpos_y_err
            + ulp(line_normal[1]) / 2 * fabs(dpos[1])
        )

        if dpos_normal - radius < -(dpos_normal_err + ulp(radius) / 2):
            # No collision because we can prove that the ball already overlaps
            # the blocked area
            return INF, (vel_normal, u)
        else:
            return t, (vel_normal, u)


def toi_args_ball_segment_twosided(
    pos, vel, radius, line_start, line_end, line_normal, line_covector
):
    """Calculate the time of impact of a moving ball and a line segment.

    The line segment is two-sided; it detects collisions from both
    sides. If it is unclear if the ball overlaps the segment (due to
    numerical inaccuracy of the position vector), treat it as an overlap
    and return an infinite time of impact.

    A segment is defined by two points ``line_start`` and ``line_end``,
    but this functions also requires the ``covector`` and the ``normal``
    which can be computed as follows::

        direction = np.subtract(line_end, line_start)
        length_sqrd = direction.dot(direction)
        covector = direction / length_sqrd
        normal = np.asarray([-direction[1], direction[0]]) / sqrt(length_sqrd)

    Since ``covector`` and ``normal`` depend only on the endpoints, they
    can be computed when defining the line and then reused.

    Args:
        pos: Center of the ball.
        vel: Velocity of the ball.
        radius: Radius of the ball.
        line_start: Starting point of the segment.
        line_end: Endpoint of the segment.
        line_normal: A unit vector that is perpendicular to the line.
        line_covector: The vector in the direction of the line, but with
            a euclidean length of ``1 / length``, where ``length`` is
            the distance of ``line_start`` and ``line_end`` (the length
            of the segment).

    Returns:
        A tuple ``(t, args)``, where ``t`` is the collision time (a
        float) and ``args`` is a tuple of arguments that can be used
        when resolving a collision. The time is infinite if there is no
        collision now or in the future. The ``args`` tuple contains two
        entries: ``line_normal.dot(vel)`` (the component of the ball's
        velocity perpendicular to the line, is negative if the ball is
        moving against the direction of ``line_normal``) and ``u`` (the
        line parameter for the impact location). If the time of impact
        is finite, then ``line_start + u * line_end`` is the position
        where the ball will touch the line (and ``0 <= u <= 1``). If
        ``u`` is an integer, then the ball collides with the endpoint at
        ``line_start`` (when ``u == 0``) or the endpoint at ``line_end``
        (when ``u == 1``). Use this information to resolve the collision
        accordingly.

    Notes:
        A ball-segment intersection problem is equivalent to a
        particle-capsule intersection problem (via Minkowski addition).
    """
    # Compute the relative position between the ball and the line
    dpos = np.subtract(pos, line_start)
    dpos_normal = line_normal.dot(dpos)

    # Keep track of absolute errors in floating point computations
    dpos_x_err = max(REL_TOL * fabs(pos[0]), ABS_TOL) + ulp(line_start[0]) / 2
    dpos_y_err = max(REL_TOL * fabs(pos[1]), ABS_TOL) + ulp(line_start[1]) / 2
    dpos_normal_err = (
        fabs(line_normal[0]) * dpos_x_err
        + ulp(line_normal[0]) / 2 * fabs(dpos[0])
        + fabs(line_normal[1]) * dpos_y_err
        + ulp(line_normal[1]) / 2 * fabs(dpos[1])
    )
    gap_err = dpos_normal_err + ulp(radius) / 2  # error of dpos_normal +- radius

    if dpos_normal - radius > gap_err:
        # Ball is on the side facing line_normal
        return toi_args_ball_segment_onesided(
            pos, vel, radius, line_start, line_end, line_normal, line_covector
        )
    elif dpos_normal + radius < -gap_err:
        # Ball is on the side opposite of where line_normal is pointing
        t, (vel_normal, u) = toi_args_ball_segment_onesided(
            pos, vel, radius, line_start, line_end, -line_normal, line_covector
        )
        return t, (-vel_normal, u)  # reverse vel_normal, because we used -line_normal
    else:
        # Ball overlaps the infinite line, does it collide with the
        # endpoints of the segment?
        dpos_line = line_covector.dot(dpos)

        # The sign of dpos_line indicates if the ball is behind line_start (< 0) or
        # ahead of line_end (> 0)
        if dpos_line < 0.0:
            t = toi_ball_point(pos, vel, radius, line_start)
            return t, (line_normal.dot(vel), 0)
        elif dpos_line > 1.0:
            t = toi_ball_point(pos, vel, radius, line_end)
            return t, (line_normal.dot(vel), 1)
        else:
            # Ball overlaps the segment
            return INF, (line_normal.dot(vel), None)


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

    pos_dot_vel = dpos.dot(dvel)

    # Keep track of absolute errors in floating point computations
    pos_dot_vel_err = (
        fabs(dpos[0]) * (ulp(vel1[0]) + ulp(vel2[0])) / 2
        + max(REL_TOL * (fabs(pos1[0]) + fabs(pos2[0])), ABS_TOL) * fabs(dvel[0])
        + fabs(dpos[1]) * (ulp(vel1[1]) + ulp(vel2[1])) / 2
        + max(REL_TOL * (fabs(pos1[1]) + fabs(pos2[1])), ABS_TOL) * fabs(dvel[1])
    )

    # Make sure that impulse will be positive
    if pos_dot_vel > pos_dot_vel_err:
        msg = f"Balls are not moving towards each other: pos * vel = {pos_dot_vel} > 0"
        raise ValueError(msg)

    # Compute the change in velocity (mass * impuls)
    impulse = 2 * (pos_dot_vel * dpos) / ((mass1 + mass2) * dpos.dot(dpos))
    return vel1 - mass2 * impulse, vel2 + mass1 * impulse
