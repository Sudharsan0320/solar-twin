# Solar Panel Cleaning Robot — Digital Twin

This is a software rebuild of my final-year B.E. Mechatronics project (Chennai Institute of Technology, 2023). The original was a physical robot — Arduino, ultrasonic sensors, water pump, brushes — that cleaned solar panels. I lost the hardware and all the data after graduation, so I'm rebuilding it here as a digital twin: a Python simulation of the robot and a local streaming data pipeline.

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

4. **The robot drives itself.** It boots into MOVING, stops to clean every 1.0 m traveled (like the real robot's distance triggers), and on low battery charges in place — then resumes exactly where it left off.

## Project structure

```
solar-twin/
  main.py       # runs the simulation and prints telemetry readings
  visual.py     # animated twin: panels recolor from live dust, robot dot tracked
  producer.py   # publishes twin telemetry to Kafka
  stream_job.py # parses Kafka telemetry and writes console + Parquet streams
  dashboard.py  # latest robot state and cleaning summary
  analytics.py  # DuckDB weekly cleaning query
  duckdb_test.py # runs the weekly cleaning query in the terminal
  src/
    config.py   # every assumption, labeled FACT or ESTIMATE
    panel.py    # the world: panels, dust growth, and cleaning
    robot.py    # robot state and behavior
    telemetry.py # formats robot and panel state as JSON-ready readings
```

## Local streaming pipeline

The local pipeline requires Java 17, the project virtual environment, and Kafka in KRaft mode. Install Python dependencies with:

```sh
venv/bin/pip install -r requirements.txt
```

Install Java 17 and set the runtime environment. With Kafka unpacked at `~/tools/kafka`, initialize storage once:

```sh
brew install openjdk@17
export JAVA_HOME="$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
java -version
"$HOME/tools/kafka/bin/kafka-storage.sh" format --standalone \
  -t "$("$HOME/tools/kafka/bin/kafka-storage.sh" random-uuid)" \
  -c "$HOME/tools/kafka/config/server.properties"
```

Use separate terminals for the broker, topic setup, producer, Spark job, and dashboard. In the broker terminal, set Java again and start Kafka:

```sh
export JAVA_HOME="$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
"$HOME/tools/kafka/bin/kafka-server-start.sh" "$HOME/tools/kafka/config/server.properties"
```

In another terminal, create the one-partition topic:

```sh
"$HOME/tools/kafka/bin/kafka-topics.sh" --bootstrap-server localhost:9092 \
  --create --if-not-exists --topic robot.telemetry --partitions 1 --replication-factor 1
```

In separate terminals, start the producer and Spark Structured Streaming job. Spark also needs the Java environment:

```sh
venv/bin/python producer.py
```

```sh
export JAVA_HOME="$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
venv/bin/python stream_job.py
```

The producer emits one JSON reading per second. By default it autonomously alternates between moving and distance-triggered cleaning, charging below 20% and resuming its prior activity when full. The optional `--state` flag overrides its starting state. `stream_job.py` writes date-partitioned Parquet under `data/parquet/telemetry`; its checkpoint is `data/checkpoints/telemetry`. Keep that checkpoint when restarting the job. Removing it starts a new stream from the topic's earliest retained offset and can create duplicate output. The console sink was removed after validating the stream so restarts do not replay old readings to the console.

Crash/restart verified: 533 Kafka offsets produced 533 Parquet rows with all-unique timestamps — no loss, no duplicates.

Run the dashboard in another terminal:

```sh
venv/bin/streamlit run dashboard.py
```

The dashboard refreshes every two seconds and shows the latest battery, state, and fault for each robot, cleaning ticks on the latest simulated date, and the DuckDB weekly panel/battery-cost summary. `venv/bin/python duckdb_test.py` runs that weekly analytical query in the terminal. By default, the producer runs the autonomous mission continuously; use `--max-messages 100` for a bounded run or `--state CLEANING` to override the starting state.

## Plan

- **Phase 1** — twin simulation
- **Phase 2** — local Kafka → Spark streaming → Parquet → dashboard
- **Phase 3** — cleaning analytics + brush/battery failure prediction

The brush-wear model will score highly because the simulated wear is nearly deterministic (a fixed rate per cleaning tick); that reflects the simplicity of the simulation, not model magic.

The remaining-useful-life training dataset excludes readings after the last observed brush-threshold crossing. That post-crossing tail is right-censored: the next maintenance event has not occurred within the observed data, so its true time-to-failure is unknown.

Run `venv/bin/python train_model.py` to regenerate the ignored `model.pkl` artifact used for live maintenance predictions.

## Assumptions

The report had no measured results, so anything I couldn't verify is an estimate, marked as one in `config.py`. The pump flow (80–120 L/H) comes from the datasheet — that's a fact.
