# Panel size: 1 m × 2 m test panel
PANEL_SIZE = (1.0, 2.0)
# Robot footprint: ~30 cm × 20 cm, mass ~2.5 kg (estimate)
ROBOT_FOOTPRINT = (0.3, 0.2, 2.5)
# Drive speed: ~0.15 m/s (estimate)
DRIVE_SPEED = 0.15
# Battery: 12 V, 2200 mAh Li-ion (estimate)
BATTERY = (12, 2200)
# Pump flow: 100 L/H — midpoint of the documented 80–120 range (FACT, datasheet)
PUMP_FLOW = 100
# Dust growth: ~0.4% efficiency loss per day (estimate)
DUST_GROWTH = 0.004
# Maximum dust level: fully soiled panel
MAX_DUST = 1.0
# Battery drain per idle tick: 0.02 percentage points (ESTIMATE)
BATTERY_IDLE_DRAIN_PER_TICK = 0.02
# Battery drain per moving tick: 0.1 percentage points (ESTIMATE)
BATTERY_MOVING_DRAIN_PER_TICK = 0.1
# Battery drain per cleaning tick with brushes and pump active: 0.3 percentage points (ESTIMATE)
BATTERY_CLEANING_DRAIN_PER_TICK = 0.3
# Battery refill per charging tick: 1 percentage point (ESTIMATE)
BATTERY_REFILL_PER_TICK = 1.0
# Dust removed by brushing per tick: 0.05 dust fraction (ESTIMATE)
CLEANING_RATE_PER_TICK = 0.05
# Width of each panel along the robot's x-axis
PANEL_WIDTH_M = 2.0
# Number of panels in the solar array (ESTIMATE)
NUM_PANELS = 20
ARRAY_LENGTH_M = NUM_PANELS * PANEL_WIDTH_M
# Brush health lost per cleaning tick: 0.0004 percentage points (ESTIMATE)
BRUSH_WEAR_PER_TICK = 0.0004
# Water tank capacity used per cleaning tick: 0.0004 percentage points (ESTIMATE)
WATER_USE_PER_TICK = 0.0004
# Brush maintenance threshold in percent
BRUSH_MAINTENANCE_THRESHOLD_PCT = 40
# Distance traveled between automatic cleaning stops: half a panel width (ESTIMATE)
CLEANING_TRIGGER_DISTANCE_M = PANEL_WIDTH_M / 2
# Number of ticks spent cleaning at each distance trigger (ESTIMATE)
CLEANING_DURATION_TICKS = 5
# Time required to replace the brush: 10 minutes (ESTIMATE)
MAINTENANCE_DURATION_TICKS = 600
