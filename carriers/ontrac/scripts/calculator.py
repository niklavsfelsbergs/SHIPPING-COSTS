"""
OnTrac Shipping Cost Calculator
===============================

Interactive CLI tool to calculate expected shipping costs for a single shipment.
"""

import polars as pl
from datetime import date

from carriers.ontrac.calculate_costs import calculate_costs
from carriers.ontrac.version import VERSION


def get_user_input() -> dict:
    """Prompt user for shipment details."""
    print("\n=== OnTrac Shipping Cost Calculator ===")
    print(f"Version: {VERSION}\n")

    # Dimensions
    length = float(input("Length (inches): "))
    width = float(input("Width (inches): "))
    height = float(input("Height (inches): "))
    weight = float(input("Weight (lbs): "))

    # Destination
    zip_code = input("Destination ZIP code: ").strip()
    region = input("Destination state (e.g., Texas): ").strip()

    # Production site
    print("\nProduction site:")
    print("  1. Phoenix")
    print("  2. Columbus")
    site_choice = input("Select (1 or 2): ").strip()
    production_site = "Phoenix" if site_choice == "1" else "Columbus"

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
    print(f"\nBillable weight: {row['billable_weight_lbs']:.1f} lbs", end="")
    if row['uses_dim_weight']:
        print(f" (dimensional: {row['dim_weight_lbs']:.1f} lbs)")
    else:
        print(" (actual)")

    # Surcharges triggered
    surcharges = []
    if row['surcharge_oml']:
        surcharges.append("OML (Over Maximum Limits)")
    if row['surcharge_lps']:
        surcharges.append("LPS (Large Package)")
    if row['surcharge_ahs']:
        surcharges.append("AHS (Additional Handling)")
    if row['surcharge_das']:
        surcharges.append("DAS (Delivery Area)")
    if row['surcharge_edas']:
        surcharges.append("EDAS (Extended Delivery Area)")
    if row['surcharge_res']:
        surcharges.append("RES (Residential - allocated)")

    print(f"\nSurcharges: {', '.join(surcharges) if surcharges else 'None'}")

    # Demand period surcharges
    demand = []
    if row['surcharge_dem_res']:
        demand.append("DEM_RES")
    if row['surcharge_dem_ahs']:
        demand.append("DEM_AHS")
    if row['surcharge_dem_lps']:
        demand.append("DEM_LPS")
    if row['surcharge_dem_oml']:
        demand.append("DEM_OML")

    if demand:
        print(f"Demand surcharges: {', '.join(demand)}")

    # Cost breakdown
    print("\n--- Cost Breakdown ---")
    print(f"Base rate:          ${row['cost_base']:>8.2f}")

    if row['cost_oml'] > 0:
        print(f"OML surcharge:      ${row['cost_oml']:>8.2f}")
    if row['cost_lps'] > 0:
        print(f"LPS surcharge:      ${row['cost_lps']:>8.2f}")
    if row['cost_ahs'] > 0:
        print(f"AHS surcharge:      ${row['cost_ahs']:>8.2f}")
    if row['cost_das'] > 0:
        print(f"DAS surcharge:      ${row['cost_das']:>8.2f}")
    if row['cost_edas'] > 0:
        print(f"EDAS surcharge:     ${row['cost_edas']:>8.2f}")
    if row['cost_res'] > 0:
        print(f"RES (allocated):    ${row['cost_res']:>8.2f}")
    if row['cost_dem_res'] > 0:
        print(f"Demand RES:         ${row['cost_dem_res']:>8.2f}")
    if row['cost_dem_ahs'] > 0:
        print(f"Demand AHS:         ${row['cost_dem_ahs']:>8.2f}")
    if row['cost_dem_lps'] > 0:
        print(f"Demand LPS:         ${row['cost_dem_lps']:>8.2f}")
    if row['cost_dem_oml'] > 0:
        print(f"Demand OML:         ${row['cost_dem_oml']:>8.2f}")

    print(f"                    {'-' * 9}")
    print(f"Subtotal:           ${row['cost_subtotal']:>8.2f}")
    print(f"Fuel surcharge:     ${row['cost_fuel']:>8.2f}")
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
