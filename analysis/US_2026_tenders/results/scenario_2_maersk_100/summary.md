# Scenario 2: 100% Maersk

## Executive Summary

This scenario calculates the total shipping cost if 100% of US shipment volume were routed to Maersk US, a carrier not currently used in the production system. **Maersk would cost $5.69M vs the current mix of $6.07M, representing a 6.4% ($386K) saving**. Maersk is now the cheapest full-coverage carrier, with strong savings on lightweight packages (0-4 lbs) and competitive rates through zone 8. Mid-to-heavy weight shipments (10+ lbs) remain significantly more expensive due to high base rates and a dramatic rate jump at 30 lbs, but these are a small portion of total volume.

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
| Total Shipments               | 539,917                     |
| Current Mix Total             | $6,072,061.73               |
| 100% Maersk Total             | $5,686,413.05               |
| **Difference**                | **-$385,649 (-6.4%)**       |
| Avg Cost/Shipment (Current)   | $11.25                      |
| Avg Cost/Shipment (Maersk)    | $10.53                      |

### Carrier Ranking (Full Coverage Only)

| Rank   | Carrier       | Serviceable   | Total Cost       | Avg Cost   |
|--------|---------------|---------------|------------------|------------|
| 1      | Maersk        | 539,917       | $5,686,413       | $10.53     |
| 2      | Current Mix   | 539,917       | $6,072,062       | $11.25     |
| 3      | FedEx         | 539,917       | $6,287,902       | $11.65     |
| 4      | USPS          | 539,917       | $14,835,549      | $27.48     |

*Note: OnTrac (64.5% coverage) and P2P (51.8% coverage) excluded - cannot service all shipments*

### Cost by Weight Bracket

The 30 lb rate jump is a critical cost driver for Maersk. The table below shows the breakdown between base rate and surcharges:

| Weight Bracket   | Shipments   | Current Avg   | Maersk Avg   | Base Rate   | Surcharges   | Diff %    |
|------------------|-------------|---------------|--------------|-------------|--------------|-----------|
| 0-1 lbs          | 142,303     | $6.74         | $4.61        | $4.15       | $0.47        | -32%      |
| 1-2 lbs          | 109,943     | $8.62         | $5.37        | $5.16       | $0.20        | -38%      |
| 2-3 lbs          | 93,314      | $9.86         | $7.46        | $5.55       | $1.91        | -24%      |
| 3-4 lbs          | 42,378      | $11.95        | $8.84        | $6.32       | $2.52        | -26%      |
| 4-5 lbs          | 40,112      | $12.32        | $12.21       | $7.39       | $4.82        | -1%       |
| 5-10 lbs         | 85,026      | $17.83        | $20.32       | $9.03       | $11.28       | +14%      |
| 10-20 lbs        | 22,481      | $23.70        | $36.11       | $17.16      | $18.96       | +52%      |
| 20-30 lbs        | 3,016       | $25.62        | $68.99       | $46.13      | $22.86       | +169%     |
| 30+ lbs          | 1,321       | $31.57        | $97.49       | $73.28      | $24.20       | +209%     |

**Key insight:** Surcharges stay relatively flat ($20-24) for heavier packages, while the **base rate** is the primary cost driver - jumping from $46 (20-30 lbs) to $73 (30+ lbs) due to Maersk's 30 lb rate jump.

**The 30 lb Rate Jump:**

| Zone     | 29-30 lbs Rate   | 30-31 lbs Rate   | Increase              |
|----------|------------------|------------------|-----------------------|
| Zone 1   | $7.61            | $22.40           | +$14.79 (+194%)       |
| Zone 5   | $11.81           | $45.18           | +$33.37 (+283%)       |
| Zone 8   | $20.36           | $73.60           | +$53.24 (+262%)       |

While only 0.2% of shipments exceed 30 lbs, they represent a disproportionate share of Maersk's total cost.

### Cost by Zone

| Zone   | Shipments   | % of Total   | Current Avg   | Maersk Avg   | Difference        |
|--------|-------------|--------------|---------------|--------------|-------------------|
| 1      | 3,956       | 0.7%         | $9.30         | $8.47        | -$0.83 (-9%)      |
| 2      | 20,412      | 3.8%         | $9.07         | $8.04        | -$1.03 (-11%)     |
| 3      | 56,270      | 10.4%        | $9.63         | $8.68        | -$0.95 (-10%)     |
| 4      | 188,429     | 34.9%        | $10.14        | $9.46        | -$0.69 (-7%)      |
| 5      | 128,384     | 23.8%        | $11.10        | $10.60       | -$0.50 (-5%)      |
| 6      | 36,722      | 6.8%         | $12.18        | $11.86       | -$0.33 (-3%)      |
| 7      | 34,230      | 6.3%         | $13.37        | $13.38       | +$0.01 (+0%)      |
| 8      | 69,879      | 12.9%        | $13.33        | $12.92       | -$0.41 (-3%)      |
| 9      | 1,635       | 0.3%         | $36.49        | $37.11       | +$0.62 (+2%)      |

