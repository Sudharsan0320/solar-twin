# Solar Panel Cleaning Robot — Digital Twin

This is a software rebuild of my final-year B.E. Mechatronics project (Chennai Institute of Technology, 2023). The original was a physical robot — Arduino, ultrasonic sensors, water pump, brushes — that cleaned solar panels. I lost the hardware and all the data after graduation, so I'm rebuilding it here as a digital twin: a Python simulation of the robot, plus (later) the data pipeline a real fleet would need.

## The original robot (from my project report)

- 2-wheel-drive chassis, Arduino Uno
- 2 ultrasonic sensors for distance, L293D motor driver, 2 drive motors
- Rotating brushes (front + back) + water pump (3–6V, 80–120 L/H)
- ESP32 camera watching the panel during cleaning
- LCD, buzzer, relay, rechargeable battery
- My teammate wrote the control code in C++; this rebuild is Python.

One honest note: the report lists automatic dust detection as future work. The robot we actually built started cleaning based on distance traveled, not dirt sensing. This twin does the same. If I add dirt sensing later, I'll label it as my extension.

## How the twin works

Three ideas carry the whole simulation:

1. **State + tick.** The twin is a snapshot of numbers (robot position, battery, each panel's dust level). Every tick is one simulated second: the robot moves a bit, the battery drops a bit, dust grows a bit. A thousand ticks is about 17 minutes of fake time.

2. **Config file.** Every number that describes the world lives in `src/config.py` — panel size, speed, battery, pump flow. Each line says whether it's a FACT (from the report or datasheet) or an ESTIMATE (my best guess). No magic numbers hiding in the code.

3. **The world is separate from the robot.** The panel array tracks the panels (dust per panel). The robot tracks itself (position, battery). Efficiency isn't stored anywhere — it's computed when asked: `1 - dust`.

## Project structure

```
solar-twin/
  main.py       # runs the simulation and prints telemetry readings
  src/
    config.py   # every assumption, labeled FACT or ESTIMATE
    panel.py    # the world: panels, dust growth, and cleaning
    robot.py    # robot state and behavior
    telemetry.py # formats robot and panel state as JSON-ready readings
```

## Plan

- **Phase 1** — twin simulation (this repo, in progress)
- **Phase 2** — Kafka → Spark streaming → live fleet dashboard
- **Phase 3** — cleaning analytics + brush/battery failure prediction

## Assumptions

The report had no measured results, so anything I couldn't verify is an estimate, marked as one in `config.py`. The pump flow (80–120 L/H) comes from the datasheet — that's a fact.
