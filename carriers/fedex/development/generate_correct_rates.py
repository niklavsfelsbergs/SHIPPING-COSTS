"""
Generate the correct discounted rate card based on discovered discount tiers.

Discovered discount structure from invoice data:
- Weight 1:      ~36.4%
- Weight 2-5:    ~38.5%
- Weight 6-10:   ~40.5%
- Weight 11-20:  ~43.5%
- Weight 21-30:  ~47.5%
- Weight 31-39:  ~49.5%
- Weight 40:     ~53.0% (special)
- Weight 41+:    ~49.5%
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from datetime import date
import polars as pl

INVOICE_PARQUET = Path(__file__).parent / "invoice_data.parquet"
UNDISCOUNTED_RATES = Path(__file__).parent.parent / "temp_files" / "fedex_ground_rates_2025_undiscounted.csv"


def get_discount_tier(weight: int) -> float:
    """Return the discount percentage for a given weight."""
    if weight == 1:
        return 0.3641
    elif weight <= 5:
        return 0.3848
    elif weight <= 10:
        return 0.4048
    elif weight <= 20:
        return 0.4348
    elif weight <= 30:
        return 0.4748
    elif weight <= 39:
        return 0.4949
    elif weight == 40:
        return 0.5299
    else:
        return 0.4949


def main():
    # Load undiscounted rates
    print("Loading undiscounted rates...")
    undiscounted = pl.read_csv(UNDISCOUNTED_RATES)
    print(f"  Weights: 1 to {len(undiscounted)}")
    print(f"  Zones: {[c for c in undiscounted.columns if c != 'Weight_lbs']}")

    # Load invoice data to get actual PP values for verification
    print("\nLoading invoice data for verification...")
    invoice_df = pl.read_parquet(INVOICE_PARQUET)
    df = invoice_df.filter(
        (pl.col("invoice_date") >= date(2025, 7, 1)) &
        (pl.col("invoice_date") <= date(2025, 12, 31)) &
        (pl.col("service_type") == "Home Delivery") &
        (pl.col("charge_description") == "Performance Pricing")
    )

    # Get mode PP by weight/zone
    actual_pp = df.group_by(["rated_weight", "shipping_zone"]).agg([
        pl.col("charge_description_amount").cast(pl.Float64).mode().first().alias("actual_pp")
    ]).with_columns([
        pl.col("rated_weight").cast(pl.Int64),
        pl.col("shipping_zone").cast(pl.Int64)
    ])

    # Apply discount tiers to generate new rates
    print("\nGenerating discounted rate card...")

    # Unpivot undiscounted rates
    undiscounted_long = undiscounted.unpivot(
        index="Weight_lbs",
        variable_name="zone_col",
        value_name="undiscounted_rate"
    ).with_columns([
        pl.col("zone_col").str.replace("Zone", "").cast(pl.Int64).alias("zone"),
        pl.col("Weight_lbs").cast(pl.Int64).alias("weight_lbs")
    ]).select(["weight_lbs", "zone", "undiscounted_rate"])

    # Calculate discounted rate
    rates_list = []
    for row in undiscounted_long.iter_rows(named=True):
        weight = row["weight_lbs"]
        zone = row["zone"]
        undiscounted = row["undiscounted_rate"]
        discount = get_discount_tier(weight)
        discounted = round(undiscounted * (1 - discount), 2)
        rates_list.append({
            "weight_lbs": weight,
            "zone": zone,
            "undiscounted": undiscounted,
            "discount_pct": discount * 100,
            "discounted": discounted
        })

    rates_df = pl.DataFrame(rates_list)

    # Join with actual PP to verify
    rates_df = rates_df.join(
        actual_pp,
        left_on=["weight_lbs", "zone"],
        right_on=["rated_weight", "shipping_zone"],
        how="left"
    )

    # Calculate what PP we would get
    rates_df = rates_df.with_columns([
        (pl.col("discounted") - pl.col("undiscounted")).round(2).alias("calculated_pp"),
        (pl.col("discounted") - pl.col("undiscounted") - pl.col("actual_pp")).round(2).alias("pp_diff")
    ])

    # Show verification results
    print("\n" + "=" * 80)
    print("VERIFICATION: CALCULATED PP vs ACTUAL PP")
    print("=" * 80)

    verified = rates_df.filter(pl.col("actual_pp").is_not_null())
    matches = verified.filter(pl.col("pp_diff").abs() < 0.02)
    mismatches = verified.filter(pl.col("pp_diff").abs() >= 0.02)

    print(f"\nTotal verified: {len(verified)}")
    print(f"Matches (PP diff < $0.02): {len(matches)} ({len(matches)/len(verified)*100:.1f}%)")
    print(f"Mismatches: {len(mismatches)} ({len(mismatches)/len(verified)*100:.1f}%)")

    if len(mismatches) > 0:
        print("\nMismatches (PP diff >= $0.02):")
        print(mismatches.select([
            "weight_lbs", "zone", "undiscounted", "discount_pct",
            "discounted", "calculated_pp", "actual_pp", "pp_diff"
        ]).sort(["zone", "weight_lbs"]).head(30))

    # Pivot to create final rate card
    print("\n" + "=" * 80)
    print("GENERATED RATE CARD")
    print("=" * 80)

    rate_card = rates_df.select(["weight_lbs", "zone", "discounted"]).pivot(
        index="weight_lbs",
        on="zone",
        values="discounted"
    ).sort("weight_lbs")

    # Rename zone columns
    for col in rate_card.columns:
        if col != "weight_lbs" and col.isdigit():
            rate_card = rate_card.rename({col: f"zone_{col}"})

    print("\nFirst 50 rows:")
    print(rate_card.head(50))

    # Save rate card
    output_path = Path(__file__).parent / "generated_rates_home_delivery.csv"
    rate_card.write_csv(output_path)
    print(f"\nSaved to: {output_path}")

    # Also show comparison with current rates
    print("\n" + "=" * 80)
    print("COMPARISON WITH CURRENT RATE CARD")
    print("=" * 80)

    current_rates = pl.read_csv(
        Path(__file__).parent.parent / "data" / "reference" / "base_rates_home_delivery.csv"
    )

    # Sample comparison for zone 2
    print("\nZone 2 comparison (first 50 weights):")
    comparison = pl.DataFrame({
        "weight": rate_card["weight_lbs"].head(50),
        "new_rate": rate_card["zone_2"].head(50),
        "old_rate": current_rates["zone_2"].head(50)
    }).with_columns(
        (pl.col("new_rate") - pl.col("old_rate")).round(2).alias("diff")
    )
    print(comparison)


if __name__ == "__main__":
    main()
