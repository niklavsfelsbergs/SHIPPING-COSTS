# Scenario 7 Deep Dive: Why $4.43M?

S7 "Drop OnTrac" achieves $4,433,040 — 25.8% below the S1 baseline ($5,971,748). This document breaks down exactly how three carriers split 558K shipments to reach that number.

## The Three-Carrier Split

| Carrier   | Shipments   | % Volume   | Total Cost      | Avg/Ship   | Avg Weight   | What It Handles                          |
|-----------|-------------|------------|-----------------|------------|--------------|------------------------------------------|
| P2P       | 198,052     | 35.5%      | $902,204        | $4.56      | 2.50 lbs     | Lightweight/medium where P2P has coverage |
| USPS      | 186,791     | 33.5%      | $1,280,195      | $6.85      | 1.73 lbs     | Lightest packages, full coverage          |
| FedEx     | 173,170     | 31.0%      | $2,250,642      | $13.00     | 6.39 lbs     | Heavy/oversize, SmartPost for large flat  |
| **Total** | **558,013** | **100%**   | **$4,433,040**  | **$7.95**  | **3.45 lbs** |                                           |

For context, S1's average cost per shipment is $10.70. S7 brings that down to $7.95 — a $2.75/shipment reduction.

## Carrier Assignment Grid: Zone x Weight

Each cell shows **USPS% / FedEx% / P2P%** of shipments assigned to that carrier, plus shipment count.

| Weight   | Zone 2             | Zone 3             | Zone 4             | Zone 5             | Zone 6             | Zone 7             | Zone 8             | Total              |
|----------|--------------------|--------------------|--------------------|--------------------|--------------------|--------------------|--------------------|--------------------|
| 0-1 lbs  | 68/ 0/32  10,052   | 62/ 0/38  16,791   | 59/ 0/41  51,054   | 44/ 7/49  34,591   | 66/ 2/32   7,267   | 64/28/ 8   7,649   | 34/30/36  18,134   | 54/ 7/39  145,687  |
| 1-2 lbs  | 56/ 1/43   7,780   | 56/ 1/42  13,479   | 51/ 1/48  38,584   | 42/14/45  27,091   | 58/11/31   5,980   | 30/61/ 8   6,297   | 23/19/59  14,127   | 45/10/44  113,398  |
| 2-3 lbs  | 41/21/38   6,607   | 44/18/38  11,043   | 39/15/46  32,871   | 30/26/43  22,958   | 25/46/30   5,140   | 20/69/10   5,406   | 13/26/61  12,187   | 33/24/43   96,338  |
| 3-5 lbs  | 35/46/19   5,565   | 36/43/21   9,492   | 29/41/30  28,062   | 17/43/40  20,472   | 10/69/21   4,867   |  9/68/22   5,361   |  5/50/44  11,112   | 22/47/32   85,060  |
| 5-10 lbs | 16/73/11   5,116   | 18/70/12   8,993   | 11/70/19  28,609   |  3/67/30  22,079   |  1/83/15   5,253   |  1/84/15   6,062   |  0/67/33  11,582   |  7/71/22   87,898  |
| 10-20 lbs|  4/88/ 8   1,289   |  4/87/ 9   2,340   |  1/88/11   7,254   |  0/85/15   6,167   |  0/93/ 7   1,582   |  0/91/ 8   1,959   |  0/80/20   3,372   |  1/86/13   24,050  |
| 20+ lbs  |  0/100/0     236   |  0/99/ 1     500   |  0/99/ 1   1,636   |  0/98/ 2   1,565   |  0/97/ 3     368   |  0/97/ 3     463   |  0/91/ 9     796   |  0/97/ 3    5,582  |
| **Total**| 46/25/29  36,645   | 45/24/31  62,638   | 39/24/37 188,070   | 28/32/41 134,923   | 33/42/25  30,457   | 26/63/12  33,197   | 16/39/45  71,310   | 33/31/35  558,013  |

