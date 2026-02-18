# S15 Validation Plan: P2P + FedEx 3-Group Routing

## Why S15

Scenario 15 replaces the current 4-carrier mix (OnTrac, USPS, FedEx, DHL) with a 2-relationship setup (P2P + FedEx) using 3 simple static routing rules. Estimated annual savings: **$973K (-16.0%)** vs the current mix.

### Decision Drivers

1. **Eliminate USPS** — operationally desired, not a preferred carrier relationship.
2. **Eliminate OnTrac** — regional carrier adds complexity. We don't want 2 regional carriers in the mix.
3. **Reduce carrier count to 2** — P2P (PFAP + PFA/PFS) and FedEx. Simpler operations, fewer integrations, fewer invoice reconciliations.
4. **Preserve FedEx relationship** — S15 maintains the 16% HD / 4% SP earned discount by keeping FedEx undiscounted spend above $5.1M. No penalty cost, no relationship damage.
5. **P2P offers a one-to-many model** — P2P manages the underlying carrier relationships. We get a single contract, single invoice, single point of contact for multiple last-mile carriers.
6. **P2P has a simple cost structure** — base rate by zone and weight, minimal surcharges. Easy to validate, easy to forecast.

### S15 Results Summary

| Metric                           | Value                        |
|----------------------------------|------------------------------|
| Total annual cost                | $5,099,099                   |
| Savings vs S1 (current mix)      | $972,963 (-16.0%)            |
| Carrier relationships            | 2 (P2P, FedEx)               |
| SPE rules                        | 3 group rules + 1 ZIP list   |
| FedEx earned discount            | 16% HD / 4% SP               |
| FedEx HD undiscounted            | $3,680,643                   |
| FedEx SP undiscounted            | $1,452,762                   |
| FedEx total undiscounted         | $5,133,406                   |
| FedEx $5.1M constraint margin    | $33,406                      |
| FedEx $5M penalty margin         | $133,406                     |
| FedEx $4.5M tier margin          | $633,406                     |

### Routing Rules

| Group  | P2P US zone (38,599 ZIPs)      | Other zones                   |
|--------|--------------------------------|-------------------------------|
| Light  | PFAP if ceil(wt) <= 3 lbs      | PFA/PFS if ceil(wt) <= 1 lbs |
| Medium | PFAP if ceil(wt) <= 21 lbs     | PFA/PFS if ceil(wt) <= 2 lbs |
| Heavy  | FedEx (HD or SP)               | FedEx (HD or SP)              |

Everything not routed to P2P goes to FedEx. Light = 20 package types (65.0%), Medium = 18 (21.6%), Heavy = 15 (13.4%).

### Carrier Split

| Carrier         | Shipments   | Share    | Cost           | Avg Cost |
|-----------------|-------------|----------|----------------|----------|
| PFAP            | 216,075     | 40.0%    | $978,249       | $4.53    |
| PFA/PFS         | 67,871      | 12.6%    | $375,615       | $5.53    |
| FedEx (total)   | 255,971     | 47.4%    | $3,745,234     | $14.63   |
|   FedEx HD      | 152,438     | 28.2%    | $2,697,192     | $17.69   |
|   FedEx SP      | 103,533     | 19.2%    | $1,048,042     | $10.12   |
| **Total**       | **539,917** | **100%** | **$5,099,099** |          |

### Comparison to Alternatives

| Scenario                        | Cost           | vs S1      | Carriers | FedEx Earned     | Why not / notes                            |
|---------------------------------|----------------|------------|:--------:|:----------------:|--------------------------------------------|
| S14 P2P+FedEx per-shipment      | $4,944,680     | -18.6%     | 2        | 16% HD / 4% SP   | 108K forced switches, complex routing      |
| **S15 3-Group P2P+FedEx**       | **$5,099,099** | **-16.0%** | **2**    | **16% HD / 4% SP** | **Selected — simple rules**              |
| S13 P2P+FedEx unconstrained     | $5,178,926     | -14.7%     | 2        | 0% (lost)        | Loses FedEx earned discount                |
| S4 Current carrier optimal      | $5,555,189     | -8.5%      | 3        | 0% (lost)        | Keeps OnTrac+USPS, loses earned discount   |

