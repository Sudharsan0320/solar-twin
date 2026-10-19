# Solar Panel Cleaning Robot — Digital Twin

This is a software rebuild of my final-year B.E. Mechatronics project (Chennai Institute of Technology, 2023). The original was a physical robot — Arduino, ultrasonic sensors, water pump, brushes — that cleaned solar panels. I lost the hardware and all the data after graduation, so I'm rebuilding it here as a digital twin: a Python simulation of the robot and a local streaming data pipeline.

## The original robot (from my project report)

- 2-wheel-drive chassis, Arduino Uno
- 2 ultrasonic sensors for distance, L293D motor driver, 2 drive motors
- Rotating brushes (front + back) + water pump (3–6V, 80–120 L/H)
- ESP32 camera watching the panel during cleaning
- LCD, buzzer, relay, rechargeable battery
- My teammate wrote the control code in C++; this rebuild is Python.

One honest note: the report lists automatic dust detection as future work. The physical robot started cleaning based on distance traveled, not dirt sensing. This twin keeps that distance trigger and adds a simulated dirt sensor as an explicitly estimated extension.

## How the twin works

Three ideas carry the whole simulation:

1. **State + tick.** The twin is a snapshot of numbers (robot position, battery, each panel's dust level). Every tick is one simulated second: the robot moves a bit, the battery drops a bit, dust grows a bit. A thousand ticks is about 17 minutes of fake time.

2. **Config file.** Every number that describes the world lives in `src/config.py` — panel size, speed, battery, pump flow. Each line says whether it's a FACT (from the report or datasheet) or an ESTIMATE (my best guess). No magic numbers hiding in the code.

3. **The world is separate from the robot.** The panel array tracks the panels (dust per panel). The robot tracks itself (position, battery). Efficiency isn't stored anywhere — it's computed when asked: `1 - dust`.

4. **The robot drives itself.** It boots into MOVING and cleans when either the distance trigger fires (like the real robot) or the simulated dirt sensor detects a soiled panel. On low battery it charges in place, then resumes exactly where it left off.

Wrap-around patrol is replaced by a lidar edge stop: at the array bounds, the robot clamps inside the panel and reverses heading (0.0 ↔ 180.0), so patrol runs back and forth.

The simulated world has two 20-panel rows separated by the estimated `ROW_GAP_M`. The robot uses `TRANSPORT` to cross the gap and patrols serpentine-style, with 2D routing for charging and panel dispatch. Panel IDs are now 0–39 and telemetry includes `row`; use a fresh Kafka topic, checkpoint, and telemetry lake before collecting data for analytics, since existing output is not migrated.

## Project structure

```
solar-twin/
  main.py       # runs the simulation and prints telemetry readings
  visual.py     # animated twin: live panels, vehicle, brushes, spray, and HUD
  producer.py   # publishes twin telemetry to Kafka
  stream_job.py # parses Kafka telemetry and writes date-partitioned Parquet
  dashboard.py  # fleet KPIs, charts, cleaning summaries, and predictions
  analytics.py  # DuckDB weekly cleaning query
  duckdb_test.py # runs the weekly cleaning query in the terminal
  src/
    config.py   # every assumption, labeled FACT or ESTIMATE
    panel.py    # the world: panels, dust growth, and cleaning
    robot.py    # robot state and behavior
    telemetry.py # formats robot and panel state as JSON-ready readings
```

## Running the project

### One-time setup

Install Java 17, Kafka in KRaft mode, and the Python dependencies. This setup assumes Kafka is unpacked at `~/tools/kafka`; its KRaft configuration is `config/server.properties`.

```sh
brew install openjdk@17
export JAVA_HOME="$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
java -version

# Create the virtual environment only if it does not already exist.
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Initialize Kafka storage once for a new local installation only. Do not format storage that already contains Kafka data.

```sh
"$HOME/tools/kafka/bin/kafka-storage.sh" format --standalone \
  -t "$("$HOME/tools/kafka/bin/kafka-storage.sh" random-uuid)" \
  -c "$HOME/tools/kafka/config/server.properties"
```

For an optional screen recording of the animated prototype, install FFmpeg:

```sh
brew install ffmpeg
venv/bin/python export_video.py
```

The headless export script writes a 12-second, 120-frame `twin_demo.mp4` to the project folder.

### Start the pipeline

Run each long-lived service in its own terminal, in this order.

1. Start Kafka. Export the Java variables in this terminal first:

   ```sh
   export JAVA_HOME="$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home"
   export PATH="$JAVA_HOME/bin:$PATH"
   "$HOME/tools/kafka/bin/kafka-server-start.sh" "$HOME/tools/kafka/config/server.properties"
   ```

2. Create the telemetry topic (one partition is used by this demo):

   ```sh
   "$HOME/tools/kafka/bin/kafka-topics.sh" --bootstrap-server localhost:9092 \
     --create --if-not-exists --topic robot.telemetry \
     --partitions 1 --replication-factor 1
   ```

3. Start Spark Structured Streaming. Export the Java variables in this terminal too:

   ```sh
   export JAVA_HOME="$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home"
   export PATH="$JAVA_HOME/bin:$PATH"
   venv/bin/spark-submit \
     --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.2.0 \
     stream_job.py
   ```

4. Start a producer in another terminal:

   ```sh
   venv/bin/python producer.py
   ```

   The producer emits one JSON reading per second and runs continuously. Use `--max-messages 100` for a bounded run, `--state CLEANING` to override its starting state, or `--robot-id twin-02` to set a fleet robot's identity. Each robot is a separate producer writing to the shared topic. The resume tick is read from the topic's last message without filtering by robot ID, so start fleet-demo robots fresh to avoid one robot resuming from another's tick.

5. After telemetry is in the lake, train or retrain the model:

   ```sh
   venv/bin/python train_model.py
   ```

   This writes the ignored `model.pkl` file used by the dashboard's predictions.

6. Start the dashboard:

   ```sh
   venv/bin/streamlit run dashboard.py
   ```

   Open [http://localhost:8501](http://localhost:8501/). It refreshes every two seconds with fleet KPIs, brush-health and cleaning-trigger charts, latest readings, cleaning summaries, and model-based maintenance predictions. `venv/bin/python duckdb_test.py` runs the weekly cleaning analytics query in the terminal.

7. Optionally run the animated twin in its own terminal:

   ```sh
   venv/bin/python visual.py
   ```

   It visualizes the live simulation state, including panel dust, the robot chassis, wheels, spinning cleaning brushes, water spray, and a status readout.

### Shutdown and fresh runs

Stop services with Ctrl+C in reverse startup order: dashboard, producer, Spark, then Kafka. The Parquet lake, Spark checkpoint, and Kafka topic persist across ordinary restarts. Keep the checkpoint at `data/checkpoints/telemetry` when resuming Spark; deleting it can replay Kafka records and duplicate Parquet output.

For a clean demo run, stop the services first. Remove the generated lake and checkpoint, then start Kafka again using step 1. With the broker running and before starting Spark or the producer, delete and recreate the topic. Wait for the deleted topic to disappear before creating it again. This permanently removes the local Parquet output and streaming progress:

```sh
rm -rf data/parquet data/checkpoints
"$HOME/tools/kafka/bin/kafka-topics.sh" --bootstrap-server localhost:9092 \
  --delete --topic robot.telemetry
"$HOME/tools/kafka/bin/kafka-topics.sh" --bootstrap-server localhost:9092 \
  --create --topic robot.telemetry --partitions 1 --replication-factor 1
```

After recreating the topic, continue from step 3. The lake is `data/parquet/telemetry`, the checkpoint is `data/checkpoints/telemetry`, and the trained model is `model.pkl`; all are gitignored.

Crash/restart verified: 533 Kafka offsets produced 533 Parquet rows with all-unique timestamps — no loss, no duplicates.

## Plan

- **Phase 1** — twin simulation
- **Phase 2** — local Kafka → Spark streaming → Parquet → dashboard
- **Phase 3** — cleaning analytics + brush/battery failure prediction

The brush-wear model will score highly because the simulated wear is nearly deterministic (a fixed rate per cleaning tick); that reflects the simplicity of the simulation, not model magic.

The remaining-useful-life training dataset excludes readings after the last observed brush-threshold crossing. That post-crossing tail is right-censored: the next maintenance event has not occurred within the observed data, so its true time-to-failure is unknown.

## Assumptions

The report had no measured results, so anything I couldn't verify is an estimate, marked as one in `config.py`. The pump flow (80–120 L/H) comes from the datasheet — that's a fact.