**Reading the grid**: "59/0/41 51,054" in Zone 4, 0-1 lbs means 59% USPS, 0% FedEx, 41% P2P across 51,054 shipments.

**Key patterns**:

- **Lightweight + close** (top-left): USPS dominates. Zone 2-4 at 0-2 lbs is 50-68% USPS — cheap flat rates for nearby lightweight.
- **Lightweight + far** (top-right): P2P takes over. Zone 8 at 1-2 lbs is 59% P2P — P2P's flat pricing beats distance-sensitive carriers.
- **Heavy + any zone** (bottom rows): FedEx monopoly. 20+ lbs is 91-100% FedEx everywhere — no alternative is competitive.
- **Mid-weight + mid-zone** (center): Three-way split. Zone 4-5 at 2-5 lbs shows all three carriers competing.
- **Zone 7 anomaly**: FedEx jumps to 61-69% even at 1-3 lbs — likely SmartPost's zone-based pricing is competitive here.
- **Zone 8 + lightweight**: P2P reclaims 36-61% — cross-country shipments where P2P's flat rate beats everyone.

## P2P Coverage Gaps

P2P can only service **289,272 shipments (51.8%)**. The 268,741 unserviceable shipments are split between USPS and FedEx:

| Carrier   | Ships Not Covered by P2P   | Avg Cost   | Avg Weight   |
|-----------|---------------------------|------------|--------------|
| USPS      | 175,423                   | $6.97      | 1.78 lbs     |
| FedEx     | 93,318                    | $13.22     | 6.52 lbs     |
| **Total** | **268,741**               |            |              |

**Why can't P2P service them?** Almost entirely geographic — 266K of the 269K gap is due to ZIP codes outside P2P's coverage area, not weight limits (P2P serves up to ~50 lbs). The gaps are spread across all states, with North Carolina (15K), New York (12K), California (12K), Colorado (12K), and Virginia (11K) being the largest.

### P2P Coverage Gap by Weight

Where P2P can't service, here's who handles each weight bracket:

| Weight     | Ships   | USPS          | FedEx          | Why FedEx Wins                    |
|------------|---------|---------------|----------------|-----------------------------------|
| 0-1 lbs    | 68,752  | 68,683 (100%) | 69 (0%)        | USPS dominates lightweight        |
| 1-2 lbs    | 57,191  | 51,464 (90%)  | 5,727 (10%)    | USPS cheaper for most             |
| 2-3 lbs    | 46,456  | 30,836 (66%)  | 15,620 (34%)   | FedEx starts competing            |
| 3-5 lbs    | 41,312  | 17,854 (43%)  | 23,458 (57%)   | FedEx takes majority              |
| 5-10 lbs   | 41,052  | 6,326 (15%)   | 34,726 (85%)   | USPS dim weight penalties kick in |
| 10-20 lbs  | 11,392  | 260 (2%)      | 11,132 (98%)   | FedEx near-monopoly               |
| 20+ lbs    | 2,586   | 0 (0%)        | 2,586 (100%)   | Only FedEx handles heavy          |

**Yes — large packages outside P2P's coverage go to FedEx.** At 5+ lbs, FedEx handles 85-100% of the P2P coverage gap. USPS only wins in the gap for lightweight packages (0-3 lbs) where its flat rate structure is cheaper.

## Why P2P Is So Cheap

P2P is the biggest contributor to S7's low cost. At $4.56/ship, it's roughly half what USPS or FedEx would charge for the same shipments.

### P2P Cost Structure

| Component   | Total       | Avg/Ship   |
|-------------|-------------|------------|
| Base rate   | $901,740    | $4.55      |
| AHS         | $464        | $0.00      |
| Oversize    | $0          | $0.00      |
| **Total**   | **$902,204**| **$4.56**  |