S14 is $154K cheaper than S15, but requires 108K per-shipment routing overrides — not configurable through simple SPE rules. S15 is the **best implementable 2-carrier scenario**. S4 uses the current 3 carriers (OnTrac, USPS, FedEx) at 0% earned — S15 beats it by $456K by replacing OnTrac/USPS with P2P and maintaining the FedEx earned discount.

---

## Validation Checklist

### V1. FedEx calculation accuracy

**Question:** Are our FedEx calculated costs in line with what FedEx actually invoices?

**Why it matters:** FedEx represents 47.4% of S15 shipments and 73.4% of cost ($3.75M). If our calculator over- or underestimates, the savings projection is wrong. Both HD and SP accuracy matter — and HD is now the dominant service (59.5% of FedEx shipments).

**How to validate:**
- Compare our FedEx calculator output against recent FedEx invoices (last 3-6 months)
- Focus on: base rate, fuel surcharge, DAS, residential, AHS, demand surcharges
- **Validate separately for HD and SP** — the earned discount adjustments differ (HD 1.0541x, SP 1.0099x)
- **Validate SmartPost limit enforcement** — confirm that packages we route to HD (because of SmartPost limits) are also routed to HD by FedEx on the invoice. If FedEx actually routes some of these as SmartPost, our cost model overstates.
- Current FedEx calculator accuracy: base rates +0.08% (HD), 0.00% (SmartPost) — but surcharges are still in development
- Key risk: SmartPost rates have been corrected in 2026 rate tables (Ground Economy pricing). Verify SmartPost invoices match the new rate structure.

**Status:** Done. Seems correct.

---

### V2. FedEx undiscounted spend threshold

**Question:** Does our calculated FedEx undiscounted spend really clear the $5M penalty threshold?

**Why it matters:** If actual undiscounted spend falls below $5M, we face a **$500K penalty**. Our model shows $5.13M undiscounted ($133K margin above $5M), but this relies on our rate-to-undiscounted conversion being correct. The margin above the $5.1M constraint is $33K.

**How to validate:**
- Request FedEx undiscounted list prices for a sample of recent shipments
- **Validate the HD and SP baked factors separately:**
  - HD: `undiscounted = base_rate / 0.370` (where 0.370 = 1 - 0.45 PP - 0.18 baked earned)
  - SP: `undiscounted = base_rate / 0.505` (where 0.505 = 1 - 0.45 PP - 0.045 baked earned)
- Verify the 0.45 performance pricing discount factor
- Verify HD baked earned = 18% and SP baked earned = 4.5% against the contract
- Check if there are FedEx cost components we're missing that count toward or against the undiscounted threshold (e.g., surcharges — do they count toward the $5M?)
- **Critical: the HD/SP split now matters even more.** HD contributes 71.7% of undiscounted spend ($3.68M) — getting the HD baked earned percentage wrong has ~2.5x the impact of getting SP wrong.
- **Validate SmartPost limit enforcement against FedEx's routing.** If FedEx routes some limit-exceeding packages as SmartPost anyway (not switching to HD), the actual HD/SP undiscounted split would differ from our model.
- Run a monthly breakdown: does every month individually contribute enough, or is there seasonal risk?

**Status:** [ ] Not started - will validate when we get the list prices.

---

### V3. P2P peak surcharges

**Question:** Do P2P US and P2P US2 have peak/demand surcharges during holiday periods?

**Why it matters:** Our P2P calculators include zero peak surcharges because none are listed in the rate cards. If P2P charges peak surcharges (Nov-Jan, like FedEx/USPS), our P2P costs are underestimated — especially in the highest-volume months.

