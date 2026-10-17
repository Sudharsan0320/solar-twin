from pathlib import Path

import duckdb
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error


ROOT = Path(__file__).resolve().parent
PARQUET_ROOT = ROOT / "data" / "parquet" / "telemetry"
FEATURE_COLUMNS = [
    "brush_health_pct",
    "brush_drain_rate_per_tick",
    "cleaning_ticks_trailing_1000",
    "water_tank_pct",
]
TARGET_COLUMN = "ticks_until_failure"

FAILURE_DATASET_QUERY = """
WITH ordered_readings AS (
    SELECT
        robot_id,
        ts,
        state,
        brush_health_pct,
        water_tank_pct,
        row_number() OVER (
            PARTITION BY robot_id ORDER BY ts
        ) AS tick_number,
        lag(brush_health_pct, 1000) OVER (
            PARTITION BY robot_id ORDER BY ts
        ) AS brush_health_1000_ticks_ago,
        lag(brush_health_pct) OVER (
            PARTITION BY robot_id ORDER BY ts
        ) AS previous_brush_health_pct,
        sum(CASE WHEN state = 'CLEANING' THEN 1 ELSE 0 END) OVER (
            PARTITION BY robot_id
            ORDER BY ts
            ROWS BETWEEN 999 PRECEDING AND CURRENT ROW
        ) AS cleaning_ticks_trailing_1000
    FROM read_parquet(?, hive_partitioning = true)
),
readings_with_failure_tick AS (
    SELECT
        *,
        coalesce(
            min(
                CASE
                    WHEN brush_health_pct < 40
                         AND previous_brush_health_pct >= 40
                    THEN tick_number
                END
            ) OVER (
                PARTITION BY robot_id
                ORDER BY tick_number
                ROWS BETWEEN 1 FOLLOWING AND UNBOUNDED FOLLOWING
            ),
            tick_number
        ) AS next_failure_tick
    FROM ordered_readings
)
SELECT
    robot_id,
    ts,
    brush_health_pct,
    (brush_health_1000_ticks_ago - brush_health_pct) / 1000.0
        AS brush_drain_rate_per_tick,
    cleaning_ticks_trailing_1000,
    water_tank_pct,
    greatest(next_failure_tick - tick_number, 0) AS ticks_until_failure
FROM readings_with_failure_tick
WHERE tick_number % 100 = 0
  AND tick_number > 1000
ORDER BY ts
"""


def build_failure_dataset(parquet_files):
    with duckdb.connect(":memory:") as connection:
        return connection.execute(FAILURE_DATASET_QUERY, [parquet_files]).fetchdf()


def main():
    parquet_files = sorted(
        str(path) for path in PARQUET_ROOT.glob("event_date=*/*.parquet")
    )
    if not parquet_files:
        raise FileNotFoundError(f"No Parquet telemetry files found in {PARQUET_ROOT}")

    dataset = build_failure_dataset(parquet_files)
    split_index = int(len(dataset) * 0.7)
    train = dataset.iloc[:split_index]
    test = dataset.iloc[split_index:]

    print(f"Total rows: {len(dataset)}")
    print(f"Time split: {len(train)} train (earliest), {len(test)} test (latest)")

    model = LinearRegression()
    model.fit(train[FEATURE_COLUMNS], train[TARGET_COLUMN])
    predictions = model.predict(test[FEATURE_COLUMNS]).clip(min=0)

    print(f"MAE: {mean_absolute_error(test[TARGET_COLUMN], predictions):.2f} ticks")
    rmse = mean_squared_error(test[TARGET_COLUMN], predictions) ** 0.5
    print(f"RMSE: {rmse:.2f} ticks")
    comparisons = test[["ts", TARGET_COLUMN]].head(5).copy()
    comparisons["predicted_ticks_until_failure"] = predictions[:5]
    print("Predicted vs. actual (first five test rows):")
    print(comparisons.to_string(index=False))


if __name__ == "__main__":
    main()