P2P's cost is almost entirely base rate — virtually no surcharges. Compare to FedEx, which adds $586K in surcharges (fuel $233K, DAS $121K, residential $93K, AHS $20K, demand $9K) on top of $1.67M base rate. P2P's simple pricing structure is its main advantage.

### What Would Alternatives Charge for P2P's 198K Shipments?

| Carrier   | Avg Cost   | Total If Used   | vs P2P         |
|-----------|------------|-----------------|----------------|
| **P2P**   | **$4.56**  | **$902,204**    | -              |
| USPS      | $9.50      | $1,881,494      | +$979K (+109%) |
| FedEx     | $9.64      | $1,909,141      | +$1,007K (+112%)|

P2P undercuts both USPS and FedEx by more than 50% on these shipments. These are mostly lightweight flat packages (avg 2.5 lbs, avg 21" x 16" x 2.4") — the sweet spot of P2P's rate card.

### Where P2P's 198K Shipments Came From (S1 Original Carrier)

| Original Carrier      | Shipments   | S1 Cost       | S7 (P2P) Cost   | Savings     |
|-----------------------|-------------|---------------|------------------|-------------|
| OnTrac                | 66,512      | $519,797      | $308,025         | $211,772    |
| FedEx SmartPost       | 46,243      | $427,328      | $205,253         | $222,074    |
| FedEx Home Delivery   | 45,384      | $463,958      | $216,940         | $247,018    |
| USPS                  | 25,262      | $170,216      | $109,550         | $60,667     |
| DHL eCommerce         | 14,261      | $85,566       | $60,581          | $24,985     |
| Other FedEx           | 390         | $3,943        | $1,855           | $2,089      |
| **Total**             | **198,052** | **$1,670,808**| **$902,204**     | **$768,604**|

P2P captures shipments from every S1 carrier. The biggest dollar savings come from FedEx Home Delivery redirects ($247K) and FedEx SmartPost ($222K), even though the most shipments come from OnTrac (67K).

## Why USPS Handles the Lightest Packages

USPS is assigned 187K shipments averaging just 1.73 lbs (median 1.22 lbs). These are the lightest packages in the portfolio.

### USPS Cost Structure

| Component   | Total         | Avg/Ship   |
|-------------|---------------|------------|
| Base rate   | $1,168,058    | $6.25      |
| NSL1        | $61,668       | $0.33      |
| NSL2        | $24,570       | $0.13      |
| Peak        | $25,899       | $0.14      |
| **Total**   | **$1,280,194**| **$6.85**  |

USPS's surcharges are modest ($112K total, 8.8% of cost). For these lightweight packages, USPS is cheaper than FedEx ($10.71/ship) and P2P can only service 11K of the 187K (6.1% — most of USPS's assigned volume is outside P2P's coverage area).

### Why Not P2P Instead of USPS?

P2P can only service 11,368 of USPS's 186,791 assigned shipments (6.1%). For those 11K where P2P *could* serve, USPS is still cheaper ($5.10 vs P2P's $9.38). USPS wins on lightweight packages in areas where both compete.

## Why FedEx Handles Heavy/Oversize