**Resolution:** P2P confirmed they follow the USPS peak surcharge schedule (Oct 5 - Jan 18). Peak surcharges added to P2P US2 calculator and S15 rerun. P2P US (PFAP) peak surcharges not yet confirmed — to be clarified.

**Status:** [x] Resolved — P2P US2 peak included in model

---

### V4. P2P US coverage stability

**Question:** Will the 38,599 P2P US (PFAP) ZIP codes remain stable?

**Why it matters:** PFAP is the cheapest carrier ($4.53 avg) handling 40.0% of shipments. If ZIP coverage shrinks, shipments fall to PFA/PFS ($5.53) or FedEx ($14.63), increasing costs significantly. The routing rules are built around this ZIP list.

**How to validate:**
- Ask P2P: How often does the PFAP coverage zone change? Is it contractually locked?
- Get history: Has coverage expanded or contracted in the past 12 months?
- Stress test: What happens to S15 total cost if PFAP loses 10% of ZIPs? 20%?

**Status:** [ ] Not started

---

### V5. P2P US2 coverage and service selection

**Question:** Are all 93,100 P2P US2 ZIPs actually serviceable, and is the PFA vs PFS service selection stable?

**Why it matters:** P2P US2 handles 12.6% of shipments. The PFA/PFS service selection is done at the (packagetype, weight_bracket) group level. If P2P changes service availability or pricing, the group-level selection could shift.

**How to validate:**
- Confirm 93,100 ZIP coverage is contractually guaranteed
- Confirm PFA and PFS service availability per zone (PFA: zones 1-8, PFS: zones 1-9)
- Verify that the remote zone surcharge waiver is contractual (currently waived per contract)
- Confirm DIM factor 166 for both services

**Status:** [ ] Not started

---

### V6. P2P US2 rate competitiveness above cutoffs

**Question:** Is P2P US2 truly uncompetitive above the cutoffs (Light 1 lb, Medium 2 lbs)?

**Why it matters:** The PFA/PFS cutoffs are constrained below the unconstrained optimum to maintain the FedEx threshold. If the threshold constraint is relaxed (e.g., with higher FedEx undiscounted spend from volume growth), PFA/PFS could be used at higher weights for additional savings.

**How to validate:**
- Compare P2P US2 rates vs FedEx at 16% HD / 4% SP earned for packages above the cutoff across zones 3-7
- Check if P2P has mentioned upcoming rate adjustments for PFA/PFS
- Note: the cutoffs are driven by the FedEx threshold constraint, not by PFA/PFS being uncompetitive

**Status:** [ ] Not started

---

### V7. FedEx contract terms for volume reduction

**Question:** What happens to the FedEx contract if we shift the service mix significantly?

**Why it matters:** S15 changes the FedEx service mix dramatically: HD handles 59.5% of FedEx shipments (up from ~24% before SmartPost limits). The total FedEx shipment count is 256K. FedEx may have contractual terms about service mix or volume changes. The undiscounted spend is maintained above $5.1M, but the HD/SP composition has shifted (71.7% HD vs 28.3% SP by undiscounted).

**How to validate:**
- Review FedEx contract for minimum volume commitments (shipment count, not just spend)
- Check if the earned discount tiers are purely spend-based or also volume-based
- **Confirm the $5M penalty threshold and $4.5M earned discount threshold are correct for 2026**
- **Confirm that HD and SP undiscounted spend are combined for threshold purposes** (not tracked separately)
- **Confirm SmartPost limit enforcement** — does FedEx automatically route limit-exceeding packages to HD, or do we need to specify HD explicitly?
- Ask: Does FedEx require advance notice of significant service mix changes?

**Status:** [ ] Not started

---

### V8. OnTrac and USPS contract exit

**Question:** What are the exit terms for OnTrac and USPS?

