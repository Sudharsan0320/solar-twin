from math import hypot

if __package__:
    from .config import (
        ARRAY_LENGTH_M,
        BATTERY_CLEANING_DRAIN_PER_TICK,
        BATTERY_IDLE_DRAIN_PER_TICK,
        BATTERY_LOW_PCT,
        BATTERY_MOVING_DRAIN_PER_TICK,
        BATTERY_REFILL_PER_TICK,
        BRUSH_MAINTENANCE_THRESHOLD_PCT,
        BRUSH_WEAR_PER_TICK,
        CHARGING_STATIONS,
        CLEANING_DURATION_TICKS,
        CLEANING_RATE_PER_TICK,
        CLEANING_TRIGGER_DISTANCE_M,
        DIRT_THRESHOLD,
        DRIVE_SPEED,
        MAINTENANCE_DURATION_TICKS,
        NUM_ROWS,
        NUM_PANELS,
        PANEL_SIZE,
        PANEL_WIDTH_M,
        ROW_PITCH,
        WATER_USE_PER_TICK,
    )
    from . import panel
else:
    from config import (
        ARRAY_LENGTH_M,
        BATTERY_CLEANING_DRAIN_PER_TICK,
        BATTERY_IDLE_DRAIN_PER_TICK,
        BATTERY_LOW_PCT,
        BATTERY_MOVING_DRAIN_PER_TICK,
        BATTERY_REFILL_PER_TICK,
        BRUSH_MAINTENANCE_THRESHOLD_PCT,
        BRUSH_WEAR_PER_TICK,
        CHARGING_STATIONS,
        CLEANING_DURATION_TICKS,
        CLEANING_RATE_PER_TICK,
        CLEANING_TRIGGER_DISTANCE_M,
        DIRT_THRESHOLD,
        DRIVE_SPEED,
        MAINTENANCE_DURATION_TICKS,
        NUM_ROWS,
        NUM_PANELS,
        PANEL_SIZE,
        PANEL_WIDTH_M,
        ROW_PITCH,
        WATER_USE_PER_TICK,
    )
    import panel


ROBOT = {
    "x": 0.0,
    "y": 0.0,
    "row": 0,
    "heading": 0.0,
    "battery_pct": 100.0,
    "water_tank_pct": 100.0,
    "brush_health_pct": 100.0,
    "fault_code": None,
    "state": "IDLE",
    "distance_since_clean_m": 0.0,
    "cleaning_ticks_remaining": 0,
    "cleaning_trigger": "none",
    "maintenance_ticks_remaining": 0,
    "resume_state": None,
    "target_station": None,
    "target_panel": None,
    "target_row": None,
}


def nearest_station(x, y):
    return min(
        range(len(CHARGING_STATIONS)),
        key=lambda index: hypot(
            x - CHARGING_STATIONS[index][0],
            y - CHARGING_STATIONS[index][1],
        ),
    )


def panel_center(panel_index):
    return (
        panel_index % NUM_PANELS * PANEL_WIDTH_M + PANEL_WIDTH_M / 2,
        panel.PANELS[panel_index]["row"] * ROW_PITCH + PANEL_SIZE[0] / 2,
    )


def distance_to_panel(panel_index):
    target_x, target_y = panel_center(panel_index)
    return hypot(ROBOT["x"] - target_x, ROBOT["y"] - target_y)


