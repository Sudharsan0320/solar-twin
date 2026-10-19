from datetime import datetime, timedelta

if __package__:
    from . import panel, robot
else:
    import panel
    import robot


ROBOT_ID = "twin-01"
SIMULATION_START = datetime(2026, 1, 1)


def set_robot_id(new_id):
    global ROBOT_ID
    ROBOT_ID = new_id


def emit(tick_number):
    robot_state = robot.ROBOT
    panel_index = panel.panel_at(robot_state["x"], robot_state["y"])
    panel_dust = (
        panel.PANELS[panel_index]["dust"] if panel_index is not None else 0.0
    )
    timestamp = SIMULATION_START + timedelta(seconds=tick_number)

    return {
        "robot_id": ROBOT_ID,
        "ts": timestamp.isoformat(),
        "state": robot_state["state"],
        "station_id": (
            robot_state["target_station"]
            if robot_state["target_station"] is not None
            else -1
        ),
        "target_panel": (
            robot_state["target_panel"]
            if robot_state["target_panel"] is not None
            else -1
        ),
        "row": robot_state["row"],
        "x": robot_state["x"],
        "y": robot_state["y"],
        "heading": robot_state["heading"],
        "battery_pct": robot_state["battery_pct"],
        "water_tank_pct": robot_state["water_tank_pct"],
        "brush_health_pct": robot_state["brush_health_pct"],
        "panel_id": panel_index if panel_index is not None else -1,
        "panel_dust": panel_dust,
        "fault_code": robot_state["fault_code"],
        "cleaning_trigger": robot_state["cleaning_trigger"],
    }
