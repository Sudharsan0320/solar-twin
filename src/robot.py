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
        PANEL_WIDTH_M,
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
        PANEL_WIDTH_M,
        WATER_USE_PER_TICK,
    )
    import panel


ROBOT = {
    "x": 0.0,
    "y": 0.0,
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
}


def nearest_station(x):
    # Station routing uses direct distance, without wrapping around the array.
    return min(
        range(len(CHARGING_STATIONS)),
        key=lambda index: abs(x - CHARGING_STATIONS[index][0]),
    )


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
        and state not in ("TO_CHARGER", "CHARGING", "TO_PANEL")
    ):
        ROBOT["resume_state"] = "MOVING" if state == "IDLE" else state
        ROBOT["target_station"] = nearest_station(ROBOT["x"])
        ROBOT["state"] = "TO_CHARGER"
        return

    if state == "TO_CHARGER":
        station_x = CHARGING_STATIONS[ROBOT["target_station"]][0]
        distance = station_x - ROBOT["x"]
        if abs(distance) <= DRIVE_SPEED:
            ROBOT["x"] = station_x
            ROBOT["state"] = "CHARGING"
        else:
            ROBOT["x"] += DRIVE_SPEED if distance > 0 else -DRIVE_SPEED
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
                key=lambda panel_index: abs(
                    ROBOT["x"]
                    - (panel_index * PANEL_WIDTH_M + PANEL_WIDTH_M / 2)
                ),
            )
            ROBOT["target_panel"] = target_panel
            ROBOT["state"] = "TO_PANEL"
            return

        ROBOT["x"] += DRIVE_SPEED
        if ROBOT["x"] >= ARRAY_LENGTH_M:
            ROBOT["x"] -= ARRAY_LENGTH_M
        ROBOT["distance_since_clean_m"] += DRIVE_SPEED
        panel_index = int(ROBOT["x"] // PANEL_WIDTH_M)
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
        panel_center = (
            ROBOT["target_panel"] * PANEL_WIDTH_M + PANEL_WIDTH_M / 2
        )
        distance = panel_center - ROBOT["x"]
        if abs(distance) <= DRIVE_SPEED:
            ROBOT["x"] = panel_center
            panel.PANELS[ROBOT["target_panel"]]["alert"] = False
            ROBOT["cleaning_trigger"] = "dispatched"
            ROBOT["distance_since_clean_m"] = 0.0
            ROBOT["cleaning_ticks_remaining"] = CLEANING_DURATION_TICKS
            ROBOT["state"] = "CLEANING"
            ROBOT["target_panel"] = None
        else:
            ROBOT["x"] += DRIVE_SPEED if distance > 0 else -DRIVE_SPEED
        return

    if state == "CLEANING":
        panel_index = int(ROBOT["x"] // PANEL_WIDTH_M)
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