# -*- coding: utf-8 -*-
"""This module contains functions for collision detection and handling."""
from math import sqrt

import numpy as np

INF = float("inf")


def time_of_impact(pos1, vel1, radius1, pos2, vel2, radius2, t_eps=1e-10):
    """Calculate for two moving balls the time until impact.

    Overlapping balls are not counted as a collision (because the impact
    already occured). But due to rounding errors an actual impact might be
    missed, use a larger t_eps to correct for that.

    Args:
        pos1: Center of the first ball.
        vel1: Velocity of the first ball.
        radius1: Radius of the first ball.
        pos2: Center of the second ball.
        vel2: Velocity of the second ball.
        radius2: Radius of the second ball.
        t_eps (optional): Correction for rounding errors, default: 1e-10.

    Return:
        Time until impact, is infinite if there is no impact.

    """
    # switch to coordinate system of ball 1
    pos_diff = np.subtract(pos2, pos1)
    vel_diff = np.subtract(vel2, vel1)

    pos_dot_vel = np.dot(pos_diff, vel_diff)
    if pos_dot_vel >= 0:
        # balls are moving apart, no impact
        return INF

    pos_sqrd = np.dot(pos_diff, pos_diff)
    vel_sqrd = np.dot(vel_diff, vel_diff)  # note: vel_sqrd != 0
    assert vel_sqrd > 0, vel_sqrd

    # time of impact is given as the solution of the quadratic equation
    # t^2 + b t + c = 0 with b and c below
    b = pos_dot_vel / vel_sqrd  # note: b < 0 because pos_dot_vel < 0
    assert b < 0, b
    c = (pos_sqrd - (radius1 + radius2) ** 2) / vel_sqrd

    discriminant = b ** 2 - c
    if discriminant <= 0:
        # the balls miss or slide past each other
        return INF

    # when writing the solution of the quadratic equation use that
    # c = t1 t2 (prevents rounding errors)
    t1 = -b + sqrt(discriminant)  # note: t1 > 0
    assert t1 > 0, (t1, b, c, sqrt(discriminant))
    t2 = c / t1

    if t2 < -t_eps:
        # If t2 is negative, then the balls overlap. This doesn't count as an
        # impact, but if t2 is close to zero, then a collision might have
        # happened and we miss it just because of rounding errors
        return INF

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
