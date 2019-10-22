# -*- coding: utf-8 -*-
try:
    from matplotlib.patches import Circle
    from matplotlib.collections import PatchCollection
    import matplotlib.pyplot as plt
except ImportError:
    print("matplotlib import failed, cannot use 'plot'")


def plot(sim):
    # simplify variables
    pos = sim.balls_position
    vel = sim.balls_velocity
    radii = sim.balls_radius

    # setup figure
    fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
    plt.axis("equal")

    # draw balls as circles
    patches = [Circle(p, radius=r) for p, r in zip(pos, radii) if r > 0]
    balls = PatchCollection(patches, edgecolor="black", lw=1, zorder=0)
    ax.add_collection(balls)

    # indicate positions via scatter plot
    plt.scatter(pos[:, 0], pos[:, 1], color="black")

    # indicate velocity with arrows, will also mark non-moving balls
    plt.quiver(pos[:, 0], pos[:, 1], vel[:, 0], vel[:, 1], color="black")

    plt.tight_layout()
    plt.show()