def tick():
    state = ROBOT["state"]
    if state == "CHARGING":
        ROBOT["battery_pct"] = min(
            ROBOT["battery_pct"] + BATTERY_REFILL_PER_TICK,
            100.0,
        )
        if ROBOT["battery_pct"] >= 100.0:
            ROBOT["water_tank_pct"] = 100.0
            ROBOT["state"] = ROBOT["resume_state"] or "MOVING"
            ROBOT["resume_state"] = None
            ROBOT["target_station"] = None
        return

    if state == "MOVING":
        drain_rate = BATTERY_MOVING_DRAIN_PER_TICK
    elif state == "TO_CHARGER":
        drain_rate = BATTERY_MOVING_DRAIN_PER_TICK
    elif state == "TO_PANEL":
        drain_rate = BATTERY_MOVING_DRAIN_PER_TICK
    elif state == "TRANSPORT":
        drain_rate = BATTERY_MOVING_DRAIN_PER_TICK
    elif state == "CLEANING":
        drain_rate = BATTERY_CLEANING_DRAIN_PER_TICK
    else:
        # Unknown states such as FAULT use the safer idle trickle rate.
        drain_rate = BATTERY_IDLE_DRAIN_PER_TICK
    ROBOT["battery_pct"] = max(
        ROBOT["battery_pct"] - drain_rate,
        0.0,
    )
    if (
        ROBOT["battery_pct"] < BATTERY_LOW_PCT
        and state not in ("TO_CHARGER", "CHARGING", "TO_PANEL", "TRANSPORT")
    ):
        ROBOT["resume_state"] = "MOVING" if state == "IDLE" else state
        ROBOT["target_station"] = nearest_station(ROBOT["x"], ROBOT["y"])
        ROBOT["state"] = "TO_CHARGER"
        return

    if state == "TO_CHARGER":
        station_x, station_y = CHARGING_STATIONS[ROBOT["target_station"]]
        dx = station_x - ROBOT["x"]
        dy = station_y - ROBOT["y"]
        # Navigate x-first, then y, to keep routing deterministic.
        if abs(dx) > DRIVE_SPEED:
            ROBOT["x"] += DRIVE_SPEED if dx > 0 else -DRIVE_SPEED
        elif abs(dy) > DRIVE_SPEED:
            ROBOT["y"] += DRIVE_SPEED if dy > 0 else -DRIVE_SPEED
        else:
            ROBOT["x"] = station_x
            ROBOT["y"] = station_y
            ROBOT["row"] = 0
            ROBOT["state"] = "CHARGING"
        return

    if state == "MAINTENANCE":
        ROBOT["maintenance_ticks_remaining"] -= 1
        if ROBOT["maintenance_ticks_remaining"] <= 0:
            ROBOT["maintenance_ticks_remaining"] = 0
            ROBOT["brush_health_pct"] = 100.0
            ROBOT["fault_code"] = None
            ROBOT["state"] = ROBOT["resume_state"] or "MOVING"
            ROBOT["resume_state"] = None
        return

    if state == "IDLE":
        ROBOT["state"] = "MOVING"
        return

    if state == "MOVING":
        alerted_panels = [
            panel_index
            for panel_index, panel_state in enumerate(panel.PANELS)
            if panel_state["alert"]
        ]
        if alerted_panels:
            target_panel = min(
                alerted_panels,
                key=distance_to_panel,
            )
            ROBOT["target_panel"] = target_panel
            ROBOT["state"] = "TO_PANEL"
            return

        direction = 1 if ROBOT["heading"] == 0.0 else -1
        ROBOT["x"] += direction * DRIVE_SPEED
        if direction > 0 and ROBOT["x"] >= ARRAY_LENGTH_M:
            ROBOT["x"] = ARRAY_LENGTH_M - DRIVE_SPEED
            ROBOT["target_row"] = (
                ROBOT["row"] + 1
                if ROBOT["row"] + 1 < NUM_ROWS
                else ROBOT["row"] - 1
            )
            ROBOT["state"] = "TRANSPORT"
            return
        if direction < 0 and ROBOT["x"] <= 0:
            ROBOT["x"] = 0
            ROBOT["target_row"] = (
                ROBOT["row"] - 1 if ROBOT["row"] > 0 else ROBOT["row"] + 1
            )
            ROBOT["state"] = "TRANSPORT"
            return

        ROBOT["distance_since_clean_m"] += DRIVE_SPEED
        panel_index = panel.panel_at(ROBOT["x"], ROBOT["y"])
        if panel_index is None:
            return
        if panel.PANELS[panel_index]["dust"] >= DIRT_THRESHOLD:
            ROBOT["cleaning_trigger"] = "dirt"
        elif ROBOT["distance_since_clean_m"] >= CLEANING_TRIGGER_DISTANCE_M:
            ROBOT["cleaning_trigger"] = "distance"
        else:
            return

        ROBOT["distance_since_clean_m"] = 0.0
        ROBOT["cleaning_ticks_remaining"] = CLEANING_DURATION_TICKS
        ROBOT["state"] = "CLEANING"
        return

    if state == "TO_PANEL":
        target_state = panel.PANELS[ROBOT["target_panel"]]
        panel_center_x, panel_center_y = panel_center(ROBOT["target_panel"])
        dx = panel_center_x - ROBOT["x"]
        dy = panel_center_y - ROBOT["y"]
        # Navigate x-first, then y, to keep routing deterministic.
        if abs(dx) > DRIVE_SPEED:
            ROBOT["x"] += DRIVE_SPEED if dx > 0 else -DRIVE_SPEED
        elif abs(dy) > DRIVE_SPEED:
            ROBOT["y"] += DRIVE_SPEED if dy > 0 else -DRIVE_SPEED
        else:
            ROBOT["x"] = panel_center_x
            ROBOT["y"] = panel_center_y
            ROBOT["row"] = target_state["row"]
            panel.PANELS[ROBOT["target_panel"]]["alert"] = False
            ROBOT["cleaning_trigger"] = "dispatched"
            ROBOT["distance_since_clean_m"] = 0.0
            ROBOT["cleaning_ticks_remaining"] = CLEANING_DURATION_TICKS
            ROBOT["state"] = "CLEANING"
            ROBOT["target_panel"] = None
        return

    if state == "TRANSPORT":
        old_row = ROBOT["row"]
        target_y = ROBOT["target_row"] * ROW_PITCH
        dy = target_y - ROBOT["y"]
        if abs(dy) <= DRIVE_SPEED:
            ROBOT["y"] = target_y
            ROBOT["row"] = ROBOT["target_row"]
            ROBOT["heading"] = 180.0 if ROBOT["row"] > old_row else 0.0
            ROBOT["target_row"] = None
            ROBOT["state"] = "MOVING"
        else:
            ROBOT["y"] += DRIVE_SPEED if dy > 0 else -DRIVE_SPEED
        return

    if state == "CLEANING":
        panel_index = panel.panel_at(ROBOT["x"], ROBOT["y"])
        if panel_index is None:
            return
        cleaning_amount = CLEANING_RATE_PER_TICK * (
            ROBOT["brush_health_pct"] / 100
        )
        panel.clean(panel_index, cleaning_amount)
        ROBOT["brush_health_pct"] = max(
            ROBOT["brush_health_pct"] - BRUSH_WEAR_PER_TICK,
            0.0,
        )
        ROBOT["water_tank_pct"] = max(
            ROBOT["water_tank_pct"] - WATER_USE_PER_TICK,
            0.0,
        )
        ROBOT["cleaning_ticks_remaining"] -= 1
        if (
            ROBOT["brush_health_pct"] < BRUSH_MAINTENANCE_THRESHOLD_PCT
            and ROBOT["fault_code"] is None
        ):
            ROBOT["fault_code"] = "BRUSH_WORN"
        if ROBOT["cleaning_ticks_remaining"] <= 0:
            ROBOT["state"] = "MOVING"
            ROBOT["cleaning_trigger"] = "none"
        if (
            ROBOT["brush_health_pct"] < BRUSH_MAINTENANCE_THRESHOLD_PCT
            and ROBOT["state"] != "MAINTENANCE"
        ):
            ROBOT["resume_state"] = (
                "MOVING" if ROBOT["state"] == "IDLE" else ROBOT["state"]
            )
            ROBOT["state"] = "MAINTENANCE"
            ROBOT["maintenance_ticks_remaining"] = MAINTENANCE_DURATION_TICKS