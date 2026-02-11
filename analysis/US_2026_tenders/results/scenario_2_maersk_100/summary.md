# Scenario 2: 100% Maersk

## Executive Summary

This scenario calculates the total shipping cost if 100% of US shipment volume were routed to Maersk US, a carrier not currently used in the production system. **Maersk would cost $6.04M vs the current mix of $5.83M, representing a 3.6% ($208K) increase**. With the corrected SmartPost pricing, the current mix is now cheaper than Maersk. Maersk has strong savings on lightweight packages (0-4 lbs) but becomes significantly more expensive for mid-to-heavy weight shipments due to high base rates and a dramatic rate jump at 30 lbs.

## Methodology

Maersk US shipping costs are calculated as:

**Cost = Base Rate + Surcharges + Pickup Fee**

Where:
- **Base Rate**: Determined by zone (1-9) and billable weight. Rates range from $3.11 (light, Zone 1) to $175.85 (heavy, Zone 9). A significant rate jump occurs at 30 lbs.
- **Billable Weight**: MAX(actual weight, dimensional weight), where DIM weight = cubic inches / 166. DIM only applies to packages over 1,728 cu in (1 cubic foot).
- **Surcharges**:
  - NSL1: $4.00 for packages with longest side > 21" (mutually exclusive with NSL2)
  - NSL2: $4.00 for packages with longest side > 30"
  - NSD: $18.00 for packages > 3,456 cubic inches (2 cu ft)
  - NSL and NSD can stack
- **Pickup Fee**: $0.04 per billable pound (always applies)
- **No fuel surcharge** - included in base rates

## Results

### Total Cost

| Metric                        | Value                       |
|-------------------------------|-----------------------------|
| Total Shipments               | 558,013                     |
| Current Mix Total             | $5,833,893.77               |
| 100% Maersk Total             | $6,041,478.28               |
| **Difference**                | **+$207,584.51 (+3.6%)**    |
| Avg Cost/Shipment (Current)   | $10.45                      |
| Avg Cost/Shipment (Maersk)    | $10.83                      |

### Carrier Ranking (Full Coverage Only)

| Rank   | Carrier       | Serviceable   | Total Cost       | Avg Cost   |
|--------|---------------|---------------|------------------|------------|
| 1      | Current Mix   | 558,013       | $5,833,894       | $10.45     |
| 2      | FedEx         | 558,013       | $5,889,066       | $10.55     |
| 3      | Maersk        | 558,013       | $6,041,478       | $10.83     |
| 4      | USPS          | 558,013       | $14,835,549      | $26.59     |

*Note: OnTrac (64.5% coverage) and P2P (51.8% coverage) excluded - cannot service all shipments*

### Cost by Weight Bracket

The 30 lb rate jump is a critical cost driver for Maersk. The table below shows the breakdown between base rate and surcharges:

| Weight Bracket   | Shipments   | Current Avg   | Maersk Avg   | Base Rate   | Surcharges   | Diff %    |
|------------------|-------------|---------------|--------------|-------------|--------------|-----------|
| 0-1 lbs          | 145,687     | $6.74         | $4.62        | $4.15       | $0.47        | -31%      |
| 1-2 lbs          | 113,398     | $8.61         | $5.37        | $5.17       | $0.21        | -38%      |
| 2-3 lbs          | 96,338      | $9.78         | $7.47        | $5.56       | $1.91        | -24%      |
| 3-4 lbs          | 43,900      | $11.82        | $8.87        | $6.35       | $2.52        | -25%      |
| 4-5 lbs          | 41,160      | $11.67        | $12.28       | $7.43       | $4.85        | +5%       |
| 5-10 lbs         | 87,898      | $15.08        | $21.12       | $9.35       | $11.77       | +40%      |
| 10-20 lbs        | 24,071      | $19.22        | $37.06       | $17.44      | $19.62       | +93%      |
| 20-30 lbs        | 3,678       | $23.92        | $72.31       | $49.38      | $22.93       | +202%     |
| 30+ lbs          | 1,883       | $31.66        | $99.95       | $75.71      | $24.24       | +216%     |

**Key insight:** Surcharges stay relatively flat ($20-24) for heavier packages, while the **base rate** is the primary cost driver - jumping from $49 (20-30 lbs) to $76 (30-70 lbs) due to Maersk's 30 lb rate jump.

**The 30 lb Rate Jump:**

| Zone     | 29-30 lbs Rate   | 30-31 lbs Rate   | Increase              |
|----------|------------------|------------------|-----------------------|
| Zone 1   | $7.61            | $22.40           | +$14.79 (+194%)       |
| Zone 5   | $11.81           | $45.18           | +$33.37 (+283%)       |
| Zone 8   | $20.36           | $73.60           | +$53.24 (+262%)       |

While only 0.3% of shipments exceed 30 lbs, they represent 3.1% of Maersk's total cost.

### Cost by Zone

