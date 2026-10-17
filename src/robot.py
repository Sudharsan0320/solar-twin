if __package__:
    from .config import (
        BATTERY_CLEANING_DRAIN_PER_TICK,
        BATTERY_IDLE_DRAIN_PER_TICK,
        BATTERY_MOVING_DRAIN_PER_TICK,
        BATTERY_REFILL_PER_TICK,
        BRUSH_MAINTENANCE_THRESHOLD_PCT,
        BRUSH_WEAR_PER_TICK,
        CLEANING_RATE_PER_TICK,
        DRIVE_SPEED,
        PANEL_WIDTH_M,
        WATER_USE_PER_TICK,
    )
    from . import panel
else:
    from config import (
        BATTERY_CLEANING_DRAIN_PER_TICK,
        BATTERY_IDLE_DRAIN_PER_TICK,
        BATTERY_MOVING_DRAIN_PER_TICK,
        BATTERY_REFILL_PER_TICK,
        BRUSH_MAINTENANCE_THRESHOLD_PCT,
        BRUSH_WEAR_PER_TICK,
        CLEANING_RATE_PER_TICK,
        DRIVE_SPEED,
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
}


def tick():
    if ROBOT["state"] == "CHARGING":
        ROBOT["battery_pct"] = min(
            ROBOT["battery_pct"] + BATTERY_REFILL_PER_TICK,
            100.0,
        )
        if ROBOT["battery_pct"] >= 100.0:
            ROBOT["state"] = "IDLE"
    else:
        if ROBOT["state"] == "MOVING":
            drain_rate = BATTERY_MOVING_DRAIN_PER_TICK
        elif ROBOT["state"] == "CLEANING":
            drain_rate = BATTERY_CLEANING_DRAIN_PER_TICK
        else:
            # Unknown states such as FAULT use the safer idle trickle rate.
            drain_rate = BATTERY_IDLE_DRAIN_PER_TICK
        ROBOT["battery_pct"] = max(
            ROBOT["battery_pct"] - drain_rate,
            0.0,
        )
        if ROBOT["battery_pct"] < 20.0:
            ROBOT["state"] = "CHARGING"

    if ROBOT["state"] == "MOVING":
        ROBOT["x"] += DRIVE_SPEED

    if ROBOT["state"] == "CLEANING":
        panel_index = min(
            int(ROBOT["x"] // PANEL_WIDTH_M),
            len(panel.PANELS) - 1,
        )
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
        if (
            ROBOT["brush_health_pct"] < BRUSH_MAINTENANCE_THRESHOLD_PCT
            and ROBOT["fault_code"] is None
        ):
            ROBOT["fault_code"] = "BRUSH_WORN"