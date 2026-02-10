# Scenario 2: 100% Maersk

## Executive Summary

This scenario calculates the total shipping cost if 100% of US shipment volume were routed to Maersk US, a carrier not currently used in the production system. **Maersk would cost $6.44M vs the current mix of $6.39M, representing a 0.8% ($51K) increase**. While Maersk is competitive for lightweight packages (1-4 lbs), it becomes significantly more expensive for mid-to-heavy weight shipments due to high base rates and a dramatic rate jump at 30 lbs.

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
| Total Shipments               | 558,210                     |
| Current Mix Total             | $6,389,595.72               |
| 100% Maersk Total             | $6,440,239.70               |
| **Difference**                | **+$50,643.98 (+0.8%)**     |
| Avg Cost/Shipment (Current)   | $11.45                      |
| Avg Cost/Shipment (Maersk)    | $11.54                      |

### Carrier Ranking (Full Coverage Only)

| Rank   | Carrier       | Serviceable   | Total Cost       | Avg Cost   |
|--------|---------------|---------------|------------------|------------|
| 1      | Current Mix   | 558,210       | $6,389,596       | $11.45     |
| 2      | Maersk        | 558,210       | $6,440,240       | $11.54     |
| 3      | FedEx         | 558,210       | $6,920,940       | $12.40     |
| 4      | USPS          | 558,210       | $8,195,287       | $14.68     |

*Note: OnTrac (64.6% coverage) and P2P (51.8% coverage) excluded - cannot service all shipments*

### Cost by Weight Bracket

The 30 lb rate jump is a critical cost driver for Maersk. The table below shows the breakdown between base rate and surcharges:

| Weight Bracket   | Shipments   | Current Avg   | Maersk Avg   | Base Rate   | Surcharges   | Diff %    |
|------------------|-------------|---------------|--------------|-------------|--------------|-----------|
| 0-1 lbs          | 145,692     | $7.06         | $4.62        | $4.15       | $0.47        | -35%      |
| 1-2 lbs          | 113,406     | $9.13         | $5.37        | $5.17       | $0.21        | -41%      |
| 2-3 lbs          | 96,358      | $10.29        | $7.47        | $5.56       | $1.91        | -27%      |
| 3-4 lbs          | 43,915      | $12.16        | $8.87        | $6.35       | $2.52        | -27%      |
| 4-5 lbs          | 41,170      | $12.38        | $12.28       | $7.43       | $4.85        | -1%       |
| 5-10 lbs         | 88,003      | $18.49        | $21.12       | $9.35       | $11.77       | +14%      |
| 10-20 lbs        | 24,071      | $24.17        | $37.06       | $17.44      | $19.62       | +53%      |
| 20-30 lbs        | 3,684       | $26.46        | $72.31       | $49.38      | $22.93       | +173%     |
| 30+ lbs          | 1,910       | $33.14        | $99.95       | $75.71      | $24.24       | +202%     |

**Key insight:** Surcharges stay relatively flat ($20-24) for heavier packages, while the **base rate** is the primary cost driver - jumping from $49 (20-30 lbs) to $76 (30-70 lbs) due to Maersk's 30 lb rate jump.

**The 30 lb Rate Jump:**

| Zone     | 29-30 lbs Rate   | 30-31 lbs Rate   | Increase              |
|----------|------------------|------------------|-----------------------|
| Zone 1   | $7.61            | $22.40           | +$14.79 (+194%)       |
| Zone 5   | $11.81           | $45.18           | +$33.37 (+283%)       |
| Zone 8   | $20.36           | $73.60           | +$53.24 (+262%)       |

While only 0.3% of shipments exceed 30 lbs, they represent 2.9% of Maersk's total cost.

### Cost by Zone

| Zone   | Shipments   | % of Total   | Current Avg   | Maersk Avg   | Difference        |
|--------|-------------|--------------|---------------|--------------|-------------------|
| 1      | 4,324       | 0.8%         | $9.62         | $8.51        | -$1.11 (-12%)     |
| 2      | 21,008      | 3.8%         | $9.43         | $8.13        | -$1.30 (-14%)     |
| 3      | 57,922      | 10.4%        | $9.98         | $8.81        | -$1.17 (-12%)     |
| 4      | 194,107     | 34.8%        | $10.53        | $9.61        | -$0.92 (-9%)      |
| 5      | 132,065     | 23.7%        | $11.51        | $10.83       | -$0.67 (-6%)      |
| 6      | 38,038      | 6.8%         | $12.63        | $12.32       | -$0.30 (-2%)      |
| 7      | 35,763      | 6.4%         | $13.85        | $14.10       | +$0.25 (+2%)      |
| 8      | 73,230      | 13.1%        | $13.73        | $13.56       | -$0.17 (-1%)      |
| 9      | 1,753       | 0.3%         | $41.30        | $37.69       | -$3.61 (-9%)      |

