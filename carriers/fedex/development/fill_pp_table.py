"""
Fill in missing values in performance_pricing.csv using discovered discount tiers.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
import polars as pl

RATE_TABLES = Path(__file__).parent / "final_rate_tables"


def get_discount_pct(weight: int) -> float:
    """Return discount percentage for a given weight."""
    if weight == 1:
        return 0.3641  # Average for weight 1
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
    # Load tables
    print("Loading tables...")
    undiscounted = pl.read_csv(RATE_TABLES / "undiscounted_rates.csv")
    pp_existing = pl.read_csv(RATE_TABLES / "performance_pricing.csv")

    print(f"Undiscounted: {undiscounted.shape}")
    print(f"PP existing: {pp_existing.shape}")

    zones = ["zone_2", "zone_3", "zone_4", "zone_5", "zone_6", "zone_7", "zone_8"]

    # Create lookup from existing PP values
    existing_lookup = {}
    for row in pp_existing.iter_rows(named=True):
        weight = row["weight_lbs"]
        for zone in zones:
            val = row.get(zone)
            if val is not None and str(val) != "":
                existing_lookup[(weight, zone)] = val

    print(f"Existing PP values: {len(existing_lookup)}")

    # Build complete PP table
    filled_count = 0
    pp_data = []
    for row in undiscounted.iter_rows(named=True):
        weight = row["weight_lbs"]
        discount = get_discount_pct(weight)

        pp_row = {"weight_lbs": weight}
        for zone in zones:
            # Check if we have existing value
            if (weight, zone) in existing_lookup:
                pp_row[zone] = existing_lookup[(weight, zone)]
            else:
                # Calculate from undiscounted rate
                undiscounted_rate = row[zone]
                pp_value = round(-undiscounted_rate * discount, 2)
                pp_row[zone] = pp_value
                filled_count += 1

        pp_data.append(pp_row)

    pp_final = pl.DataFrame(pp_data)

    print(f"\nFilled {filled_count} missing values")
    print(f"Final PP table: {pp_final.shape}")
    print("\nFirst 20 rows:")
    print(pp_final.head(20))

    # Save
    output_path = RATE_TABLES / "performance_pricing.csv"
    pp_final.write_csv(output_path)
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
