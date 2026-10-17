from pathlib import Path

import duckdb
import streamlit as st

from analytics import weekly_cleaning_summary


ROOT = Path(__file__).resolve().parent
PARQUET_ROOT = ROOT / "data" / "parquet" / "telemetry"

st.set_page_config(page_title="Solar Twin", layout="wide")
st.title("Solar Robot Telemetry")


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
            SELECT robot_id, ts, state, battery_pct, fault_code
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
            SELECT count(*)
            FROM read_parquet(?, hive_partitioning = true)
            WHERE state = 'CLEANING'
              AND CAST(ts AS DATE) = (
                  SELECT max(CAST(ts AS DATE))
                  FROM read_parquet(?, hive_partitioning = true)
              )
            """,
            [parquet_files, parquet_files],
        ).fetchone()[0]

    st.subheader("Latest readings")
    st.dataframe(latest_readings, use_container_width=True, hide_index=True)
    st.metric("Cleaning ticks on latest simulated day", cleaning_today)

    st.subheader("Weekly cleaning summary")
    weekly_summary = weekly_cleaning_summary(parquet_files)
    if weekly_summary.empty:
        st.info("No cleaning readings are available for the latest simulated week yet.")
    else:
        st.dataframe(weekly_summary, use_container_width=True, hide_index=True)


render_dashboard()
