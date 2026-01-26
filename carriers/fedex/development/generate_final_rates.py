"""
Generate the final correct discounted rate card for FedEx Home Delivery.

Discount structure discovered from invoice analysis:
- Weight 1, Zones 2-4: Minimum rate $8.07
- Weight 1, Zone 5: $8.16
- Weight 1, Zone 6: $8.44
- Weight 1, Zone 7: $8.57
- Weight 1, Zone 8: $8.72
- Weight 2-5: 38.48% discount
- Weight 6-10: 40.48% discount
- Weight 11-20: 43.48% discount
- Weight 21-30: 47.48% discount
- Weight 31-39: 49.49% discount
- Weight 40: 52.99% discount (special tier)
- Weight 41+: 49.49% discount
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
from datetime import date
import polars as pl

INVOICE_PARQUET = Path(__file__).parent / "invoice_data.parquet"
UNDISCOUNTED_RATES = Path(__file__).parent.parent / "temp_files" / "fedex_ground_rates_2025_undiscounted.csv"


# Weight 1 fixed net rates by zone
WEIGHT_1_NET_RATES = {
    2: 8.07,
    3: 8.07,
    4: 8.07,
    5: 8.16,
    6: 8.44,
    7: 8.57,
    8: 8.72,
}

# Minimum rate floor (applies when calculated rate would be lower)
MINIMUM_RATE = 8.07


def get_discount_rate(weight: int) -> float:
    """Return the discount percentage for a given weight."""
    if weight <= 5:
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


def calculate_net_rate(weight: int, zone: int, undiscounted: float) -> float:
    """Calculate the net rate after discount."""
    if weight == 1:
        return WEIGHT_1_NET_RATES.get(zone, undiscounted * (1 - 0.3641))
    else:
        discount = get_discount_rate(weight)
        calculated = round(undiscounted * (1 - discount), 2)
        # Apply minimum rate floor
        return max(calculated, MINIMUM_RATE)


def main():
    # Load undiscounted rates
    print("Loading undiscounted rates...")
    undiscounted_df = pl.read_csv(UNDISCOUNTED_RATES)

    # Unpivot to long format
    undiscounted_long = undiscounted_df.unpivot(
        index="Weight_lbs",
        variable_name="zone_col",
        value_name="undiscounted_rate"
    ).with_columns([
        pl.col("zone_col").str.replace("Zone", "").cast(pl.Int64).alias("zone"),
        pl.col("Weight_lbs").cast(pl.Int64).alias("weight_lbs")
    ]).select(["weight_lbs", "zone", "undiscounted_rate"])

    # Calculate discounted rates
    print("\nCalculating discounted rates...")
    rates_list = []
    for row in undiscounted_long.iter_rows(named=True):
        weight = row["weight_lbs"]
        zone = row["zone"]
        undiscounted = row["undiscounted_rate"]
        net_rate = calculate_net_rate(weight, zone, undiscounted)
        rates_list.append({
            "weight_lbs": weight,
            "zone": zone,
            "undiscounted": undiscounted,
            "net_rate": net_rate
        })

    rates_df = pl.DataFrame(rates_list)

    # Verify against invoice data
    print("\nLoading invoice data for verification...")
    invoice_df = pl.read_parquet(INVOICE_PARQUET)
    pp_df = invoice_df.filter(
        (pl.col("invoice_date") >= date(2025, 7, 1)) &
        (pl.col("invoice_date") <= date(2025, 12, 31)) &
        (pl.col("service_type") == "Home Delivery") &
        (pl.col("charge_description") == "Performance Pricing")
    )

    # Calculate actual net rate from invoice
    actual_net = pp_df.with_columns([
        pl.col("rated_weight").cast(pl.Int64),
        pl.col("shipping_zone").cast(pl.Int64),
        (pl.col("transportation_charge_usd").cast(pl.Float64) +
         pl.col("charge_description_amount").cast(pl.Float64)).round(2).alias("actual_net")
    ]).group_by(["rated_weight", "shipping_zone"]).agg([
        pl.col("actual_net").mode().first().alias("actual_net_mode"),
        pl.len().alias("count")
    ])

    # Join and compare
    verification = rates_df.join(
        actual_net,
        left_on=["weight_lbs", "zone"],
        right_on=["rated_weight", "shipping_zone"],
        how="left"
    ).with_columns(
        (pl.col("net_rate") - pl.col("actual_net_mode")).round(2).alias("diff")
    )

    verified = verification.filter(pl.col("actual_net_mode").is_not_null())
    matches = verified.filter(pl.col("diff").abs() < 0.02)
    mismatches = verified.filter(pl.col("diff").abs() >= 0.02)

    print("\n" + "=" * 80)
    print("VERIFICATION RESULTS")
    print("=" * 80)
    print(f"\nTotal weight/zone combinations with invoice data: {len(verified)}")
    print(f"Matches (diff < $0.02): {len(matches)} ({len(matches)/len(verified)*100:.1f}%)")
    print(f"Mismatches: {len(mismatches)} ({len(mismatches)/len(verified)*100:.1f}%)")

    if len(mismatches) > 0:
        print("\nMismatches:")
        print(mismatches.select([
            "weight_lbs", "zone", "undiscounted", "net_rate", "actual_net_mode", "diff", "count"
        ]).sort(["zone", "weight_lbs"]))

    # Pivot to create rate card
    rate_card = rates_df.select(["weight_lbs", "zone", "net_rate"]).pivot(
        index="weight_lbs",
        on="zone",
        values="net_rate"
    ).sort("weight_lbs")

    # Rename columns
    for col in rate_card.columns:
        if col != "weight_lbs" and col.isdigit():
            rate_card = rate_card.rename({col: f"zone_{col}"})

    print("\n" + "=" * 80)
    print("FINAL RATE CARD (First 50 weights)")
    print("=" * 80)
    print(rate_card.head(50))

    # Save
    output_path = Path(__file__).parent / "final_rates_home_delivery.csv"
    rate_card.write_csv(output_path)
    print(f"\nSaved to: {output_path}")

    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY: OLD vs NEW RATES")
    print("=" * 80)

    old_rates = pl.read_csv(
        Path(__file__).parent.parent / "data" / "reference" / "base_rates_home_delivery.csv"
    )

    # Compare zone 4 (most common)
    print("\nZone 4 comparison (sample weights):")
    sample_weights = [1, 5, 10, 20, 30, 40, 50, 70, 100, 150]
    for w in sample_weights:
        if w <= len(rate_card):
            new_val = rate_card.filter(pl.col("weight_lbs") == w)["zone_4"][0]
            old_val = old_rates.filter(pl.col("weight_lbs") == w)["zone_4"][0]
            diff = new_val - old_val
            print(f"  Weight {w:3d}: old=${old_val:7.2f}, new=${new_val:7.2f}, diff={diff:+.2f}")


if __name__ == "__main__":
    main()
