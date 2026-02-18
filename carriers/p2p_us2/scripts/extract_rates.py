"""
Extract Reference Data from P2P US2 Rate Card Excel

One-time script to generate:
    - data/reference/zones.csv         (93,100 rows: zip, zone, is_remote)
    - data/reference/base_rates_pfa.csv (360 rows: 45 tiers x 8 zones)
    - data/reference/base_rates_pfs.csv (666 rows: 74 tiers x 9 zones)

Source: temp_files/P2PG_PicaNova_DomesticRates_20260212.xlsx

Usage:
    python -m carriers.p2p_us2.scripts.extract_rates
"""

import re
from pathlib import Path

import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

TEMP_DIR = Path(__file__).parent.parent / "temp_files"
EXCEL_FILE = TEMP_DIR / "P2PG_PicaNova_DomesticRates_20260212.xlsx"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "reference"


# =============================================================================
# ZONES
# =============================================================================

def extract_zones() -> pd.DataFrame:
    """
    Extract ZIP-to-zone mapping from PFA_Zip_ORD sheet.

    Parses "remote X" zone values -> zone=X, is_remote=True.
    Standard numeric zones -> is_remote=False.
    """
    df = pd.read_excel(EXCEL_FILE, sheet_name="PFA_Zip_ORD")

    # Normalize column names
    df.columns = [str(c).strip() for c in df.columns]

    # Extract ZIP and Zone columns
    zip_col = [c for c in df.columns if "zip" in c.lower() and "3" not in c][0]
    zone_col = [c for c in df.columns if c.strip().lower() == "zone"][0]

    result = pd.DataFrame({
        "zip": df[zip_col].astype(str).str.zfill(5),
        "_raw_zone": df[zone_col].astype(str).str.strip(),
    })

    # Parse zone values: "remote X" -> zone=X, is_remote=True
    def parse_zone(raw):
        match = re.match(r"remote\s+(\d+)", str(raw), re.IGNORECASE)
        if match:
            return int(match.group(1)), True
        return int(float(raw)), False

    parsed = result["_raw_zone"].apply(parse_zone)
    result["zone"] = parsed.apply(lambda x: x[0])
    result["is_remote"] = parsed.apply(lambda x: x[1])

    result = result[["zip", "zone", "is_remote"]].copy()

    return result


# =============================================================================
# PFA RATES
# =============================================================================

def extract_pfa_rates() -> pd.DataFrame:
    """
    Extract PFA base rates from PFA sheet.

    Weight brackets: 15 ounce brackets + 30 pound brackets = 45 tiers.
    Zones: 1-8.
    Output: 45 x 8 = 360 rows.
    """
    df = pd.read_excel(EXCEL_FILE, sheet_name="PFA", header=None)

    # Find the header row containing "Weight" and "Zone N"
    header_row = None
    for i, row in df.iterrows():
        vals = [str(v).strip() for v in row.values]
        if any("Weight" in v for v in vals):
            header_row = i
            break

    if header_row is None:
        raise ValueError("Could not find header row in PFA sheet")

    # Use header row to identify columns
    headers = [str(v).strip() for v in df.iloc[header_row].values]

    weight_col_idx = next(i for i, h in enumerate(headers) if "Weight" in h)
    zone_col_map = {}
    for idx, h in enumerate(headers):
        match = re.match(r"Zone\s+(\d+)", h, re.IGNORECASE)
        if match:
            zone_col_map[int(match.group(1))] = idx

    # Process data rows after header
    rows = []
    prev_upper = 0.0

    for i in range(header_row + 1, len(df)):
        raw_weight = str(df.iloc[i, weight_col_idx]).strip()
        if not raw_weight or raw_weight == "nan":
            continue

        upper = _parse_weight(raw_weight)
        if upper is None:
            continue

        for zone_num in sorted(zone_col_map.keys()):
            rate = df.iloc[i, zone_col_map[zone_num]]
            if pd.isna(rate):
                continue
            rows.append({
                "weight_lbs_lower": round(prev_upper, 6),
                "weight_lbs_upper": round(upper, 6),
                "zone": zone_num,
                "rate": round(float(rate), 2),
            })

        prev_upper = upper

    return pd.DataFrame(rows)


# =============================================================================
# PFS RATES
# =============================================================================

