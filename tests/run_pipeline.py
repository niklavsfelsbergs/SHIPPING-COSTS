"""
Run Pipeline on Mock Data

Loads mock shipments, runs through supplement + calculate, saves output.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import polars as pl
from ontrac.calculate_costs import supplement_shipments, calculate


def main():
    # Load mock shipments
    mock_data_path = Path(__file__).parent / "data" / "mock_shipments.csv"
    df = pl.read_csv(
        mock_data_path,
        try_parse_dates=True,
    )

    # Ensure pcs_created is Date type
    df = df.with_columns(pl.col("pcs_created").cast(pl.Date))

    print(f"Loaded {len(df)} mock shipments")
    print(f"Columns: {df.columns}")
    print()

    # Run supplement_shipments and save intermediate output
    print("Running supplement_shipments...")
    df_supplemented = supplement_shipments(df)
    print(f"After supplement: {df_supplemented.columns}")

    supplemented_output_path = Path(__file__).parent / "data" / "mock_shipments_supplemented.csv"
    df_supplemented.write_csv(supplemented_output_path)
    print(f"Supplemented output saved to: {supplemented_output_path}")
    print()

    # Run calculate
    print("Running calculate...")
    df_calculated = calculate(df_supplemented)
    print(f"After calculate: {df_calculated.columns}")

    calculated_output_path = Path(__file__).parent / "data" / "mock_shipments_calculated.csv"
    df_calculated.write_csv(calculated_output_path)
    print(f"Calculated output saved to: {calculated_output_path}")
    print()

    # Print results summary
    print("\n" + "=" * 80)
    print("SUPPLEMENTED FIELDS")
    print("=" * 80)

    supplement_cols = [
        "pcs_ordernumber",
        "weight_lbs",
        "length_in",
        "width_in",
        "height_in",
        "cubic_in",
        "longest_side_in",
        "second_longest_in",
        "length_plus_girth",
        "dim_weight_lbs",
        "uses_dim_weight",
        "billable_weight_lbs",
        "shipping_zone",
        "das_zone",
    ]
    supplement_cols = [c for c in supplement_cols if c in df_supplemented.columns]
    print(df_supplemented.select(supplement_cols))

    print("\n" + "=" * 80)
    print("SURCHARGE FLAGS & COSTS")
    print("=" * 80)

    surcharge_cols = [
        "pcs_ordernumber",
        "pcs_created",
        "billable_weight_lbs",
        "surcharge_oml", "cost_oml",
        "surcharge_lps", "cost_lps",
        "surcharge_ahs", "cost_ahs",
        "surcharge_edas", "cost_edas",
        "surcharge_das", "cost_das",
        "surcharge_res", "cost_res",
        "surcharge_dem_oml", "cost_dem_oml",
        "surcharge_dem_lps", "cost_dem_lps",
        "surcharge_dem_ahs", "cost_dem_ahs",
        "surcharge_dem_res", "cost_dem_res",
    ]
    surcharge_cols = [c for c in surcharge_cols if c in df_calculated.columns]
    print(df_calculated.select(surcharge_cols))

    print("\n" + "=" * 80)
    print("TOTALS")
    print("=" * 80)

    total_cols = [
        "pcs_ordernumber",
        "cost_base",
        "cost_subtotal",
        "cost_fuel",
        "cost_total",
        "calculator_version",
    ]
    total_cols = [c for c in total_cols if c in df_calculated.columns]
    print(df_calculated.select(total_cols))

    return df_calculated


if __name__ == "__main__":
    main()
