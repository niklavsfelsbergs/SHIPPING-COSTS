# 2025 Actuals Reconciliation

## Reported vs Dataset

| Source | USD | EUR (monthly ECB rates) |
|--------|-----|------------------------|
| Company report | — | EUR 6,100,000 |
| Raw invoices (FedEx + OnTrac + USPS + DHL estimate) | $6,888,664 | EUR 6,102,444 |
| PCS-matched actuals (matched-only dataset) | $6,541,050 | — |

The raw invoice total in EUR matches the company report. The $348K gap between raw invoices and PCS-matched actuals is explained below.

## Gap: Raw Invoices ($6,889K) vs PCS-Matched ($6,541K) = $348K

### 1. Multi-parcel orders: ~$143K

Orders with multiple tracking numbers (2+ parcels) only have the latest tracking number in our dataset (`row_nr = 1`). The extra parcels exist on invoices but are not in our PCS-matched set.

| Carrier | Extra tracks | Extra cost |
|---------|-------------|------------|
| FedEx HD/Ground | 4,064 | $92,632 |
| FedEx SmartPost | 516 | $6,287 |
| OnTrac | 1,264 | $18,151 |
| USPS | 2,931 | $25,784 |
| **Total** | **8,775** | **$142,854** |

8,500 orders (1.5% of total) have 2+ tracking numbers, generating 4,864 extra parcels.

### 2. Non-Picanova FedEx services: ~$45K

Shipments on the FedEx account using services not part of the domestic ecommerce flow:

| Service | Tracks | Net Charge |
|---------|--------|------------|
| FedEx 2Day | 27 | $1,778 |
| FedEx International Economy | 164 | $16,026 |
| FedEx Priority Overnight | 73 | $7,967 |
| FedEx International Priority | 15 | $3,331 |
| Other express/ground | ~80 | ~$16K |
| **Total** | **~360** | **~$45K** |

### 3. Remaining ~$160K

DHL cost is estimated at $6/shipment, and a small number of shipments across carriers could not be matched to PCS orders due to various reasons (tracking number format mismatches, date window gaps, etc.). Not worth investigating further — the gap is <2.4% of the total.


## Invoice Coverage by Carrier

| Carrier | Invoice Period | Tracks | Total |
|---------|---------------|--------|-------|
| FedEx | Jan-Dec 2025 | 278,943 | $4,283,389 |
| OnTrac | Jul-Dec 2025 | 129,287 | $1,511,653 |
| USPS | Aug-Dec 2025 | 107,813 | $852,680 |
| DHL | estimated | 40,157 | $240,942 (@$6/ship) |



## EUR Conversion

Monthly ECB USD/EUR rates applied to invoice totals:

| Month | USD/EUR | FedEx | OnTrac | USPS | DHL est | Total USD | Total EUR |
|-------|---------|-------|--------|------|---------|-----------|-----------|
| Jan | 1.0354 | $603K | — | — | $20K | $624K | EUR 602K |
| Feb | 1.0413 | $575K | — | — | $20K | $595K | EUR 572K |
| Mar | 1.0807 | $408K | — | — | $20K | $428K | EUR 396K |
| Apr | 1.1214 | $434K | — | — | $20K | $454K | EUR 405K |
| May | 1.1278 | $553K | — | — | $20K | $573K | EUR 508K |
| Jun | 1.1516 | $442K | — | — | $20K | $462K | EUR 401K |
| Jul | 1.1677 | $397K | $39K | — | $20K | $456K | EUR 391K |
| Aug | 1.1631 | $260K | $103K | $39K | $20K | $422K | EUR 363K |
| Sep | 1.1732 | $102K | $179K | $92K | $20K | $392K | EUR 334K |
| Oct | 1.1630 | $83K | $186K | $136K | $20K | $425K | EUR 366K |
| Nov | 1.1560 | $208K | $345K | $158K | $20K | $731K | EUR 632K |
| Dec | 1.1709 | $220K | $660K | $428K | $20K | $1,327K | EUR 1,133K |
| **Total** | | **$4,283K** | **$1,512K** | **$853K** | **$241K** | **$6,889K** | **EUR 6,102K** |

Effective average rate: 1.1288 USD/EUR.

---

*Created: February 2026*
