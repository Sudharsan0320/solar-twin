from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_date
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)


ROOT = Path(__file__).resolve().parent
TOPIC = "robot.telemetry"
BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_CONNECTOR = "org.apache.spark:spark-sql-kafka-0-10_2.13:4.2.0"
PARQUET_PATH = ROOT / "data" / "parquet" / "telemetry"
CHECKPOINT_PATH = ROOT / "data" / "checkpoints" / "telemetry"

TELEMETRY_SCHEMA = StructType(
    [
        StructField("robot_id", StringType(), False),
        StructField("ts", TimestampType(), False),
        StructField("state", StringType(), False),
        StructField("x", DoubleType(), False),
        StructField("y", DoubleType(), False),
        StructField("heading", DoubleType(), False),
        StructField("battery_pct", DoubleType(), False),
        StructField("water_tank_pct", DoubleType(), False),
        StructField("brush_health_pct", DoubleType(), False),
        StructField("panel_id", IntegerType(), False),
        StructField("fault_code", StringType(), True),
    ]
)


def main():
    spark = (
        SparkSession.builder.appName("solar-twin-telemetry")
        .config("spark.jars.packages", KAFKA_CONNECTOR)
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    try:
        kafka_readings = (
            spark.readStream.format("kafka")
            .option("kafka.bootstrap.servers", BOOTSTRAP_SERVERS)
            .option("subscribe", TOPIC)
            .option("startingOffsets", "earliest")
            .load()
        )
        readings = (
            kafka_readings.select(
                from_json(
                    col("value").cast("string"),
                    TELEMETRY_SCHEMA,
                    {"mode": "FAILFAST"},
                ).alias("reading")
            )
            .select("reading.*")
            .withColumn("event_date", to_date("ts"))
        )

        parquet_query = (
            readings.writeStream.format("parquet")
            .outputMode("append")
            .option("path", str(PARQUET_PATH))
            .option("checkpointLocation", str(CHECKPOINT_PATH))
            .partitionBy("event_date")
            .start()
        )
        parquet_query.awaitTermination()
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
