#!/usr/bin/env python3
import pytest

import billiards


@pytest.fixture
def create_newtons_cradle():
    def _create_newtons_cradle(num_balls=5, with_walls=True):
        if with_walls:
            left = -4
            right = 2 * num_balls + 3
            obs = [
                billiards.InfiniteWall((left, -2), (left, 2), "right"),
                billiards.InfiniteWall((right, -2), (right, 2)),
            ]
        else:
            obs = []

        bld = billiards.Billiard(obstacles=obs)

        bld.add_ball((-3, 0), (1, 0), 1)
        for i in range(1, num_balls):
            bld.add_ball((2 * i, 0), (0, 0), radius=1)

        return bld

    return _create_newtons_cradle
