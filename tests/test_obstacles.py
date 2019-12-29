#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pytest

from billiards.obstacles import Disk


def test_disk():
    d = Disk((0, 0), 1)

    assert d.calc_toi((-10, 0), (1, 0), 1) == 8.0
    assert tuple(d.collide((-2, 0), (1, 0), 1)) == (-1, 0)


if __name__ == "__main__":
    pytest.main()
