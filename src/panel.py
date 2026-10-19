if __package__:
    from .config import DUST_GROWTH, MAX_DUST, NUM_PANELS, PANEL_ALERT_THRESHOLD
else:
    from config import DUST_GROWTH, MAX_DUST, NUM_PANELS, PANEL_ALERT_THRESHOLD


PANELS = [{"dust": 0.0, "alert": False} for _ in range(NUM_PANELS)]


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
