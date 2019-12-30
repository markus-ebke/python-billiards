#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import pytest
from pytest import approx

from billiards.obstacles import Disk, circle_model


def test_circle_model():
    r, n = 5.0, 16
    vertices, indices = circle_model(r, num_points=n)

    assert isinstance(vertices, np.ndarray)
    assert vertices.shape == (n, 2)
    assert np.hypot(vertices[:, 0], vertices[:, 1]) == approx(r)

    assert len(indices) == 2 * n


def test_disk():
    d = Disk((0, 0), 1)

    assert d.calc_toi((-10, 0), (1, 0), 1) == 8.0
    assert tuple(d.collide((-2, 0), (1, 0), 1)) == (-1, 0)


if __name__ == "__main__":
    pytest.main()
