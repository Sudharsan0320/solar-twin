if __package__:
    from .config import (
        DUST_GROWTH,
        MAX_DUST,
        NUM_PANELS,
        NUM_ROWS,
        PANEL_ALERT_THRESHOLD,
        PANEL_SIZE,
        PANEL_WIDTH_M,
        ROW_GAP_M,
        ROW_PITCH,
    )
else:
    from config import (
        DUST_GROWTH,
        MAX_DUST,
        NUM_PANELS,
        NUM_ROWS,
        PANEL_ALERT_THRESHOLD,
        PANEL_SIZE,
        PANEL_WIDTH_M,
        ROW_GAP_M,
        ROW_PITCH,
    )


PANELS = [
    {"dust": 0.0, "alert": False, "row": row}
    for row in range(NUM_ROWS)
    for _ in range(NUM_PANELS)
]


def panel_at(x, y):
    row = int(y // ROW_PITCH)
    row_offset = y % ROW_PITCH
    if (
        row < 0
        or row >= NUM_ROWS
        or PANEL_SIZE[0] < row_offset < PANEL_SIZE[0] + ROW_GAP_M
    ):
        return None

    col = int(x // PANEL_WIDTH_M)
    if col < 0 or col >= NUM_PANELS:
        return None

    return row * NUM_PANELS + col


def tick():
    for panel in PANELS:
        panel["dust"] = min(panel["dust"] + DUST_GROWTH, MAX_DUST)
        if panel["dust"] >= PANEL_ALERT_THRESHOLD:
            panel["alert"] = True


def get_efficiency(panel_index):
    return 1 - PANELS[panel_index]["dust"]


def clean(panel_index, amount):
    PANELS[panel_index]["dust"] = max(PANELS[panel_index]["dust"] - amount, 0.0)
    if PANELS[panel_index]["dust"] < PANEL_ALERT_THRESHOLD:
        PANELS[panel_index]["alert"] = False
