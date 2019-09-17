Usage
=====

To use ``billiards`` in a project::

    import billiards

    sim = billiards.Simulation()
    idx = sim.add_ball((2, 0), (4, 0))

    sim.step(10)
    print(sim.balls_position[idx])

