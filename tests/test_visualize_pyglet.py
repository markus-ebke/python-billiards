#!/usr/bin/env python3
import numpy as np
import pytest
from pytest import approx

# import billiards

try:
    import pyglet
except ImportError:
    has_pyglet = False
else:
    has_pyglet = True
    pyglet.options["headless"] = True  # run the tests without showing a window

with_pyglet = pytest.mark.skipif(not has_pyglet, reason="requires pyglet")

if not has_pyglet:
    with pytest.raises(ImportError) as exc_info:
        import billiards.visualize_pyglet as visualize
    assert exc_info.value.args[0] == "No module named 'pyglet'"
else:
    import billiards.visualize_pyglet as visualize


@with_pyglet
def test_model_circle():
    r, n = 5.0, 16
    vertices, indices = visualize.model_circle_line(r, segments=n)

    assert isinstance(vertices, np.ndarray)
    assert vertices.shape == (n, 2)
    assert np.hypot(vertices[:, 0], vertices[:, 1]) == approx(r)

    assert len(indices) == 2 * n


if __name__ == "__main__":
    pytest.main()
