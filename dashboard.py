from pathlib import Path
import pickle

import duckdb
import streamlit as st

from analytics import weekly_cleaning_summary


ROOT = Path(__file__).resolve().parent
PARQUET_ROOT = ROOT / "data" / "parquet" / "telemetry"
MODEL_PATH = ROOT / "model.pkl"

st.set_page_config(page_title="Solar Twin", layout="wide")
st.title("Solar Robot Telemetry")


@st.cache_resource
def load_model():
    if not MODEL_PATH.exists():
        return None
    with MODEL_PATH.open("rb") as model_file:
        return pickle.load(model_file)


@st.fragment(run_every="2s")
def render_dashboard():
    parquet_files = sorted(
        str(path) for path in PARQUET_ROOT.glob("event_date=*/*.parquet")
    )
    if not parquet_files:
        st.info("Waiting for Parquet telemetry. Start the Kafka producer and Spark job.")
        return

    with duckdb.connect(":memory:") as connection:
        latest_readings = connection.execute(
            """
            SELECT robot_id, ts, state, battery_pct, brush_health_pct, fault_code
            FROM read_parquet(?, hive_partitioning = true)
            QUALIFY row_number() OVER (
                PARTITION BY robot_id ORDER BY ts DESC
            ) = 1
            ORDER BY robot_id
            """,
            [parquet_files],
        ).fetchdf()
        cleaning_today = connection.execute(
            """
            SELECT robot_id, count(*) AS cleaning_ticks
            FROM read_parquet(?, hive_partitioning = true)
            WHERE state = 'CLEANING'
              AND CAST(ts AS DATE) = (
                  SELECT max(CAST(ts AS DATE))
                  FROM read_parquet(?, hive_partitioning = true)
              )
            GROUP BY robot_id
            ORDER BY robot_id
            """,
            [parquet_files, parquet_files],
        ).fetchdf()
        panels_cleaned = connection.execute(
            """
            SELECT count(DISTINCT panel_id)
            FROM read_parquet(?, hive_partitioning = true)
            WHERE state = 'CLEANING'
            """,
            [parquet_files],
        ).fetchone()[0]
        brush_health_samples = connection.execute(
            """
            WITH sampled_readings AS (
                SELECT
                    robot_id,
                    ts,
                    brush_health_pct,
                    row_number() OVER (
                        PARTITION BY robot_id ORDER BY ts
                    ) AS reading_number
                FROM read_parquet(?, hive_partitioning = true)
            )
            SELECT robot_id, ts, brush_health_pct
            FROM sampled_readings
            WHERE (reading_number - 1) % 10 = 0
            ORDER BY ts, robot_id
            """,
            [parquet_files],
        ).fetchdf()
        brush_health_chart = brush_health_samples.pivot(
            index="ts",
            columns="robot_id",
            values="brush_health_pct",
        ).sort_index()
        cleaning_triggers = connection.execute(
            """
            SELECT cleaning_trigger, count(*) AS cleaning_ticks
            FROM read_parquet(?, hive_partitioning = true)
            WHERE cleaning_trigger != 'none'
            GROUP BY cleaning_trigger
            ORDER BY cleaning_trigger
            """,
            [parquet_files],
        ).fetchdf()

        model_bundle = load_model()
        prediction_table = None
        if model_bundle is not None:
            latest_features = connection.execute(
                """
                WITH readings AS (
                    SELECT
                        robot_id,
                        ts,
                        brush_health_pct,
                        water_tank_pct,
                        lag(brush_health_pct, 1000) OVER (
                            PARTITION BY robot_id ORDER BY ts
                        ) AS brush_health_1000_ticks_ago,
                        sum(CASE WHEN state = 'CLEANING' THEN 1 ELSE 0 END) OVER (
                            PARTITION BY robot_id
                            ORDER BY ts
                            ROWS BETWEEN 999 PRECEDING AND CURRENT ROW
                        ) AS cleaning_ticks_trailing_1000,
                        row_number() OVER (
                            PARTITION BY robot_id ORDER BY ts DESC
                        ) AS latest_reading_rank
                    FROM read_parquet(?, hive_partitioning = true)
                )
                SELECT
                    robot_id,
                    brush_health_pct,
                    (brush_health_1000_ticks_ago - brush_health_pct) / 1000.0
                        AS brush_drain_rate_per_tick,
                    cleaning_ticks_trailing_1000,
                    water_tank_pct
                FROM readings
                WHERE latest_reading_rank = 1
                ORDER BY robot_id
                """,
                [parquet_files],
            ).fetchdf()

    if model_bundle is not None:
        features = model_bundle["features"]
        predictions = model_bundle["model"].predict(latest_features[features]).clip(min=0)
        prediction_table = latest_features[["robot_id"]].copy()
        prediction_table["predicted_ticks_until_maintenance"] = predictions
        prediction_table["predicted_hours_until_maintenance"] = predictions / 3600

    metric_columns = st.columns(4)
    metric_columns[0].metric("Fleet size", len(latest_readings))
    metric_columns[1].metric("Panels cleaned", int(panels_cleaned))
    metric_columns[2].metric(
        "Avg brush health",
        f"{latest_readings['brush_health_pct'].mean():.1f}%",
    )
    soonest_maintenance = (
        f"{prediction_table['predicted_hours_until_maintenance'].min():.1f} h"
        if prediction_table is not None
        else "N/A"
    )
    metric_columns[3].metric("Soonest maintenance", soonest_maintenance)

    st.subheader("Brush health over time")
    st.line_chart(
        brush_health_chart.reset_index(),
        x="ts",
        y=brush_health_chart.columns.tolist(),
        use_container_width=True,
    )

    st.subheader("What triggered cleaning")
    st.bar_chart(
        cleaning_triggers,
        x="cleaning_trigger",
        y="cleaning_ticks",
        use_container_width=True,
    )

    st.subheader("Latest readings")
    st.dataframe(latest_readings, use_container_width=True, hide_index=True)
    st.subheader("Cleaning ticks on latest simulated day")
    st.dataframe(cleaning_today, use_container_width=True, hide_index=True)

    st.subheader("Weekly cleaning summary")
    weekly_summary = weekly_cleaning_summary(parquet_files)
    if weekly_summary.empty:
        st.info("No cleaning readings are available for the latest simulated week yet.")
    else:
        st.dataframe(weekly_summary, use_container_width=True, hide_index=True)

    st.subheader("Predicted maintenance")
    if prediction_table is None:
        st.info("Train the model first: python train_model.py")
    else:
        st.dataframe(prediction_table, use_container_width=True, hide_index=True)


render_dashboard()
