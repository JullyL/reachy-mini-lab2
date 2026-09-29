from reachy_mini import ReachyMini
from reachy_mini.utils import create_head_pose


with ReachyMini() as mini:
    mini.enable_motors()

    print("Connected, nodding head and moving antennas...")

    # Gently nod the head, then return to the neutral pose.
    mini.goto_target(
        head=create_head_pose(pitch=10, degrees=True),
        antennas=[0.3, -0.3],
        duration=1.0
    )

    mini.goto_target(
        head=create_head_pose(pitch=-10, degrees=True),
        antennas=[-0.3, 0.3],
        duration=1.0
    )
    mini.goto_target(
        head=create_head_pose(),
        antennas=[0.0, 0.0],
        duration=1.0
    )

    print("Done")
