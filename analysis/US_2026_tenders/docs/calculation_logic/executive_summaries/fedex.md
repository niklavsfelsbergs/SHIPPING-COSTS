# FedEx Shipping Cost - Executive Summary

FedEx shipping costs consist of a base rate, surcharges for special handling, and a fuel surcharge. We use two FedEx services: **Home Delivery** (residential packages up to 150 lbs) and **Ground Economy/SmartPost** (economical service up to 71 lbs).

---

## Base Rate

The base rate uses a **4-part structure**:

- **Undiscounted Rate** - The published price based on package weight and destination zone
- **Performance Pricing** - A volume-based discount (currently $0 due to reduced shipping volume)
- **Earned Discount** - Additional negotiated discount (currently $0)
- **Grace Discount** - Promotional discount (currently $0)

The rate depends on:
- **Weight** - The higher of actual weight or dimensional weight (volume / 250 for Home Delivery, volume / 139 for Ground Economy)
- **Zone** - Distance from origin (Phoenix or Columbus) to destination, ranging from zone 2 (nearby) to zone 9+ (Alaska/Hawaii)

---

## Surcharges

### Residential Surcharge
- **Applies to:** All Home Delivery shipments
- **Cost:** $2.08 per package
- **Why:** Home Delivery is exclusively for residential addresses

### Delivery Area Surcharge (DAS)
- **Applies to:** Packages going to remote or hard-to-reach ZIP codes
- **Cost:** $2.17 to $43.00 depending on tier
  - Standard DAS: $2.17 (HD) / $3.10 (SmartPost)
  - Extended DAS: $2.91 (HD) / $4.15 (SmartPost)
  - Remote DAS: $5.43 (HD only)
  - Hawaii: $14.50 (HD) / $8.30 (SmartPost)
  - Alaska: $43.00 (HD) / $8.30 (SmartPost)
- **Why:** Higher delivery costs in rural and remote areas

### Additional Handling - Dimensions (AHS)
- **Applies to:** Home Delivery packages exceeding size thresholds:
  - Longest side over 48 inches
  - Second-longest side over 30.3 inches
  - Length plus girth over 106 inches
- **Cost:** $8.60 per package
- **Why:** Oversized packages require special handling equipment

### Additional Handling - Weight (AHS Weight)
- **Applies to:** All packages over 50 lbs
- **Cost:** $26.38 per package
- **Why:** Heavy packages require manual handling or equipment

### Oversize Surcharge
- **Applies to:** Home Delivery packages that are extremely large:
  - Longest side over 96 inches
  - Length plus girth over 130 inches
  - Volume over 17,280 cubic inches (12 cubic feet)
  - Weight over 110 lbs
- **Cost:** $115.00 per package
- **Why:** Requires specialized transport and handling

**Note:** Only one dimensional surcharge applies per package - the most expensive one wins (Oversize > AHS Weight > AHS Dimensions).

### Peak Season Demand Surcharges
During the holiday peak period (late September through mid-January):

- **Base Demand (Home Delivery only):** $0.40 to $0.65 per package
- **Demand AHS:** $4.13 to $5.45 per package (when AHS or AHS Weight applies)
- **Demand Oversize:** $45.00 to $54.25 per package (when Oversize applies)

**Why:** Higher rates during peak shipping season to manage capacity

---

## Fuel Surcharge

- **Rate:** 10% of the undiscounted rate plus all surcharges
- **Why:** Covers fuel cost fluctuations

---

## Service Differences Summary

| Feature | Home Delivery | Ground Economy (SmartPost) |
|---------|---------------|---------------------------|
| Max weight | 150 lbs | 71 lbs |
| DIM factor | 250 | 139 |
| Residential surcharge | Yes ($2.08) | No |
| AHS Dimensions | Yes ($8.60) | No |
| Oversize | Yes ($115.00) | No |
| Base demand surcharge | Yes | No |
| DAS rates | Higher | Lower |

---

## Optimal Service Selection (All-US Analysis)

For optimization scenarios, we calculate costs for **both** services and pick the cheaper option:

1. Calculate Home Delivery cost
2. Calculate SmartPost cost
3. If weight ≤ 70 lbs AND SmartPost is cheaper → use SmartPost
4. Otherwise → use Home Delivery

**SmartPost typically wins** for smaller, lighter packages due to:
- No residential surcharge ($2.08 savings)
- No AHS-Dimensions surcharge
- No base demand surcharge during peak

**Home Delivery typically wins** for larger packages where SmartPost's lower DIM factor (139 vs 250) would significantly inflate the billable weight.

---

## Total Cost Formula

**Total = Base Rate + Surcharges + Fuel**

Where:
- Base Rate = Undiscounted Rate - Performance Pricing - Earned Discount - Grace Discount
- Surcharges = Residential + DAS + AHS (if applicable) + Demand (if peak season)
- Fuel = 10% of (Undiscounted Rate + Surcharges)
