"""
P2P US Shipping Cost Calculator
===============================

Interactive CLI tool to calculate expected shipping costs for a single shipment.

Usage:
    python -m carriers.p2p_us.scripts.calculator
"""

import polars as pl
from datetime import date

from carriers.p2p_us.calculate_costs import calculate_costs
from carriers.p2p_us.version import VERSION


def get_user_input() -> dict:
    """Prompt user for shipment details."""
    print("\n=== P2P Parcel Flex Advantage Plus Cost Calculator ===")
    print(f"Version: {VERSION}\n")

    # Dimensions
    length = float(input("Length (inches): "))
    width = float(input("Width (inches): "))
    height = float(input("Height (inches): "))
    weight = float(input("Weight (lbs, max 50): "))

    if weight > 50:
        print("\nWarning: P2P US max weight is 50 lbs")

    # Destination
    zip_code = input("Destination ZIP code (5-digit): ").strip()
    region = input("Destination state (e.g., Texas): ").strip()

    # Production site (fixed for P2P US)
    production_site = "Columbus"
    print(f"\nProduction site: {production_site} (fixed)")

    # Ship date
    date_input = input(f"\nShip date (YYYY-MM-DD) [default: {date.today()}]: ").strip()
    if date_input:
        ship_date = date.fromisoformat(date_input)
    else:
        ship_date = date.today()

    return {
        "length_in": length,
        "width_in": width,
        "height_in": height,
        "weight_lbs": weight,
        "shipping_zip_code": zip_code,
        "shipping_region": region,
        "production_site": production_site,
        "ship_date": ship_date,
    }


def create_shipment_df(shipment: dict) -> pl.DataFrame:
    """Create a single-row DataFrame from user input."""
    return pl.DataFrame([{
        "ship_date": shipment["ship_date"],
        "production_site": shipment["production_site"],
        "shipping_zip_code": shipment["shipping_zip_code"],
        "shipping_region": shipment["shipping_region"],
        "length_in": shipment["length_in"],
        "width_in": shipment["width_in"],
        "height_in": shipment["height_in"],
        "weight_lbs": shipment["weight_lbs"],
    }])


def print_results(df: pl.DataFrame, shipment: dict) -> None:
    """Print calculation results."""
    row = df.row(0, named=True)

    print("\n" + "=" * 50)
    print("CALCULATION RESULTS")
    print("=" * 50)

    # Input summary
    print(f"\nShipment: {shipment['length_in']}x{shipment['width_in']}x{shipment['height_in']} in, {shipment['weight_lbs']} lbs")
    print(f"Destination: ZIP {shipment['shipping_zip_code']} (Zone {row['shipping_zone']})")
    print(f"Origin: {shipment['production_site']}")
    print(f"Ship date: {shipment['ship_date']}")

    # Dimensional info
    print(f"\nCubic inches: {row['cubic_in']:.0f}")
    print(f"Longest side: {row['longest_side_in']:.1f} in")
    print(f"Second longest: {row['second_longest_in']:.1f} in")
    print(f"Length + girth: {row['length_plus_girth']:.1f} in")

    # Weight calculations
    print(f"\nDIM weight: {row['dim_weight_lbs']:.2f} lbs")
    print(f"Uses DIM weight: {row['uses_dim_weight']}")
    print(f"Billable weight: {row['billable_weight_lbs']:.2f} lbs", end="")
    if row['uses_dim_weight']:
        print(" (dimensional)")
    else:
        print(" (actual)")

    # Surcharges triggered
    surcharges = []
    if row['surcharge_ahs']:
        surcharges.append("AHS (Additional Handling)")
    if row['surcharge_oversize']:
        surcharges.append("Oversize (>70 lbs)")

    print(f"\nSurcharges: {', '.join(surcharges) if surcharges else 'None'}")

    # Cost breakdown
    print("\n--- Cost Breakdown ---")
    print(f"Base rate:          ${row['cost_base']:>8.2f}")

    if row['cost_ahs'] > 0:
        print(f"AHS surcharge:      ${row['cost_ahs']:>8.2f}")
    if row['cost_oversize'] > 0:
        print(f"Oversize surcharge: ${row['cost_oversize']:>8.2f}")

    print(f"                    {'-' * 9}")
    print(f"Subtotal:           ${row['cost_subtotal']:>8.2f}")
    print(f"                    {'=' * 9}")
    print(f"TOTAL:              ${row['cost_total']:>8.2f}")
    print()


def main():
    """Main entry point."""
    try:
        # Get user input
        shipment = get_user_input()

        # Create single-row DataFrame
        df = create_shipment_df(shipment)

        # Run through pipeline
        df = calculate_costs(df)

        # Print results
        print_results(df, shipment)

    except KeyboardInterrupt:
        print("\n\nCancelled.")
    except Exception as e:
        print(f"\nError: {e}")
        raise


if __name__ == "__main__":
    main()