**Why it matters:** S15 eliminates both carriers. OnTrac has a 279K/year minimum volume commitment (5,365/week x 52). USPS has a 140K/year minimum (35K/quarter). Breaking these commitments may have financial penalties.

**How to validate:**
- Review OnTrac contract: penalty for early termination or volume shortfall?
- Review USPS contract: penalty for dropping below Tier 1 quarterly minimum?
- Calculate net savings: S15 savings ($973K) minus any exit penalties
- Timeline: When do current contracts expire? Can we align the transition?

**Status:** [ ] Not started

---

### V9. Seasonal FedEx threshold risk

**Question:** Does the $5.1M FedEx undiscounted threshold hold across seasonal volume patterns?

**Why it matters:** Annual aggregate is $5.13M with **$33K margin above the $5.1M constraint** and **$133K margin above the $5M penalty threshold**. If any quarter or measurement period dips, the undiscounted spend could fall below thresholds.

**How to validate:**
- Clarify with FedEx: Is the $5M threshold measured annually, quarterly, or on a rolling basis?
- Run monthly FedEx undiscounted spend projection using S15 routing on 2025 monthly volumes
- **Split the monthly projection into HD and SP undiscounted** — verify both components are stable. HD now dominates (71.7%), so seasonal HD volume patterns are the key driver.
- Identify the lowest-volume quarter and check if it individually risks the threshold (if quarterly measurement)
- **The $133K margin above $5M is reasonable** but still warrants seasonal analysis

**Status:** [ ] Not started

---

### V10. SPE implementation feasibility

**Question:** Can the 3 routing rules + ZIP list be configured in PCS/SPE?

**Why it matters:** S15's value depends on PCS being able to route shipments based on (package type group, weight ceiling, destination ZIP list). If SPE can't support this logic, we'd need a workaround.

**How to validate:**
- Confirm SPE can handle: IF zip IN list AND ceil(weight) <= X THEN carrier Y
- Confirm SPE can map package types to groups (Light/Medium/Heavy)
- Test with a small batch: route 100 shipments through the new rules, verify correct carrier selection
- Identify any SPE limitations (e.g., max ZIP list size, weight rounding behavior)
- **Note the Medium PFAP cutoff is 21 lbs and Medium PFA/PFS cutoff is 2 lbs.** Verify SPE can handle these cutoffs.

**Status:** [ ] Not started

---

### V11. P2P invoice reconciliation capability

**Question:** Can we validate P2P invoices against our calculator?

**Why it matters:** The shipping cost validation system (this repository) needs to extend to P2P US and P2P US2. If P2P invoice format is incompatible or we can't match shipments, we lose cost control visibility.

**How to validate:**
- Request sample P2P invoice (PFAP, PFA, PFS)
- Map invoice fields to our calculator output columns
- Build upload_actuals and compare_expected_to_actuals for P2P (similar to existing OnTrac/USPS/FedEx)
- Target accuracy: < 1% variance between calculated and invoiced

**Status:** [ ] Not started

---

### V12. Transit time and service level impact

**Question:** Are P2P transit times acceptable compared to current carriers?

**Why it matters:** Cost savings are meaningless if delivery times degrade and impact customer satisfaction. P2P routes through various last-mile carriers — transit times may vary by region.

**How to validate:**
- Request P2P transit time guarantees/SLAs by zone
- Compare against current carrier transit times (OnTrac: 1-3 days West, USPS: 2-5 days, FedEx: 2-7 days)
- Focus on the 40.0% of shipments moving to PFAP — are these getting slower?
- Check P2P's track record: on-time delivery rate, damage rate, claims process

**Status:** [ ] Not started

---

### V13. SmartPost limit enforcement alignment

**Question:** Does FedEx enforce the same SmartPost limits we've modeled?

