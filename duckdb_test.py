from pathlib import Path

from analytics import weekly_cleaning_summary


parquet_root = Path(__file__).resolve().parent / "data" / "parquet" / "telemetry"
parquet_files = sorted(
    str(path) for path in parquet_root.glob("event_date=*/*.parquet")
)
if not parquet_files:
    raise FileNotFoundError(f"No Parquet telemetry found under {parquet_root}")

print(weekly_cleaning_summary(parquet_files).to_string(index=False))