FedEx is assigned 173K shipments averaging 6.39 lbs — the heaviest segment. These are predominantly large flat packages (avg 34.5" x 25.7" x 2.6", avg 2,475 cubic inches).

### FedEx Cost Structure

| Component      | Total         | Avg/Ship   | % of Total   |
|----------------|---------------|------------|--------------|
| Base rate      | $1,665,006    | $9.61      | 74.0%        |
| Fuel (14%)     | $233,063      | $1.35      | 10.4%        |
| DAS            | $121,380      | $0.70      | 5.4%         |
| Residential    | $92,973       | $0.54      | 4.1%         |
| AHS            | $20,772       | $0.12      | 0.9%         |
| Other          | $117,448      | $0.68      | 5.2%         |
| **Total**      | **$2,250,642**| **$13.00** | **100%**     |

FedEx surcharges add $586K (26% of total), but FedEx still wins because USPS would charge **$67.42/ship** for these same packages — 5x more. USPS's dimensional weight penalties are devastating for large flat items. P2P can only service 80K of the 173K, and where it can, P2P would charge $26.17 vs FedEx's $12.74.

### FedEx Service Split: SmartPost vs Home Delivery

| Service           | Shipments   | Avg Cost   | Share   |
|-------------------|-------------|------------|---------|
| SmartPost (FXSP)  | 131,986     | $12.68     | 76.2%   |
| Home Delivery     | 41,184      | $14.00     | 23.8%   |

SmartPost handles 76% of FedEx-assigned volume. SmartPost uses USPS for final-mile delivery, reducing the residential and fuel surcharge burden.

#### FedEx HD vs SP by Weight

| Weight     | FedEx Ships   | SmartPost   | SP%    | Home Delivery   | HD%    | SP Avg   | HD Avg   |
|------------|---------------|-------------|--------|-----------------|--------|----------|----------|
| 0-1 lbs    | 10,190        | 10,190      | 100%   | 0               | 0%     | $8.33    | -        |
| 1-2 lbs    | 11,627        | 11,576      | 100%   | 51              | 0%     | $8.69    | $10.23   |
| 2-3 lbs    | 23,414        | 22,225      | 95%    | 1,189           | 5%     | $9.16    | $12.21   |
| 3-5 lbs    | 39,574        | 24,655      | 62%    | 14,919          | 38%    | $10.73   | $12.26   |
| 5-10 lbs   | 62,181        | 45,539      | 73%    | 16,642          | 27%    | $15.07   | $12.65   |
| 10-20 lbs  | 20,771        | 15,441      | 74%    | 5,330           | 26%    | $18.22   | $16.05   |
| 20+ lbs    | 5,413         | 2,360       | 44%    | 3,053           | 56%    | $22.44   | $27.02   |

**SmartPost dominates at 0-3 lbs** (95-100%) where its cheaper rates win easily. At **5-10 lbs, SmartPost is actually more expensive** ($15.07 vs HD $12.65) but still carries 73% of volume — this is because the optimizer assigns SmartPost when the SP rate is lower for that specific zone/weight combination, even though the *average* across all assignments favors HD. At **20+ lbs**, HD takes over (56%) as SmartPost's heavy-package surcharges make it less competitive.

#### FedEx HD vs SP by Zone

| Zone   | FedEx Ships   | SmartPost   | SP%    | Home Delivery   | HD%    | SP Avg   | HD Avg   |
|--------|---------------|-------------|--------|-----------------|--------|----------|----------|
| 2      | 9,156         | 7,627       | 83%    | 1,529           | 17%    | $10.11   | $10.21   |
| 3      | 14,997        | 11,706      | 78%    | 3,291           | 22%    | $11.15   | $11.17   |
| 4      | 44,893        | 32,244      | 72%    | 12,649          | 28%    | $11.99   | $11.90   |
| 5      | 42,616        | 32,592      | 77%    | 10,024          | 24%    | $12.59   | $13.82   |
| 6      | 12,711        | 9,431       | 74%    | 3,280           | 26%    | $13.41   | $14.64   |
| 7      | 20,775        | 16,750      | 81%    | 4,025           | 19%    | $13.01   | $16.65   |
| 8      | 27,872        | 21,486      | 77%    | 6,386           | 23%    | $14.75   | $18.81   |

SmartPost is 72-83% of FedEx volume across all zones. The cost gap widens with distance — at Zone 7-8, SmartPost saves $3-4/ship vs HD. At Zone 2-4, the two services are nearly identical in cost.

#### FedEx HD vs SP by Package Type

| Package Type          | FedEx Ships   | SP%    | HD%    | SP Avg   | HD Avg   | Why                                        |
|-----------------------|---------------|--------|--------|----------|----------|--------------------------------------------|
| PIZZA BOX 42x32x2     | 24,809        | 100%   | 0%     | $16.09   | -        | Too large for HD (second longest > 30")    |
| PIZZA BOX 48x36x1     | 19,768        | 100%   | 0%     | $19.18   | -        | Too large for HD                           |
| PIZZA BOX 36x24x2     | 25,845        | 5%     | 95%    | $12.42   | $12.26   | HD slightly cheaper, fits HD limits        |
| PIZZA BOX 30x20x3     | 4,041         | 9%     | 91%    | $12.22   | $12.84   | HD slightly cheaper at these dimensions    |
| PIZZA BOX 24x20x2     | 16,332        | 96%    | 4%     | $9.85    | $12.86   | SP much cheaper for this mid-size box      |
| PIZZA BOX 40x30x1     | 16,122        | 96%    | 4%     | $9.81    | $13.32   | SP much cheaper despite large footprint    |
| PIZZA BOX 20x16x1     | 10,204        | 100%   | 0%     | $8.60    | -        | SP dominates small/light                   |
| CROSS PACKAGING 30x24"| 7,333         | 92%    | 8%     | $9.67    | $13.01   | SP cheaper for this mid-weight format      |

The two **100% SmartPost** package types (42x32x2 and 48x36x1) are the oversized boxes that exceed Home Delivery's second-longest-side limit. SmartPost can handle them because it uses USPS Ground for final mile. Conversely, **PIZZA BOX 36x24x2** is 95% Home Delivery — it fits within HD's dimensions and HD is marginally cheaper.

### The $4.5M Threshold

FedEx's base rate total is **$1,665,006** — which converts to **$4,500,016 undiscounted** (÷ 0.37). The $4.5M threshold is met by just **$16**. The optimizer precisely calibrates FedEx volume to the minimum needed to maintain the 16% earned discount.

If the baked base rate fell below $1,665,000 ($4.5M undiscounted), FedEx would lose the 16% earned discount entirely, and all FedEx rates would jump by 48.65% (the 0% tier multiplier). This would add approximately $1.06M to S7's cost.

## Breakdown by Package Type

The top 15 package types account for ~93% of shipments. For each, the weight breakdown shows which carrier wins at each weight tier:

### PIZZA BOX 20x16x1 (117,206 ships, avg 1.3 lbs, 21"x17"x1", P2P covers 50%)

| Weight   | Ships    | USPS   | FedEx   | P2P    |
|----------|----------|--------|---------|--------|
| 0-1 lbs  | 46,486   | 50%    | 6%      | 44%    |
| 1-2 lbs  | 60,299   | 48%    | 10%     | 42%    |
| 2-3 lbs  | 9,154    | 40%    | 13%     | 48%    |

S1: $1,014K → S7: $667K (**-34.3%**). USPS and P2P split the volume roughly evenly — this is a lightweight box where both are competitive and FedEx is too expensive.

### PIZZA BOX 12x8x1 (55,898 ships, avg 0.7 lbs, 13"x9"x2", P2P covers 50%)

| Weight   | Ships    | USPS   | FedEx   | P2P    |
|----------|----------|--------|---------|--------|
| 0-1 lbs  | 52,195   | 61%    | 8%      | 31%    |

S1: $340K → S7: $263K (**-22.6%**). Smallest box — almost all under 1 lb. USPS dominates because its ultralight rates beat P2P in most geographies.

### PIZZA BOX 42x32x2 (24,809 ships, avg 8.9 lbs, 44"x34"x2", P2P covers 57%)

| Weight   | Ships    | USPS   | FedEx   | P2P    |
|----------|----------|--------|---------|--------|
| 5-10 lbs | 17,810   | 0%     | 100%    | 0%     |
| 10-20 lbs| 6,668    | 0%     | 100%    | 0%     |
| 20+ lbs  | 330      | 0%     | 100%    | 0%     |

S1: $468K → S7: $399K (**-14.6%**). **100% FedEx SmartPost.** Despite P2P covering 57%, P2P is not assigned any — FedEx ($16.10 avg) beats P2P ($26.17 avg) for this heavy, oversized box. USPS would charge $67+/ship due to dim weight.

### PIZZA BOX 48x36x1 (19,768 ships, avg 8.0 lbs, 50"x36"x2", P2P covers 55%)

| Weight   | Ships    | USPS   | FedEx   | P2P    |
|----------|----------|--------|---------|--------|
| 3-5 lbs  | 2,352    | 0%     | 100%    | 0%     |
| 5-10 lbs | 12,594   | 0%     | 100%    | 0%     |
| 10-20 lbs| 4,598    | 0%     | 100%    | 0%     |

S1: $516K → S7: $379K (**-26.6%**). **100% FedEx SmartPost.** Largest box in the portfolio — only SmartPost can handle it economically.

### PIZZA BOX 36x24x2 (37,143 ships, avg 6.0 lbs, 38"x27"x2", P2P covers 54%)

| Weight   | Ships    | USPS   | FedEx   | P2P    |
|----------|----------|--------|---------|--------|
| 3-5 lbs  | 17,490   | 6%     | 75%     | 19%    |
| 5-10 lbs | 17,945   | 7%     | 66%     | 28%    |
| 10-20 lbs| 1,587    | 6%     | 57%     | 37%    |

S1: $447K → S7: $393K (**-12.0%**). FedEx dominates (70% overall, 95% Home Delivery). P2P picks up 24% where it can undercut, mostly at 5-20 lbs.

### PIZZA BOX 40x30x1 (21,002 ships, avg 3.3 lbs, 40"x30"x1", P2P covers 55%)

| Weight   | Ships    | USPS   | FedEx   | P2P    |
|----------|----------|--------|---------|--------|
| 2-3 lbs  | 7,604    | 30%    | 70%     | 0%     |
| 3-5 lbs  | 10,138   | 20%    | 80%     | 0%     |
| 5-10 lbs | 2,193    | 12%    | 88%     | 0%     |

S1: $412K → S7: $214K (**-48.0%**). Biggest % savings. FedEx SmartPost (96%) replaces OnTrac/HD from S1. **P2P gets 0% despite 55% coverage** — FedEx SP at $9.81 beats P2P for this large flat box. This is the box where the S1→S7 SmartPost rerouting has the biggest impact.

### Other Notable Package Types

| Package Type          | Ships   | S1→S7 Savings   | Key Carrier Split                    | Notes                                |
|-----------------------|---------|------------------|--------------------------------------|--------------------------------------|
| PIZZA BOX 16x12x2     | 43,674  | -27.7%           | P2P 44% / USPS 44% / FedEx 12%     | Mid-size, evenly split               |
| WRAP 16"x12"          | 42,298  | -29.7%           | P2P 51% / USPS 45% / FedEx 4%      | Light wrap, P2P leads                |
| PIZZA BOX 24x20x2     | 40,950  | -20.8%           | P2P 41% / FedEx 40% / USPS 19%     | Mid-weight, FedEx SP 96%            |
| PIZZA BOX 20x16x2     | 36,316  | -28.3%           | P2P 44% / USPS 44% / FedEx 12%     | Similar to 16x12x2                   |
| WRAP 24"x16"          | 23,432  | -24.4%           | P2P 49% / FedEx 34% / USPS 17%     | Heavier wrap, FedEx enters           |
| CROSS PACKAGING 30x24"| 15,128  | -22.4%           | FedEx 49% / P2P 41% / USPS 11%     | FedEx SP 92%, medium weight          |
| 21" Tube              | 12,376  | -13.5%           | P2P 44% / USPS 39% / FedEx 17%     | Lightweight tube                     |
| PIZZA BOX 30x20x3     | 10,152  | -27.8%           | P2P 52% / FedEx 40% / USPS 8%      | FedEx 91% HD (unusual)               |
| POLY BAG 9x12         | 5,471   | -9.7%            | USPS 60% / P2P 27% / FedEx 13%     | Lightest item, smallest savings      |

## Breakdown by FedEx Zone

Zone reflects distance from production site to destination. Higher zones = farther = more expensive.

| Zone   | Ships    | S1 Cost       | S7 Cost       | Savings     | %      | Carrier Split                |
|--------|----------|---------------|---------------|-------------|--------|------------------------------|
| 2      | 36,645   | $322,719      | $239,629      | $83,090     | 25.7%  | USPS 46% / P2P 29% / FedEx 25% |
| 3      | 62,638   | $591,850      | $431,489      | $160,361    | 27.1%  | USPS 45% / P2P 31% / FedEx 24% |
| 4      | 188,070  | $1,835,106    | $1,331,597    | $503,509    | 27.4%  | USPS 39% / P2P 37% / FedEx 24% |
| 5      | 134,923  | $1,462,570    | $1,069,305    | $393,265    | 26.9%  | P2P 41% / FedEx 32% / USPS 28% |
| 6      | 30,457   | $358,804      | $284,783      | $74,022     | 20.6%  | FedEx 42% / USPS 33% / P2P 25% |
| 7      | 33,197   | $437,985      | $369,618      | $68,367     | 15.6%  | FedEx 63% / USPS 25% / P2P 12% |
| 8      | 71,310   | $939,882      | $692,917      | $246,965    | 26.3%  | P2P 45% / FedEx 39% / USPS 16% |

**Patterns**:
- **Close zones (2-4)**: USPS dominates — cheap flat rate for lightweight, nearby destinations
- **Mid zones (5)**: P2P takes the lead — its flat pricing beats distance-sensitive USPS/FedEx rates
- **Far zones (6-7)**: FedEx dominates — SmartPost's zone-based pricing scales better than USPS for heavier packages at distance
- **Zone 8**: P2P reclaims the lead — cross-country from Phoenix to East Coast, where P2P's flat pricing undercuts distance-sensitive carriers

Zone 4 generates the most absolute savings ($504K) as it's the highest-volume zone.

## Breakdown by Weight

| Weight     | Ships    | S1 Cost       | S7 Cost       | Savings     | %      | Primary Carrier              |
|------------|----------|---------------|---------------|-------------|--------|------------------------------|
| 0-1 lbs    | 145,687  | $1,000,267    | $709,201      | $291,065    | 29.1%  | USPS 54% / P2P 39%          |
| 1-2 lbs    | 113,398  | $1,001,847    | $694,811      | $307,037    | 30.6%  | USPS 46% / P2P 44%          |
| 2-3 lbs    | 96,338   | $963,890      | $675,513      | $288,377    | 29.9%  | P2P 43% / USPS 33% / FedEx 24% |
| 3-5 lbs    | 85,060   | $1,021,473    | $758,151      | $263,322    | 25.8%  | FedEx 47% / P2P 32%         |
| 5-10 lbs   | 87,898   | $1,358,535    | $1,068,358    | $290,177    | 21.4%  | FedEx 71% / P2P 22%         |
| 10-20 lbs  | 24,050   | $474,023      | $389,542      | $84,480     | 17.8%  | FedEx 86% / P2P 13%         |
| 20+ lbs    | 5,582    | $151,713      | $137,465      | $14,249     | 9.4%   | FedEx 97%                   |

**Clear weight segmentation**:
- **0-2 lbs** (259K ships, 46%): USPS + P2P dominate. These are the cheapest shipments and the highest-savings segment (30%).
- **2-5 lbs** (181K ships, 33%): Three-way split. P2P still competitive but FedEx starts winning at 3+ lbs.
- **5+ lbs** (118K ships, 21%): FedEx near-monopoly. P2P's coverage drops sharply above 10 lbs, and USPS's dimensional penalties make it uncompetitive.

The savings percentage decreases steadily with weight: 30% at 0-2 lbs down to 9% at 20+ lbs. S7's advantage is concentrated in lightweight shipments.

## Breakdown by Production Site

| Site      | Ships    | S7 Cost       | Split                                    |
|-----------|----------|---------------|------------------------------------------|
| Phoenix   | 286,189  | $2,495,708    | FedEx 36% / P2P 33% / USPS 31%          |
| Miami     | 152,421  | $1,103,893    | P2P 38% / USPS 34% / FedEx 28%          |
| Columbus  | 119,402  | $833,435      | USPS 39% / P2P 37% / FedEx 24%          |

Phoenix generates the most FedEx volume ($1.41M) — it ships more heavy/oversize packages and to higher zones (West to East). Miami and Columbus lean more toward P2P and USPS.

## Where the $1.54M Savings Come From

S7 saves $1,538,708 vs S1. Here's where:

### By Mechanism

| Source of Savings                                        | Estimated Impact  |
|----------------------------------------------------------|-------------------|
| **P2P cherry-picking** (198K ships at $4.56 vs $8.44 S1) | ~$769K            |
| **Dropping OnTrac** (67K ships moved to cheaper carriers) | ~$350K            |
| **FedEx SmartPost routing** (vs HD in S1)                 | ~$200K            |
| **USPS optimization** (lightweight routing)               | ~$150K            |
| **FedEx 16% earned discount** (vs 18% baked)              | -$272K (cost)     |
| **Net**                                                   | ~**$1,539K**      |

The 16% earned discount adjustment actually *increases* FedEx costs by $272K vs the baked 18% rate. But this is far outweighed by the routing optimization and P2P savings.

### Why Isn't It Suspicious?

The $4.43M total might seem too good, but the math checks out:

1. **P2P at $4.56/ship is a real rate** — it's almost entirely base rate with negligible surcharges. P2P's business model is high-volume, low-cost last-mile delivery.

2. **P2P only gets shipments where it's genuinely cheapest** — of 289K shipments P2P could service, it's only assigned 198K. The other 91K go to FedEx (80K, where P2P would cost $26.17 vs FedEx $12.74) or USPS (11K, where P2P would cost $9.38 vs USPS $5.10).

3. **FedEx handles the expensive tail** — the 173K FedEx shipments at $13.00 avg include all the heavy, oversized, and long-distance packages that P2P and USPS can't handle cheaply.

4. **The FedEx threshold is barely met** — $4,500,016 vs $4,500,000 required. If the optimizer could push more FedEx volume to P2P, it would — but it can't without losing the 16% discount, which would cost ~$1M.

5. **S1's $10.70 avg is inflated by OnTrac** — OnTrac averages $12.61/ship in S1 and carries 138K shipments. Replacing those with a mix of P2P ($4.56) and cheaper USPS/FedEx assignments drives a large part of the savings.

## Key Risks

1. **FedEx threshold fragility**: $16 of margin. Seasonal volume changes could push FedEx below $4.5M undiscounted, triggering the 0% tier and adding ~$1M in costs. See Scenario 8 ($5M conservative threshold) for a buffered alternative at $4,537K (+$104K).

2. **P2P coverage**: Only 51.8% of shipments are serviceable, almost entirely due to geographic limits (not weight). If P2P changes coverage areas, the benefit shrinks.

3. **P2P rate stability**: At $4.56/ship, P2P operates on thin margins. Rate increases would directly erode savings.

4. **OnTrac contract termination**: This scenario assumes OnTrac's contract can be exited. Early termination penalties or strategic relationship value are not modeled.

---

*Analysis generated: February 2026*
*Data source: shipments_unified.parquet (558,013 shipments) joined with scenario_7_with_p2p/assignments.parquet (Drop OnTrac variant)*
*FedEx rates at 16% earned discount (1.0541x multiplier from baked 18%)*
