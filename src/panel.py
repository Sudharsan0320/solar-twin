if __package__:
    from .config import DUST_GROWTH, MAX_DUST, NUM_PANELS
else:
    from config import DUST_GROWTH, MAX_DUST, NUM_PANELS


PANELS = [{"dust": 0.0} for _ in range(NUM_PANELS)]


def tick():
    for panel in PANELS:
        panel["dust"] = min(panel["dust"] + DUST_GROWTH, MAX_DUST)


def get_efficiency(panel_index):
    return 1 - PANELS[panel_index]["dust"]


def clean(panel_index, amount):
    PANELS[panel_index]["dust"] = max(PANELS[panel_index]["dust"] - amount, 0.0)