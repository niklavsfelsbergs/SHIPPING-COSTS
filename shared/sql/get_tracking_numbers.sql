-- Get tracking numbers for given orderids
-- Parameter: {pcs_orderids} - comma-separated list of orderids

SELECT
    orderid as pcs_orderid,
    trackingnumber
FROM bi_stage_dev_dbo.pcsu_sentparcels
WHERE orderid IN ({pcs_orderids})
  AND trackingnumber IS NOT NULL
