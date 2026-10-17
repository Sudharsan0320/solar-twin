import argparse
import json
import time
from datetime import datetime

from kafka import KafkaConsumer, KafkaProducer, TopicPartition

from src import panel, robot, telemetry


def latest_tick_number(bootstrap_server, topic):
    consumer = KafkaConsumer(
        bootstrap_servers=bootstrap_server,
        enable_auto_commit=False,
    )
    try:
        partition_ids = consumer.partitions_for_topic(topic)
        if not partition_ids:
            raise RuntimeError(f"Kafka topic {topic!r} has no partitions")

        partitions = [TopicPartition(topic, partition_id) for partition_id in partition_ids]
        end_offsets = consumer.end_offsets(partitions)
        partition = max(partitions, key=end_offsets.__getitem__)
        if end_offsets[partition] == 0:
            return 0

        consumer.assign([partition])
        consumer.seek(partition, end_offsets[partition] - 1)
        records = consumer.poll(timeout_ms=5000, max_records=1).get(partition, [])
        if not records:
            raise RuntimeError(f"Could not read the latest message from topic {topic!r}")

        latest_reading = json.loads(records[-1].value)
        latest_timestamp = datetime.fromisoformat(latest_reading["ts"])
        return int((latest_timestamp - telemetry.SIMULATION_START).total_seconds())
    finally:
        consumer.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Publish twin telemetry to Kafka.")
    parser.add_argument("--bootstrap-server", default="localhost:9092")
    parser.add_argument("--topic", default="robot.telemetry")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--max-messages", type=int)
    parser.add_argument("--start-tick", type=int, default=0)
    parser.add_argument(
        "--state",
        choices=("IDLE", "MOVING", "CLEANING", "CHARGING"),
        help="override the autonomous mission's starting state",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.interval <= 0:
        raise ValueError("--interval must be greater than zero")
    if args.max_messages is not None and args.max_messages < 1:
        raise ValueError("--max-messages must be at least one")

    if args.state is not None:
        robot.ROBOT["state"] = args.state
    tick_number = max(
        args.start_tick,
        latest_tick_number(args.bootstrap_server, args.topic),
    )
    first_tick = tick_number
    producer = KafkaProducer(
        bootstrap_servers=args.bootstrap_server,
    )
    next_publish = time.monotonic()

    try:
        while args.max_messages is None or tick_number - first_tick < args.max_messages:
            tick_number += 1
            panel.tick()
            robot.tick()
            reading = telemetry.emit(tick_number)
            encoded_reading = json.dumps(reading).encode("utf-8")
            producer.send(args.topic, value=encoded_reading).get(timeout=30)
            print(json.dumps(reading), flush=True)
            next_publish += args.interval
            if args.max_messages is None or tick_number - first_tick < args.max_messages:
                time.sleep(max(0.0, next_publish - time.monotonic()))
    finally:
        producer.flush(timeout=30)
        producer.close(timeout=30)


if __name__ == "__main__":
    main()
