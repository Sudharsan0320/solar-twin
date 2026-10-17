from datetime import datetime, timedelta

if __package__:
    from .config import PANEL_WIDTH_M
    from . import panel, robot
else:
    from config import PANEL_WIDTH_M
    import panel
    import robot


ROBOT_ID = "twin-01"
SIMULATION_START = datetime(2026, 1, 1)


def emit(tick_number):
    robot_state = robot.ROBOT
    panel_index = min(
        max(int(robot_state["x"] // PANEL_WIDTH_M), 0),
        len(panel.PANELS) - 1,
    )
    timestamp = SIMULATION_START + timedelta(seconds=tick_number)

    return {
        "robot_id": ROBOT_ID,
        "ts": timestamp.isoformat(),
        "state": robot_state["state"],
        "x": robot_state["x"],
        "y": robot_state["y"],
        "heading": robot_state["heading"],
        "battery_pct": robot_state["battery_pct"],
        "water_tank_pct": robot_state["water_tank_pct"],
        "brush_health_pct": robot_state["brush_health_pct"],
        "panel_id": panel_index,
        "fault_code": robot_state["fault_code"],
    }
