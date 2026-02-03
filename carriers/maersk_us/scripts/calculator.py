"""
Maersk US Shipping Cost Calculator
==================================

Interactive CLI tool to calculate expected shipping costs for a single shipment.

Usage:
    python -m carriers.maersk_us.scripts.calculator
"""

import polars as pl
from datetime import date

from carriers.maersk_us.calculate_costs import calculate_costs
from carriers.maersk_us.version import VERSION


def get_user_input() -> dict:
    """Prompt user for shipment details."""
    print("\n=== Maersk US Domestic Last Mile Cost Calculator ===")
    print(f"Version: {VERSION}\n")

    # Dimensions
    length = float(input("Length (inches): "))
    width = float(input("Width (inches): "))
    height = float(input("Height (inches): "))
    weight = float(input("Weight (lbs, max 70): "))

    if weight > 70:
        print("\nWarning: Maersk US max weight is 70 lbs")

    # Destination
    zip_code = input("Destination ZIP code: ").strip()
    region = input("Destination state (e.g., Texas): ").strip()

    # Production site (fixed for Maersk US)
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

    # Weight calculations
    print(f"\nBillable weight: {row['billable_weight_lbs']:.2f} lbs", end="")
    if row['uses_dim_weight']:
        print(f" (dimensional: {row['dim_weight_lbs']:.2f} lbs)")
    else:
        print(" (actual)")

    # Surcharges triggered
    surcharges = []
    if row['surcharge_nsl1']:
        surcharges.append("NSL1 (Length >21\")")
    if row['surcharge_nsl2']:
        surcharges.append("NSL2 (Length >30\")")
    if row['surcharge_nsd']:
        surcharges.append("NSD (Volume >2 cu ft)")
    if row['surcharge_pickup']:
        surcharges.append("Pickup Fee")

    print(f"\nSurcharges: {', '.join(surcharges) if surcharges else 'None'}")

    # Cost breakdown
    print("\n--- Cost Breakdown ---")
    print(f"Base rate:          ${row['cost_base']:>8.2f}")

    if row['cost_nsl1'] > 0:
        print(f"NSL1 surcharge:     ${row['cost_nsl1']:>8.2f}")
    if row['cost_nsl2'] > 0:
        print(f"NSL2 surcharge:     ${row['cost_nsl2']:>8.2f}")
    if row['cost_nsd'] > 0:
        print(f"NSD surcharge:      ${row['cost_nsd']:>8.2f}")
    if row['cost_pickup'] > 0:
        print(f"Pickup fee:         ${row['cost_pickup']:>8.2f}  (${0.04}/lb x {row['billable_weight_lbs']:.2f} lbs)")

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
