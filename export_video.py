import matplotlib

matplotlib.use("Agg")

import math

import matplotlib.pyplot as plt
from matplotlib import animation, patches

from src import config, panel, robot
from src.config import (
    ARRAY_LENGTH_M,
    NUM_PANELS,
    NUM_ROWS,
    ROW_PITCH,
    ROBOT_FOOTPRINT,
)


figure, axes = plt.subplots()
axes.set_xlim(0, ARRAY_LENGTH_M)
axes.set_ylim(-0.2, NUM_ROWS * ROW_PITCH)
axes.set_aspect("equal")
robot_status = axes.text(
    0.01,
    1.01,
    "",
    ha="left",
    va="bottom",
    fontsize=8,
    transform=axes.transAxes,
)

panel_rectangles = []
for row in range(NUM_ROWS):
    for col in range(NUM_PANELS):
        rectangle = patches.Rectangle(
            (col * config.PANEL_WIDTH_M, row * ROW_PITCH),
            config.PANEL_WIDTH_M,
            config.PANEL_SIZE[0],
        )
        axes.add_patch(rectangle)
        rectangle.set_edgecolor("black")
        panel_rectangles.append(rectangle)

for rectangle, panel_state in zip(panel_rectangles, panel.PANELS):
    grayscale = 1 - panel_state["dust"]
    rectangle.set_facecolor((grayscale, grayscale, grayscale))

chassis_width, chassis_height = ROBOT_FOOTPRINT[:2]
wheel_radius = min(chassis_width, chassis_height) * 0.15
wheel_offsets = [
    (x_offset, y_offset)
    for x_offset in (-chassis_width / 2, chassis_width / 2)
    for y_offset in (-chassis_height / 2, chassis_height / 2)
]
wheel_centers = [
    (robot.ROBOT["x"] + x_offset, robot.ROBOT["y"] + y_offset)
    for x_offset, y_offset in wheel_offsets
]
wheels = [patches.Circle(center, wheel_radius, color="#263238") for center in wheel_centers]

chassis = patches.Rectangle(
    (robot.ROBOT["x"] - chassis_width / 2, robot.ROBOT["y"] - chassis_height / 2),
    chassis_width,
    chassis_height,
    facecolor="#4682b4",
    edgecolor="black",
)
axes.add_patch(chassis)
heading_arrow = patches.Polygon(
    [
        (robot.ROBOT["x"] + chassis_width / 2, robot.ROBOT["y"]),
        (robot.ROBOT["x"] + chassis_width / 2 - 0.1, robot.ROBOT["y"] + 0.06),
        (robot.ROBOT["x"] + chassis_width / 2 - 0.1, robot.ROBOT["y"] - 0.06),
    ],
    closed=True,
    facecolor="#ffeb3b",
    edgecolor="black",
)
axes.add_patch(heading_arrow)
for wheel in wheels:
    axes.add_patch(wheel)

brush_angle = 0.0
brush_length = 0.12
brush_lines = [
    axes.plot(
        [robot.ROBOT["x"] + x_offset, robot.ROBOT["x"] + x_offset],
        [
            robot.ROBOT["y"] - brush_length / 2,
            robot.ROBOT["y"] + brush_length / 2,
        ],
        color="#1565c0",
        linewidth=3,
    )[0]
    for x_offset in (-chassis_width / 2, chassis_width / 2)
]
spray_offsets = [
    (0.2, -0.08),
    (0.23, -0.055),
    (0.26, -0.025),
    (0.29, 0.0),
    (0.32, 0.025),
    (0.35, 0.055),
    (0.38, 0.08),
    (0.4, 0.0),
]
spray_droplets = [
    patches.Circle((0, 0), 0.015, facecolor="#29b6f6", edgecolor="none")
    for _ in spray_offsets
]
for droplet in spray_droplets:
    droplet.set_visible(False)
    axes.add_patch(droplet)


def update(frame_number):
    global brush_angle

    for _ in range(30):
        panel.tick()
        robot.tick()

    for rectangle, panel_state in zip(panel_rectangles, panel.PANELS):
        grayscale = 1 - panel_state["dust"]
        rectangle.set_facecolor((grayscale, grayscale, grayscale))

    chassis.set_xy(
        (
            robot.ROBOT["x"] - chassis_width / 2,
            robot.ROBOT["y"] - chassis_height / 2,
        )
    )
    direction = 1 if robot.ROBOT["heading"] == 0.0 else -1
    heading_arrow.set_xy(
        [
            (robot.ROBOT["x"] + direction * chassis_width / 2, robot.ROBOT["y"]),
            (
                robot.ROBOT["x"] + direction * (chassis_width / 2 - 0.1),
                robot.ROBOT["y"] + 0.06,
            ),
            (
                robot.ROBOT["x"] + direction * (chassis_width / 2 - 0.1),
                robot.ROBOT["y"] - 0.06,
            ),
        ]
    )
    for wheel, (x_offset, y_offset) in zip(wheels, wheel_offsets):
        wheel.center = (
            robot.ROBOT["x"] + x_offset,
            robot.ROBOT["y"] + y_offset,
        )
    brush_centers = [
        (robot.ROBOT["x"] + x_offset, robot.ROBOT["y"])
        for x_offset in (-chassis_width / 2, chassis_width / 2)
    ]
    if robot.ROBOT["state"] == "CLEANING":
        brush_angle += 0.6
    brush_dx = brush_length / 2 * math.sin(brush_angle)
    brush_dy = brush_length / 2 * math.cos(brush_angle)
    for brush_line, (center_x, center_y) in zip(brush_lines, brush_centers):
        brush_line.set_data(
            [center_x - brush_dx, center_x + brush_dx],
            [center_y - brush_dy, center_y + brush_dy],
        )
    spray_active = (
        robot.ROBOT["state"] == "CLEANING"
        and robot.ROBOT["water_tank_pct"] > 0
    )
    for droplet, (x_offset, y_offset) in zip(spray_droplets, spray_offsets):
        droplet.center = (
            robot.ROBOT["x"] + x_offset,
            robot.ROBOT["y"] + y_offset,
        )
        droplet.set_visible(spray_active)
    robot_status.set_text(
        f"{robot.ROBOT['state']} | "
        f"batt {robot.ROBOT['battery_pct']:.1f}% | "
        f"brush {robot.ROBOT['brush_health_pct']:.1f}% | "
        f"water {robot.ROBOT['water_tank_pct']:.1f}%"
    )
    return [
        *panel_rectangles,
        *wheels,
        chassis,
        heading_arrow,
        *brush_lines,
        *spray_droplets,
        robot_status,
    ]


ani = animation.FuncAnimation(
    figure,
    update,
    frames=120,
    interval=200,
    cache_frame_data=False,
)
ani.save("twin_demo.mp4", writer="ffmpeg", fps=10)