| Zone   | Shipments   | % of Total   | Current Avg   | Maersk Avg   | Difference        |
|--------|-------------|--------------|---------------|--------------|-------------------|
| 1      | 4,321       | 0.8%         | $8.70         | $8.50        | -$0.20 (-2%)      |
| 2      | 20,994      | 3.8%         | $8.57         | $8.13        | -$0.44 (-5%)      |
| 3      | 57,898      | 10.4%        | $9.09         | $8.80        | -$0.28 (-3%)      |
| 4      | 194,013     | 34.8%        | $9.51         | $9.61        | +$0.10 (+1%)      |
| 5      | 132,018     | 23.7%        | $10.38        | $10.82       | +$0.44 (+4%)      |
| 6      | 38,034      | 6.8%         | $11.46        | $12.32       | +$0.86 (+8%)      |
| 7      | 35,760      | 6.4%         | $12.84        | $14.09       | +$1.25 (+10%)     |
| 8      | 73,222      | 13.1%        | $12.90        | $13.56       | +$0.66 (+5%)      |
| 9      | 1,753       | 0.3%         | $20.42        | $37.69       | +$17.26 (+85%)    |

Maersk is cheaper only in zones 1-3. In zones 4-9, the current carrier mix (with corrected SmartPost pricing) is now cheaper.

### Surcharge Breakdown

| Component         | Total Cost     | % of Total   | Shipments Affected   |
|-------------------|----------------|--------------|----------------------|
| Base Rate         | $3,870,329     | 64.1%        | 558,013 (100%)       |
| NSD (>2 cu ft)    | $1,091,988     | 18.1%        | 60,666 (10.9%)       |
| NSL2 (>30")       | $515,840       | 8.5%         | 128,960 (23.1%)      |
| NSL1 (>21")       | $417,884       | 6.9%         | 104,471 (18.7%)      |
| Pickup Fee        | $145,437       | 2.4%         | 558,013 (100%)       |

**Key Insight:** 41.8% of shipments trigger length surcharges (NSL1 or NSL2), and 10.9% trigger the volume surcharge (NSD). Surcharge overlap (NSL + NSD) affects 10.9% of shipments, adding $22 per package.

### Top Cost Drivers

**Package types where Maersk is EXPENSIVE:**

| Package Type                    | Shipments   | Avg Weight   | Current Avg   | Maersk Avg   | Diff    |
|---------------------------------|-------------|--------------|---------------|--------------|---------|
| PIZZA BOX 42x32x2 (2x str)      | 2,910       | 22.4 lbs     | $32.34        | $92.27       | +185%   |
| PIZZA BOX 42x32x2               | 24,809      | 8.9 lbs      | $26.68        | $32.66       | +22%    |
| PIZZA BOX 48X36X1               | 19,768      | 8.0 lbs      | $31.49        | $35.62       | +13%    |

**Package types where Maersk is CHEAP:**

| Package Type                    | Shipments   | Avg Weight   | Current Avg   | Maersk Avg   | Diff    |
|---------------------------------|-------------|--------------|---------------|--------------|---------|
| PIZZA BOX 40x30x1               | 21,002      | 3.3 lbs      | $19.76        | $9.99        | -49%    |
| PIZZA BOX 20x16x1               | 117,206     | 1.3 lbs      | $8.40         | $4.98        | -41%    |
| MIXPIX BOX                      | 3,239       | 1.3 lbs      | $8.54         | $4.89        | -43%    |
| PIZZA BOX 20x16x2               | 36,316      | 3.2 lbs      | $9.81         | $5.91        | -40%    |
| PIZZA BOX 16x12x2               | 43,674      | 2.2 lbs      | $9.09         | $5.48        | -40%    |

## Key Findings

1. **Maersk is 3.6% more expensive than current mix** (+$208K) for full volume. With corrected SmartPost pricing, the current mix is now cheaper than Maersk. FedEx ($5.89M) is also cheaper than Maersk.

2. **Still dominant for lightweight packages (0-4 lbs)**: These represent 72% of shipments and show 25-38% cost savings vs current mix, but this no longer offsets the higher costs for heavier shipments.

3. **The 30 lb rate jump is devastating**: Base rates nearly triple at the 30 lb threshold across all zones. Fortunately, only 0.3% of shipments exceed this weight.

4. **Surcharges are significant**: 35.9% of total cost comes from surcharges (NSL1/NSL2/NSD/Pickup), with the $18 NSD surcharge being the largest individual contributor.

5. **Zone pricing less favorable with SmartPost fix**: Maersk is now cheaper only in zones 1-3. The corrected SmartPost rates make the current mix cheaper in zones 4-9.

6. **No fuel surcharge advantage**: Unlike competitors, Maersk has no separate fuel surcharge - this is built into base rates.

## Recommendation

**Maersk is no longer the cheapest full-coverage carrier** - at +3.6% vs current mix, it costs $208K more annually. FedEx (with SmartPost) is now the cheapest full-coverage alternative at +0.9%.

Maersk would be even more valuable in a **selective routing strategy** for:
- Lightweight packages (0-4 lbs) - saves 28-42% vs current mix
- Packages under 21" longest dimension (avoids NSL surcharges)
- Any zone (Maersk is cheaper in 8 of 9 zones)

**Avoid routing to Maersk:**
- Packages over 10 lbs (rates become uncompetitive vs other carriers)
- Large packages over 2 cubic feet (NSD surcharge adds $18)
- Packages approaching 30 lb threshold (massive rate jump)

---

*Analysis generated: February 2026*
*Data source: `shipments_aggregated.parquet` and `shipments_unified.parquet`*
*Script: `scenario_2_maersk_100.py`*