def extract_pfs_rates() -> pd.DataFrame:
    """
    Extract PFS base rates from PFS sheet.

    Weight brackets: 4 ounce brackets + 70 pound brackets = 74 tiers.
    Zones: 1-9.
    Output: 74 x 9 = 666 rows.
    Skips "Oversized" row.

    Sheet layout:
        Row 2: "Weight Not Over (ounces)" section label
        Row 3: Zone headers (Zone 1 through Zone 9)
        Rows 4-7: Ounce data (4, 8, 12, 15.999)
        Row 8: "Weight Not Over (pounds)" section label
        Rows 9+: Pound data (1, 2, ..., 70, Oversized)
    """
    df = pd.read_excel(EXCEL_FILE, sheet_name="PFS", header=None)

    col0 = df.iloc[:, 0].astype(str)

    # Find section headers
    oz_header_idx = None
    lb_header_idx = None
    for i, val in col0.items():
        if "ounce" in val.lower() and "weight" in val.lower():
            oz_header_idx = i
        if "pound" in val.lower() and "weight" in val.lower():
            lb_header_idx = i

    # Find zone header row (row after ounce header, contains "Zone N")
    zone_header_idx = oz_header_idx + 1
    zone_col_map = {}
    for col_idx in range(len(df.columns)):
        val = str(df.iloc[zone_header_idx, col_idx]).strip()
        match = re.match(r"Zone\s+(\d+)", val, re.IGNORECASE)
        if match:
            zone_col_map[int(match.group(1))] = col_idx

    rows = []
    prev_upper = 0.0

    # Extract ounce section (starts after zone header row)
    for i in range(zone_header_idx + 1, lb_header_idx):
        raw_weight = str(df.iloc[i, 0]).strip()
        if not raw_weight or raw_weight == "nan":
            continue

        upper = _parse_weight_value(raw_weight, unit="oz")
        if upper is None:
            continue

        for zone_num in sorted(zone_col_map.keys()):
            rate = df.iloc[i, zone_col_map[zone_num]]
            if pd.isna(rate):
                continue
            rows.append({
                "weight_lbs_lower": round(prev_upper, 6),
                "weight_lbs_upper": round(upper, 6),
                "zone": zone_num,
                "rate": round(float(rate), 2),
            })

        prev_upper = upper

    # Extract pound section (starts after pound header)
    for i in range(lb_header_idx + 1, len(df)):
        raw_weight = str(df.iloc[i, 0]).strip()
        if not raw_weight or raw_weight == "nan":
            continue
        if "oversize" in raw_weight.lower():
            continue

        upper = _parse_weight_value(raw_weight, unit="lbs")
        if upper is None:
            continue

        for zone_num in sorted(zone_col_map.keys()):
            rate = df.iloc[i, zone_col_map[zone_num]]
            if pd.isna(rate):
                continue
            rows.append({
                "weight_lbs_lower": round(prev_upper, 6),
                "weight_lbs_upper": round(upper, 6),
                "zone": zone_num,
                "rate": round(float(rate), 2),
            })

        prev_upper = upper

    return pd.DataFrame(rows)


# =============================================================================
# HELPERS
# =============================================================================

def _parse_weight(raw: str) -> float | None:
    """Parse PFA weight string like '5 oz' or '10 lbs' into lbs upper bound."""
    raw = raw.strip().lower()

    # Match "N oz" or "N lbs"
    match = re.match(r"([\d.]+)\s*(oz|lbs?)", raw)
    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2)

    if unit == "oz":
        return value / 16.0
    else:  # lbs
        return value


def _parse_weight_value(raw: str, unit: str) -> float | None:
    """Parse a numeric weight value with known unit."""
    try:
        value = float(raw)
    except ValueError:
        return None

    if unit == "oz":
        return value / 16.0
    else:  # lbs
        return value


# =============================================================================
# MAIN
# =============================================================================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Reading: {EXCEL_FILE.name}")
    print()

    # Zones
    print("Extracting zones...")
    zones = extract_zones()
    zones_path = OUTPUT_DIR / "zones.csv"
    zones.to_csv(zones_path, index=False)
    print(f"  {len(zones):,} ZIPs -> {zones_path.name}")
    print(f"  Zone distribution: {dict(zones['zone'].value_counts().sort_index())}")
    print(f"  Remote ZIPs: {zones['is_remote'].sum():,}")

    # PFA rates
    print("\nExtracting PFA rates...")
    pfa = extract_pfa_rates()
    pfa_path = OUTPUT_DIR / "base_rates_pfa.csv"
    pfa.to_csv(pfa_path, index=False)
    tiers_pfa = pfa["weight_lbs_upper"].nunique()
    zones_pfa = pfa["zone"].nunique()
    print(f"  {len(pfa):,} rows ({tiers_pfa} tiers x {zones_pfa} zones) -> {pfa_path.name}")
    print(f"  Weight range: {pfa['weight_lbs_lower'].min():.4f} - {pfa['weight_lbs_upper'].max():.1f} lbs")
    print(f"  Zones: {sorted(pfa['zone'].unique())}")

    # PFS rates
    print("\nExtracting PFS rates...")
    pfs = extract_pfs_rates()
    pfs_path = OUTPUT_DIR / "base_rates_pfs.csv"
    pfs.to_csv(pfs_path, index=False)
    tiers_pfs = pfs["weight_lbs_upper"].nunique()
    zones_pfs = pfs["zone"].nunique()
    print(f"  {len(pfs):,} rows ({tiers_pfs} tiers x {zones_pfs} zones) -> {pfs_path.name}")
    print(f"  Weight range: {pfs['weight_lbs_lower'].min():.4f} - {pfs['weight_lbs_upper'].max():.1f} lbs")
    print(f"  Zones: {sorted(pfs['zone'].unique())}")

    print("\nDone!")


if __name__ == "__main__":
    main()
