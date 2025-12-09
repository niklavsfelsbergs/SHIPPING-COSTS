# DPD UK - External Data Sources

Sources referenced in contract (Quotation 02660977, effective 28 July 2025) that need to be obtained.

## Surcharge Rates (Dynamic)

| Source | URL | Data Needed |
|--------|-----|-------------|
| Fuel & Energy Surcharge | https://www.dpd.co.uk/fuel | Current fuel surcharge percentage |
| Carriage Surcharge | https://www.dpd.co.uk/carriage | Carriage surcharge rates |

## Reference Documents

### DPD Tariff Guide
- **URL:** https://www.dpd.co.uk/pdf/dpd-tariff-guide.pdf
- **Data Needed:**
  - Miscellaneous Air Surcharges
  - Scottish Highlands and Islands postcode list
  - Detailed surcharge application rules
  - Dimension/weight limits

### DPD Terms & Conditions
- **URL:** https://www.dpd.co.uk/terms
- **Data Needed:**
  - Max parcel dimensions
  - Max weights by service
  - Non-Coms criteria
  - Oversize/Overweight thresholds

## Postcode Mapping

Needed to determine destination region (not explicitly provided in contract):

| Region | Postcodes | Notes |
|--------|-----------|-------|
| UK Mainland | Standard England, Scotland, Wales | Excludes Highlands/Islands |
| Scottish Highlands & Islands | ? | Listed in tariff guide |
| Northern Ireland | BT postcodes | Offshore rates |
| Channel Islands | JE, GY postcodes | Offshore rates |
| Isle of Man | IM postcodes | Offshore rates |
| Scilly Isles | TR21-TR25 | Offshore rates |

## Congestion Zones

Contract lists £0.95 congestion surcharge for UK but does not specify which postcodes trigger it. Likely London zones - check tariff guide.

## Status

- [ ] Fetch fuel surcharge rate
- [ ] Fetch carriage surcharge rate
- [ ] Download and parse tariff guide PDF
- [ ] Extract Scottish Highlands/Islands postcodes
- [ ] Extract congestion zone postcodes
- [ ] Confirm Terms & Conditions dimension limits
