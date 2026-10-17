import json

from src import panel, robot, telemetry


for tick_number in range(1, 21):
    panel.tick()
    robot.tick()
    print(json.dumps(telemetry.emit(tick_number)))