Maersk is cheaper in zones 1-6 and zone 8. Only zones 7 and 9 are marginally more expensive.

### Surcharge Breakdown

| Component         | Total Cost     | % of Total   | Shipments Affected   |
|-------------------|----------------|--------------|----------------------|
| Base Rate         | $3,632,259     | 63.9%        | 539,917 (100%)       |
| NSD (>2 cu ft)    | $1,018,908     | 17.9%        | 56,606 (10.5%)       |
| NSL2 (>30")       | $493,584       | 8.7%         | 123,396 (22.9%)      |
| NSL1 (>21")       | $404,100       | 7.1%         | 101,025 (18.7%)      |
| Pickup Fee        | $137,562       | 2.4%         | 539,917 (100%)       |

**Key Insight:** 41.6% of shipments trigger length surcharges (NSL1 or NSL2), and 10.5% trigger the volume surcharge (NSD). Surcharge overlap (NSL + NSD) affects a subset of shipments, adding $22 per package.

### Top Cost Drivers

**Package types where Maersk is EXPENSIVE:**

| Package Type                    | Shipments   | Avg Weight   | Current Avg   | Maersk Avg   | Diff    |
|---------------------------------|-------------|--------------|---------------|--------------|---------|
| BOX 16x24x12                    | 1,238       | 9.2 lbs      | $14.50        | $71.24       | +391%   |
| PIZZA BOX 42x32x2 (2x str)      | 2,532       | 21.9 lbs     | $32.17        | $91.54       | +185%   |
| PIZZA BOX 30x20x3 (2x str)      | 1,359       | 10.6 lbs     | $14.36        | $36.12       | +151%   |
| PIZZA BOX 36x24x2 (2x str)      | 1,289       | 15.3 lbs     | $18.68        | $45.30       | +142%   |
| CROSS PACKAGING 49X30"          | 1,990       | 17.7 lbs     | $26.55        | $52.69       | +98%    |

**Package types where Maersk is CHEAP:**

| Package Type                    | Shipments   | Avg Weight   | Current Avg   | Maersk Avg   | Diff    |
|---------------------------------|-------------|--------------|---------------|--------------|---------|
| PIZZA BOX 40x30x1               | 20,091      | 3.3 lbs      | $19.62        | $9.99        | -49%    |
| PIZZA BOX 20x16x1               | 113,896     | 1.3 lbs      | $8.42         | $4.97        | -41%    |
| MIXPIX BOX                      | 3,082       | 1.3 lbs      | $7.96         | $4.88        | -39%    |
| PIZZA BOX 16x12x2               | 42,377      | 2.2 lbs      | $8.57         | $5.48        | -36%    |
| PIZZA BOX 20x16x2               | 35,114      | 3.2 lbs      | $9.21         | $5.90        | -36%    |

## Key Findings

1. **Maersk is 6.4% cheaper than current mix** (-$386K) for full volume. Maersk is now the cheapest full-coverage carrier, beating both the current mix and FedEx.

2. **Dominant for lightweight packages (0-4 lbs)**: These represent 72% of shipments and show 24-38% cost savings vs current mix. This lightweight advantage is the primary driver of overall savings.

3. **Competitive across most zones**: Maersk is cheaper in 7 of 9 zones (zones 1-6 and 8), with savings of 3-11% per shipment. Only zones 7 and 9 are marginally more expensive.

4. **The 30 lb rate jump is devastating**: Base rates nearly triple at the 30 lb threshold across all zones. Fortunately, only 0.2% of shipments exceed this weight.

5. **Surcharges are significant**: 36.1% of total cost comes from surcharges (NSL1/NSL2/NSD/Pickup), with the $18 NSD surcharge being the largest individual contributor.

6. **No fuel surcharge advantage**: Unlike competitors, Maersk has no separate fuel surcharge - this is built into base rates.

## Recommendation

**Maersk is the cheapest full-coverage carrier** at -6.4% vs current mix, saving $386K annually. It beats both the current carrier mix and FedEx ($6.29M).

Maersk would be even more valuable in a **selective routing strategy** for:
- Lightweight packages (0-4 lbs) - saves 24-38% vs current mix
- Packages under 21" longest dimension (avoids NSL surcharges)
- Zones 1-6 and 8 (cheaper than current mix)

**Avoid routing to Maersk:**
- Packages over 10 lbs (rates become uncompetitive vs other carriers)
- Large packages over 2 cubic feet (NSD surcharge adds $18)
- Packages approaching 30 lb threshold (massive rate jump)

---

*Analysis generated: February 2026*
*Data source: `shipments_aggregated.parquet` and `shipments_unified.parquet`*
*Script: `scenario_2_maersk_100.py`*
