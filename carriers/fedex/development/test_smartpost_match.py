"""
Test SmartPost match rate using pcs_trackingnumber (crossref fields).
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from shared.database import pull_data


def main():
    print("=" * 80)
    print("SMARTPOST MATCH RATE TEST")
    print("=" * 80)

    # Pull SmartPost invoice data with pcs_trackingnumber
    print("\n1. Loading SmartPost invoice data (Nov-Dec 2025)...")
    invoice_query = """
    SELECT DISTINCT
        CASE
            WHEN f.express_or_ground_tracking_id LIKE '%.%'
            THEN f.express_or_ground_tracking_id::numeric::text
            ELSE f.express_or_ground_tracking_id::text
        END AS trackingnumber,
        f.crossreftrackingid_prefix || f.crossreftrackingid AS pcs_trackingnumber,
        f.invoice_date::date AS invoice_date,
        f.service_type
    FROM bi_stage_dev_dbo.fedex_invoicedata_historical f
    WHERE f.invoice_date::date >= '2025-11-01'
      AND f.invoice_date::date <= '2025-12-31'
      AND f.service_type = 'SmartPost'
    """
    invoice_df = pull_data(invoice_query)
    print(f"   SmartPost shipments: {len(invoice_df):,}")

    # Check how many have pcs_trackingnumber
    has_pcs_tn = invoice_df.filter(invoice_df["pcs_trackingnumber"].is_not_null())
    print(f"   With pcs_trackingnumber: {len(has_pcs_tn):,} ({len(has_pcs_tn)/len(invoice_df)*100:.1f}%)")

    # Load PCS data for SmartPost (FXESPPS)
    print("\n2. Loading PCS data (FXESPPS, Oct-Dec 2025)...")
    pcs_query = """
    WITH trackingnumbers AS (
        SELECT orderid, trackingnumber,
            ROW_NUMBER() OVER (PARTITION BY orderid ORDER BY id DESC) AS row_nr
        FROM bi_stage_dev_dbo.pcsu_sentparcels
    )
    SELECT DISTINCT
        tn.trackingnumber
    FROM bi_stage_dev_dbo.pcsu_orders po
    JOIN bi_stage_dev_dbo.pcsu_productionsites pp ON pp.id = po.productionsiteid
    JOIN bi_stage_dev_dbo.pcsu_shippingproviders ps ON ps.id = po.shippingproviderid
    LEFT JOIN trackingnumbers tn ON tn.orderid = po.id AND tn.row_nr = 1
    WHERE ps.extkey = 'FXESPPS'
      AND pp."name" IN ('Columbus', 'Phoenix')
      AND po.createddate >= '2025-10-01'
      AND po.createddate <= '2025-12-31'
      AND tn.trackingnumber IS NOT NULL
    """
    pcs_df = pull_data(pcs_query)
    print(f"   PCS SmartPost shipments: {len(pcs_df):,}")

    # Test match on original trackingnumber
    print("\n3. Testing match rates...")

    # Join on original trackingnumber
    matched_original = invoice_df.join(
        pcs_df,
        on="trackingnumber",
        how="inner"
    )
    print(f"\n   Match on trackingnumber (original): {len(matched_original):,} / {len(invoice_df):,} ({len(matched_original)/len(invoice_df)*100:.1f}%)")

    # Join on pcs_trackingnumber
    matched_pcs = has_pcs_tn.join(
        pcs_df,
        left_on="pcs_trackingnumber",
        right_on="trackingnumber",
        how="inner"
    )
    print(f"   Match on pcs_trackingnumber: {len(matched_pcs):,} / {len(invoice_df):,} ({len(matched_pcs)/len(invoice_df)*100:.1f}%)")

    # Show sample of pcs_trackingnumber values
    print("\n   Sample pcs_trackingnumber values:")
    print(has_pcs_tn.select(["trackingnumber", "pcs_trackingnumber"]).head(10))


if __name__ == "__main__":
    main()
