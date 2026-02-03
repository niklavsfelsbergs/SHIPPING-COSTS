-- Load Shipments from PCS Database (with country filter)
--
-- Parameters (replaced at runtime):
--   {carrier_filter} - Carrier filter clause (e.g., "and ps.extkey = 'ONTRAC'")
--   {production_sites_filter} - Production sites filter clause
--   {country_filter} - Country filter clause (e.g., "and pc.\"name\" = 'United States of America'")
--   {start_date_filter} - Start date filter clause
--   {end_date_filter} - End date filter clause
--   {limit_clause} - Optional limit clause

with trackingnumbers as (
    select
        orderid,
        trackingnumber,
        count(*) over (partition by orderid) as trackingnumber_count,
        row_number() over (partition by orderid order by id desc) as row_nr
    from bi_stage_dev_dbo.pcsu_sentparcels
)

select
    po.ordernumber as pcs_ordernumber,
    po.id as pcs_orderid,
    tn.trackingnumber as latest_trackingnumber,
    tn.trackingnumber_count,
    po.createddate as pcs_created,
    (po.createddate + interval '2 days')::date as ship_date,
    po.shopreferencenumber1 as shop_ordernumber,
    pp."name" as production_site,
    po.shippingzipcode as shipping_zip_code,
    po.shippingregion as shipping_region,
    pc."name" as shipping_country,
    po.packagetype,
    ps.extkey as pcs_shipping_provider,
    -- Metric (source units: mm, kg)
    GREATEST(po.packagelength, po.packagewidth) / 10.0 as length_cm,
    LEAST(po.packagelength, po.packagewidth) / 10.0 as width_cm,
    po.packageheight / 10.0 as height_cm,
    po.packageweight as weight_kg,
    -- Imperial (converted)
    GREATEST(po.packagelength, po.packagewidth) / 10.0 * 0.39370079::float8 as length_in,
    LEAST(po.packagelength, po.packagewidth) / 10.0 * 0.39370079::float8 as width_in,
    po.packageheight / 10.0 * 0.39370079::float8 as height_in,
    po.packageweight * 2.20462262::float8 as weight_lbs

from bi_stage_dev_dbo.pcsu_orders po
join bi_stage_dev_dbo.pcsu_countries pc on pc.id = po.shippingcountryid
join bi_stage_dev_dbo.pcsu_productionsites pp on pp.id = po.productionsiteid
join bi_stage_dev_dbo.pcsu_shippingproviders ps on ps.id = po.shippingproviderid
left join trackingnumbers tn on tn.orderid = po.id and tn.row_nr = 1

where 1=1
  {carrier_filter}
  {production_sites_filter}
  {country_filter}
  {start_date_filter}
  {end_date_filter}
{limit_clause}
