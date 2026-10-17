import matplotlib.pyplot as plt
from matplotlib import animation, patches

from src import config, panel, robot
from src.config import ARRAY_LENGTH_M, NUM_PANELS


figure, axes = plt.subplots()
axes.set_xlim(0, ARRAY_LENGTH_M)
axes.set_ylim(-0.2, config.PANEL_SIZE[0] + 0.2)
axes.set_aspect("equal")

panel_rectangles = []
for panel_index in range(NUM_PANELS):
    rectangle = patches.Rectangle(
        (panel_index * config.PANEL_WIDTH_M, 0),
        config.PANEL_WIDTH_M,
        config.PANEL_SIZE[0],
    )
    axes.add_patch(rectangle)
    rectangle.set_edgecolor("black")
    panel_rectangles.append(rectangle)

for rectangle, panel_state in zip(panel_rectangles, panel.PANELS):
    grayscale = 1 - panel_state["dust"]
    rectangle.set_facecolor((grayscale, grayscale, grayscale))

robot_dot, = axes.plot(robot.ROBOT["x"], robot.ROBOT["y"], "ro")


def update(frame_number):
    for _ in range(30):
        panel.tick()
        robot.tick()

    for rectangle, panel_state in zip(panel_rectangles, panel.PANELS):
        grayscale = 1 - panel_state["dust"]
        rectangle.set_facecolor((grayscale, grayscale, grayscale))

    robot_dot.set_data([robot.ROBOT["x"]], [robot.ROBOT["y"]])
    return [*panel_rectangles, robot_dot]


ani = animation.FuncAnimation(
    figure,
    update,
    interval=200,
    cache_frame_data=False,
)
plt.show()
