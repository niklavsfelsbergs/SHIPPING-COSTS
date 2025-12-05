"""Debug script to investigate period expression issue."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import polars as pl
from datetime import date

from ontrac.surcharges import DEM_RES, DEM_AHS

# Test the period expression logic manually
print("DEM_RES period:")
print(f"  start: {DEM_RES.period_start} -> {DEM_RES.period_start[0] * 100 + DEM_RES.period_start[1]}")
print(f"  end: {DEM_RES.period_end} -> {DEM_RES.period_end[0] * 100 + DEM_RES.period_end[1]}")

print("\nDEM_AHS period:")
print(f"  start: {DEM_AHS.period_start} -> {DEM_AHS.period_start[0] * 100 + DEM_AHS.period_start[1]}")
print(f"  end: {DEM_AHS.period_end} -> {DEM_AHS.period_end[0] * 100 + DEM_AHS.period_end[1]}")

# Create test dataframe with different dates
test_dates = [
    date(2025, 6, 15),   # June 15 - should be OUTSIDE
    date(2025, 9, 26),   # Sept 26 - should be OUTSIDE (DEM_AHS starts Sept 27)
    date(2025, 9, 27),   # Sept 27 - should be IN for DEM_AHS
    date(2025, 10, 24),  # Oct 24 - should be OUTSIDE for DEM_RES
    date(2025, 10, 25),  # Oct 25 - should be IN for DEM_RES
    date(2025, 11, 15),  # Nov 15 - should be IN
    date(2025, 12, 31),  # Dec 31 - should be IN
    date(2025, 1, 16),   # Jan 16 - should be IN
    date(2025, 1, 17),   # Jan 17 - should be OUTSIDE
    date(2025, 3, 1),    # Mar 1 - should be OUTSIDE
]

df = pl.DataFrame({
    "pcs_created": test_dates,
    "surcharge_res": [True] * len(test_dates),
    "surcharge_ahs": [True] * len(test_dates),
})

print("\n" + "=" * 60)
print("Testing period expressions")
print("=" * 60)

# Add period check columns - debug the individual components
df = df.with_columns([
    pl.col("pcs_created").dt.month().alias("month"),
    pl.col("pcs_created").dt.day().alias("day"),
    pl.col("pcs_created").dt.month().cast(pl.Int32).alias("month_i32"),
    pl.col("pcs_created").dt.day().cast(pl.Int32).alias("day_i32"),
    (pl.col("pcs_created").dt.month() * 100 + pl.col("pcs_created").dt.day()).alias("ship_md_raw"),
    (pl.col("pcs_created").dt.month().cast(pl.Int32) * 100 + pl.col("pcs_created").dt.day().cast(pl.Int32)).alias("ship_md_i32"),
    DEM_RES._period_expr().alias("dem_res_period"),
    DEM_AHS._period_expr().alias("dem_ahs_period"),
    DEM_RES.conditions().alias("dem_res_conditions"),
    DEM_AHS.conditions().alias("dem_ahs_conditions"),
])

df.write_csv(Path(__file__).parent / "data" / "debug_period_output.csv")
print("Output written to tests/data/debug_period_output.csv")

# Expected results
print("\n" + "=" * 60)
print("Expected results:")
print("=" * 60)
print("June 15 (615): OUTSIDE both periods")
print("Sept 26 (926): OUTSIDE both periods")
print("Sept 27 (927): IN DEM_AHS, OUTSIDE DEM_RES")
print("Oct 24 (1024): IN DEM_AHS, OUTSIDE DEM_RES")
print("Oct 25 (1025): IN both periods")
print("Nov 15 (1115): IN both periods")
print("Dec 31 (1231): IN both periods")
print("Jan 16 (116): IN both periods")
print("Jan 17 (117): OUTSIDE both periods")
print("Mar 1 (301): OUTSIDE both periods")