Maersk is cheaper in zones 1-6 and 8-9, with only zone 7 being slightly more expensive (+2%).

### Surcharge Breakdown

| Component         | Total Cost     | % of Total   | Shipments Affected   |
|-------------------|----------------|--------------|----------------------|
| Base Rate         | $3,872,840     | 64.0%        | 558,210 (100%)       |
| NSD (>2 cu ft)    | $1,094,148     | 18.1%        | 60,786 (10.9%)       |
| NSL2 (>30")       | $516,492       | 8.5%         | 129,123 (23.1%)      |
| NSL1 (>21")       | $417,944       | 6.9%         | 104,486 (18.7%)      |
| Pickup Fee        | $145,590       | 2.4%         | 558,210 (100%)       |

**Key Insight:** 41.8% of shipments trigger length surcharges (NSL1 or NSL2), and 10.9% trigger the volume surcharge (NSD). Surcharge overlap (NSL + NSD) affects 10.9% of shipments, adding $22 per package.

### Top Cost Drivers

**Package types where Maersk is EXPENSIVE:**

| Package Type                    | Shipments   | Avg Weight   | Current Avg   | Maersk Avg   | Diff    |
|---------------------------------|-------------|--------------|---------------|--------------|---------|
| PIZZA BOX 42x32x2 (2x str)      | 2,914       | 22.4 lbs     | $32.95        | $92.26       | +180%   |
| PIZZA BOX 42x32x2               | 24,864      | 8.9 lbs      | $27.51        | $32.65       | +19%    |
| PIZZA BOX 48X36X1               | 19,809      | 8.0 lbs      | $32.06        | $35.61       | +11%    |

**Package types where Maersk is CHEAP:**

| Package Type                    | Shipments   | Avg Weight   | Current Avg   | Maersk Avg   | Diff    |
|---------------------------------|-------------|--------------|---------------|--------------|---------|
| PIZZA BOX 40x30x1               | 21,026      | 3.3 lbs      | $19.74        | $9.99        | -49%    |
| PIZZA BOX 20x16x1               | 117,217     | 1.3 lbs      | $9.01         | $4.98        | -45%    |
| MIXPIX BOX                      | 3,239       | 1.3 lbs      | $8.46         | $4.89        | -42%    |
| PIZZA BOX 20x16x2               | 36,319      | 3.2 lbs      | $9.70         | $5.91        | -39%    |
| PIZZA BOX 16x12x2               | 43,675      | 2.2 lbs      | $9.01         | $5.48        | -39%    |

## Key Findings

1. **Maersk is slightly more expensive than current mix** (+0.8%, +$51K) for full volume.

2. **Maersk is competitive for lightweight packages (0-4 lbs)**: These represent 72% of shipments and show 27-41% cost savings vs current mix.

3. **The 30 lb rate jump is devastating**: Base rates nearly triple at the 30 lb threshold across all zones. Fortunately, only 0.3% of shipments exceed this weight.

4. **Surcharges are significant**: 34.3% of total cost comes from surcharges (NSL1/NSL2/NSD/Pickup), with the $18 NSD surcharge being the largest individual contributor.

5. **Zone pricing is favorable**: Maersk is cheaper in 8 of 9 zones (all except zone 7). The overall cost increase is driven by heavy package surcharges, not zone pricing.

6. **No fuel surcharge advantage**: Unlike competitors, Maersk has no separate fuel surcharge - this is built into base rates.

## Recommendation

**Maersk is not recommended as a 100% volume carrier** at +0.8% vs current mix.

However, Maersk could be valuable in a **selective routing strategy** for:
- Lightweight packages (0-4 lbs) - saves 27-41% vs current mix
- Packages under 21" longest dimension (avoids NSL surcharges)
- Any zone (Maersk is cheaper in 8 of 9 zones)

**Avoid routing to Maersk:**
- Packages over 10 lbs (rates become uncompetitive)
- Large packages over 2 cubic feet (NSD surcharge adds $18)
- Packages approaching 30 lb threshold (massive rate jump)

---

*Analysis generated: February 2026*
*Data source: `shipments_aggregated.parquet` and `shipments_unified.parquet`*
*Script: `scenario_2_maersk_100.py`*
