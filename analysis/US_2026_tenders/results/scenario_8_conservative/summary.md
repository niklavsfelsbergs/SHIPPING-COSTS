# Scenario 8: Conservative P2P + FedEx 16% Earned Discount ($5M Buffer)

## Executive Summary

Scenario 8 is a conservative variant of Scenario 7, raising the FedEx undiscounted spend threshold from $4.5M to **$5M** to build a ~$500K safety buffer against seasonal volume fluctuations. Like S7, it uses a dual-method optimization with USPS + FedEx + P2P (dropping OnTrac). The higher threshold forces more volume to FedEx and away from P2P, resulting in a higher total cost than S7 but with significantly more headroom on the earned discount qualification.

The recommended "Drop OnTrac" variant produces a total cost of **$5,136,088 (15.4% savings vs S1 baseline)** -- $135K more than S7's $5,000,952 but with the FedEx 16% tier safely met rather than clearing by just $43.

## Methodology

### Approach

Same dual-method approach as Scenario 7:

- **Method A**: Greedy assignment across USPS, FedEx, and P2P, then adjust for volume constraints and the $5M FedEx undiscounted threshold
- **Method B**: Take Scenario 6's solution (same carriers, $5M threshold) and improve by switching groups to P2P where cheaper

The cheaper of the two methods is selected for each constraint combination. Method B guarantees S8 <= S6 because it only makes beneficial switches from S6's baseline.

### Key Parameters

| Parameter                  | S7 Value     | S8 Value (this scenario) |
|----------------------------|--------------|--------------------------|
| FedEx earned discount      | 16%          | 16%                      |
| FedEx undiscounted threshold | $4,500,000 | **$5,000,000**           |
| Safety buffer vs S7        | --           | +$500,000                |
| Carriers available         | USPS, FedEx, P2P | USPS, FedEx, P2P     |
| OnTrac                     | Dropped      | Dropped                  |
| USPS minimum               | 140,000      | 140,000                  |

### Constraint Combinations

| Variant             | Available Carriers           | Minimums Enforced                                     |
|---------------------|------------------------------|-------------------------------------------------------|
| Both constraints    | OnTrac, USPS, FedEx, P2P    | OnTrac >= 279K, USPS >= 140K, FedEx >= $5M undisc.   |
| Drop OnTrac         | USPS, FedEx, P2P            | USPS >= 140K, FedEx >= $5M undisc.                    |
| Drop USPS           | OnTrac, FedEx, P2P          | OnTrac >= 279K, FedEx >= $5M undisc.                  |
| Drop both           | FedEx, P2P                  | FedEx >= $5M undisc.                                  |

## Results

### Total Cost (Drop OnTrac -- Recommended)

| Metric                    | Value                    |
|---------------------------|--------------------------|
| Total cost                | **$5,136,088**           |
| Savings vs S1             | **$935,974 (15.4%)**     |
| Total shipments           | 539,917                  |
| FedEx 16% tier            | **MET**                  |

### Carrier Mix (Drop OnTrac)

| Carrier     | Shipments   | Share    | Total Cost     | Avg Cost    |
|-------------|-------------|---------|----------------|-------------|
| USPS        | 185,845     | 34.4%   | $1,300,390     | $7.00       |
| FedEx       | 261,488     | 48.4%   | $3,401,115     | $13.01      |
| P2P         | 92,584      | 17.1%   | $434,583       | $4.69       |
| **Total**   | **539,917** | **100%**| **$5,136,088** |             |

### Constraint Satisfaction (Drop OnTrac)

| Constraint              | Actual         | Minimum          | Status      |
|-------------------------|----------------|------------------|-------------|
| USPS volume             | 185,845        | 140,000          | **MET**     |
| FedEx undiscounted      | >= $5,000,000  | $5,000,000       | **MET**     |
| P2P volume              | 92,584         | 0                | N/A         |

### Impact of the $5M Threshold vs S7's $4.5M

The higher threshold shifts volume from P2P to FedEx compared to S7:

| Metric              | S7 ($4.5M)     | S8 ($5M)        | Difference     |
|---------------------|----------------|-----------------|----------------|
| FedEx shipments     | 226,532        | 261,488         | +34,956        |
| P2P shipments       | 127,540        | 92,584          | -34,956        |
| USPS shipments      | 185,845        | 185,845         | 0              |
| Total cost          | $5,000,952     | $5,136,088      | +$135,136      |
| FedEx threshold     | MET by $43     | MET with buffer  |                |

The $135K annual cost increase buys significant protection against losing the 16% earned discount tier.

## Cross-Scenario Comparison

| Scenario                              | Cost           | vs S1     | FedEx Tier   | Notes                          |
|---------------------------------------|----------------|-----------|--------------|--------------------------------|
| S7 Drop OnTrac ($4.5M threshold)     | $5,000,952     | 17.6%     | MET by $43   | Razor-thin margin              |
| **S8 Drop OnTrac ($5M threshold)**   | **$5,136,088** | **15.4%** | **MET**      | **$500K safety buffer**        |
| S10 Static Rules (per-packagetype)   | $4,942,173     | 18.6%     | MET          | ~50 rules + zip list           |
| S11 3-Group Rules                    | $4,962,119     | 18.3%     | MET          | 3 rules + zip list             |
| S1 Baseline                          | $6,072,062     | --        | --           | Current carrier mix            |

S8 is more conservative than S7 but less optimized than S10/S11, which use static routing rules with the $4.5M threshold. The S10/S11 scenarios produce lower costs because they use finer-grained routing (per-packagetype or per-group weight cutoffs) rather than S8's greedy per-group optimization, and because they target the lower $4.5M threshold.

## Key Findings

1. **The $5M buffer costs $135K/year vs S7**: S8's total of $5,136,088 is $135,136 more than S7's $5,000,952. This premium buys protection against seasonal volume fluctuations pushing FedEx below the 16% tier, which S7 cleared by only $43.

2. **P2P captures 35K fewer shipments than S7**: The higher FedEx threshold forces 35K shipments from P2P to FedEx, reducing P2P from 23.6% to 17.1% of volume. P2P's average cost is slightly higher at $4.69/shipment (vs S7's $4.62) because the cheapest P2P-eligible groups are now retained by FedEx.

3. **USPS volume is identical to S7**: Both scenarios route 185,845 shipments to USPS -- the $5M vs $4.5M threshold difference is absorbed entirely by the FedEx/P2P split, not by USPS.

4. **FedEx carries 48% of volume**: With 261,488 shipments (vs S7's 226,532), FedEx is the dominant carrier. This is the cost of the safety buffer -- more volume at FedEx's higher average cost of $13.01/shipment.

5. **Still saves 15.4% vs S1 baseline**: Despite the conservative threshold, S8 delivers nearly $1M in annual savings compared to the current carrier mix, confirming that the USPS + FedEx + P2P strategy is robust even under conservative assumptions.

6. **S10/S11 offer better cost with lower threshold risk**: If the $4.5M threshold is acceptable, S10 ($4,942,173) and S11 ($4,962,119) both outperform S8 by $174-194K. S8 is the right choice only if the additional FedEx spend headroom is deemed necessary.

---

*Analysis generated: February 2026*
*Data source: shipments_unified.parquet (539,917 matched shipments), FedEx at 16% earned discount*
*Baseline: $6,072,062 (Scenario 1 current mix, FedEx at 16% earned discount)*
*FedEx threshold: $5.0M undiscounted spend required (conservative, vs $4.5M in S7)*
