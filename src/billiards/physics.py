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
    # c = (dist_sqrd - (radius1 + radius2) ** 2) / 4. Depending on the value of
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
    """
    # switch to coordinate system of ball 1
    pos_diff = np.subtract(pos2, pos1)
    vel_diff = np.subtract(vel2, vel1)

    pos_dot_vel = pos_diff.dot(vel_diff)
    assert pos_dot_vel < 0  # check that colliding balls move towards each other

    impulse = 2 * (pos_dot_vel * pos_diff) / ((mass1 + mass2) * pos_diff.dot(pos_diff))
    return vel1 + mass2 * impulse, vel2 - mass1 * impulse