**Why it matters:** Our FedEx calculator now overrides SmartPost to HD for packages exceeding: L+G >84", weight >20 lbs, any dimension >27", second longest >17". This shifted 59.5% of FedEx shipments to HD and changed the HD/SP undiscounted ratio to 71.7:28.3. **If FedEx's actual enforcement differs from our model, the entire HD/SP split — and therefore the undiscounted spend calculation — could be wrong.**

**How to validate:**
- Confirm the 4 SmartPost limits with FedEx or contract documentation
- Check FedEx invoices for packages near the limits — did FedEx charge HD or SP?
- Identify any additional SmartPost restrictions we may have missed (e.g., cylindrical items, fragile goods)
- Compare our SmartPost→HD override rate against FedEx invoice HD/SP split for the same shipments

**Status:** [ ] Not started — **HIGH PRIORITY** given the magnitude of the HD/SP shift

---

## Validation Priority

| Priority | Item                            | Risk if skipped                          | Effort |
|:--------:|---------------------------------|------------------------------------------|--------|
| **P1**   | V13 SmartPost limit alignment   | Wrong HD/SP split → wrong undiscounted   | Medium |
| **P1**   | V2 FedEx undiscounted threshold | $500K penalty ($33K margin)              | Medium |
| **P1**   | V1 FedEx calculation accuracy   | Wrong savings estimate                   | Medium |
| **P1**   | V9 Seasonal threshold risk      | $500K penalty in low quarter             | Medium |
| **P2**   | V7 FedEx contract terms         | Unexpected exit costs                    | Low    |
| **P2**   | V8 OnTrac/USPS exit terms       | Unexpected exit penalties                | Low    |
| **P2**   | V4 PFAP coverage stability      | Cost increase if ZIPs lost               | Low    |
| **P2**   | V10 SPE implementation          | Can't implement the rules                | Medium |
| **P3**   | V3 P2P peak surcharges (PFAP)   | Underestimated P2P cost                  | Low    |
| **P3**   | V5 P2P US2 coverage/service     | Minor cost variance                      | Low    |
| **P3**   | V6 P2P US2 rate competitiveness | Missed optimization                      | Low    |
| **P3**   | V11 P2P invoice reconciliation  | No cost control                          | Medium |
| **P3**   | V12 Transit times               | Service degradation                      | Low    |

**V13 (SmartPost limit alignment) is the new top priority.** The SmartPost limit enforcement shifted 59.5% of FedEx shipments to HD and changed the undiscounted ratio to 71.7:28.3. If our limits don't match FedEx's actual enforcement, the entire cost model is built on incorrect HD/SP assumptions. This must be validated before any other threshold calculations can be trusted.

**V2 and V9 remain critical** — the $33K margin on the $5.1M constraint provides better comfort than before. The $133K margin above $5M is reasonable but still warrants seasonal analysis.

---

## Decision Gate

Proceed with S15 implementation if:

- [ ] V13: SmartPost limit enforcement confirmed (our HD/SP split matches FedEx invoices)
- [ ] V2: FedEx HD/SP undiscounted spend formula confirmed against actual list prices
- [ ] V9: FedEx $5M threshold measurement period confirmed AND seasonal risk acceptable (given $33K/$133K margins)
- [ ] V1: FedEx calculator variance < 2% vs invoices (HD and SP separately)
- [x] V3: P2P peak surcharges are zero OR accounted for in updated model

If any P1 validation fails, rerun S15 with corrected inputs before committing.

---

*Updated: February 2026*
*Data basis: 539,917 matched-only shipments (2025 volumes), 2026 rate cards*
*FedEx calculator v2026.02.18.1 — SmartPost size/weight limits enforced*
*S15 total: $5,099,099 (-16.0% vs S1 current mix $6,072,062)*
*FedEx HD at 16% earned (1.0541x), SP at 4% earned (1.0099x)*
*FedEx undiscounted: HD $3,680,643 + SP $1,452,762 = $5,133,406 ($33K margin above $5.1M)*
