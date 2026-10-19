import math

import matplotlib.pyplot as plt
from matplotlib import animation, patches

from src import config, panel, robot
from src.config import (
    ARRAY_LENGTH_M,
    CHARGING_STATIONS,
    NUM_PANELS,
    ROBOT_FOOTPRINT,
)


figure, axes = plt.subplots()
axes.set_xlim(0, ARRAY_LENGTH_M)
axes.set_ylim(-0.5, config.PANEL_SIZE[0] + 0.2)
axes.set_aspect("equal")
robot_status = axes.text(
    0.5,
    1.1,
    "",
    ha="left",
    va="bottom",
    fontsize=8,
)

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
    rectangle.set_edgecolor("red" if panel_state["alert"] else "black")
    rectangle.set_linewidth(2.5 if panel_state["alert"] else 1.0)

station_markers = []
station_labels = []
for station_index, (station_x, _) in enumerate(CHARGING_STATIONS):
    marker = patches.Rectangle(
        (station_x - 0.15, -0.3),
        0.3,
        0.3,
        facecolor="#d4a017",
        edgecolor="black",
    )
    axes.add_patch(marker)
    station_markers.append(marker)
    station_labels.append(
        axes.text(station_x, -0.34, f"S{station_index}", ha="center", va="top")
    )

station_route, = axes.plot(
    [],
    [],
    linestyle="--",
    color="gray",
)
station_route.set_visible(False)

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
        rectangle.set_edgecolor("red" if panel_state["alert"] else "black")
        rectangle.set_linewidth(2.5 if panel_state["alert"] else 1.0)

    chassis.set_xy(
        (
            robot.ROBOT["x"] - chassis_width / 2,
            robot.ROBOT["y"] - chassis_height / 2,
        )
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
            (robot.ROBOT["x"] + x_offset) % ARRAY_LENGTH_M,
            robot.ROBOT["y"] + y_offset,
        )
        droplet.set_visible(spray_active)
    station_id = robot.ROBOT["target_station"]
    station_route_active = (
        robot.ROBOT["state"] == "TO_CHARGER"
        and station_id is not None
    )
    panel_route_active = (
        robot.ROBOT["state"] == "TO_PANEL"
        and robot.ROBOT["target_panel"] is not None
    )
    if station_route_active:
        station_x = CHARGING_STATIONS[station_id][0]
        station_route.set_data(
            [robot.ROBOT["x"], station_x],
            [robot.ROBOT["y"], -0.15],
        )
    elif panel_route_active:
        panel_center_x = (
            robot.ROBOT["target_panel"] * config.PANEL_WIDTH_M
            + config.PANEL_WIDTH_M / 2
        )
        station_route.set_data(
            [robot.ROBOT["x"], panel_center_x],
            [robot.ROBOT["y"], -0.15],
        )
    station_route.set_visible(station_route_active or panel_route_active)
    robot_status.set_text(
        f"{robot.ROBOT['state']} | "
        f"batt {robot.ROBOT['battery_pct']:.1f}% | "
        f"brush {robot.ROBOT['brush_health_pct']:.1f}% | "
        f"water {robot.ROBOT['water_tank_pct']:.1f}%"
    )
    return [
        *panel_rectangles,
        *station_markers,
        *station_labels,
        station_route,
        *wheels,
        chassis,
        *brush_lines,
        *spray_droplets,
        robot_status,
    ]


ani = animation.FuncAnimation(
    figure,
    update,
    interval=200,
    cache_frame_data=False,
)
plt.show()
