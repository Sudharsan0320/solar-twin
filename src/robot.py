if __package__:
    from .config import (
        ARRAY_LENGTH_M,
        BATTERY_CLEANING_DRAIN_PER_TICK,
        BATTERY_IDLE_DRAIN_PER_TICK,
        BATTERY_MOVING_DRAIN_PER_TICK,
        BATTERY_REFILL_PER_TICK,
        BRUSH_MAINTENANCE_THRESHOLD_PCT,
        BRUSH_WEAR_PER_TICK,
        CLEANING_DURATION_TICKS,
        CLEANING_RATE_PER_TICK,
        CLEANING_TRIGGER_DISTANCE_M,
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
        BATTERY_MOVING_DRAIN_PER_TICK,
        BATTERY_REFILL_PER_TICK,
        BRUSH_MAINTENANCE_THRESHOLD_PCT,
        BRUSH_WEAR_PER_TICK,
        CLEANING_DURATION_TICKS,
        CLEANING_RATE_PER_TICK,
        CLEANING_TRIGGER_DISTANCE_M,
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
    "maintenance_ticks_remaining": 0,
    "resume_state": None,
}


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
        return

    if state == "MOVING":
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
    if ROBOT["battery_pct"] < 20.0:
        ROBOT["resume_state"] = "MOVING" if state == "IDLE" else state
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
        ROBOT["x"] += DRIVE_SPEED
        if ROBOT["x"] >= ARRAY_LENGTH_M:
            ROBOT["x"] -= ARRAY_LENGTH_M
        ROBOT["distance_since_clean_m"] += DRIVE_SPEED
        if ROBOT["distance_since_clean_m"] >= CLEANING_TRIGGER_DISTANCE_M:
            ROBOT["distance_since_clean_m"] = 0.0
            ROBOT["cleaning_ticks_remaining"] = CLEANING_DURATION_TICKS
            ROBOT["state"] = "CLEANING"
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
        if (
            ROBOT["brush_health_pct"] < BRUSH_MAINTENANCE_THRESHOLD_PCT
            and ROBOT["state"] != "MAINTENANCE"
        ):
            ROBOT["resume_state"] = (
                "MOVING" if ROBOT["state"] == "IDLE" else ROBOT["state"]
            )
            ROBOT["state"] = "MAINTENANCE"
            ROBOT["maintenance_ticks_remaining"] = MAINTENANCE_DURATION_TICKS