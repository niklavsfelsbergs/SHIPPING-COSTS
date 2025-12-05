-- Load OnTrac Shipments from PCS Database
--
-- Parameters (replaced at runtime):
--   {start_date_filter} - Start date filter clause
--   {end_date_filter} - End date filter clause
--   {limit_clause} - Optional limit clause

with trackingnumbers as (
    select
        orderid,
        trackingnumber,
        row_number() over (partition by orderid order by id desc) as row_nr
    from bi_stage_dev_dbo.pcsu_sentparcels
)

select
    po.ordernumber as pcs_ordernumber,
    po.id as pcs_orderid,
    tn.trackingnumber,
    po.createddate as pcs_created,
    (po.createddate + interval '2 days')::date as ship_date,
    po.shopreferencenumber1 as shop_ordernumber,
    pp."name" as production_site,
    po.shippingzipcode as shipping_zip_code,
    po.shippingregion as shipping_region,
    pc."name" as shipping_country,
    GREATEST(po.packagelength, po.packagewidth) / 10.0 * 0.39370079::float8 as length_in,
    LEAST(po.packagelength, po.packagewidth) / 10.0 * 0.39370079::float8 as width_in,
    po.packageheight / 10.0 * 0.39370079::float8 as height_in,
    po.packageweight * 2.20462262::float8 as weight_lbs

from bi_stage_dev_dbo.pcsu_orders po
join bi_stage_dev_dbo.pcsu_countries pc on pc.id = po.shippingcountryid
join bi_stage_dev_dbo.pcsu_productionsites pp on pp.id = po.productionsiteid
join bi_stage_dev_dbo.pcsu_shippingproviders ps on ps.id = po.shippingproviderid
left join trackingnumbers tn on tn.orderid = po.id and tn.row_nr = 1

where ps.extkey = 'ONTRAC'
  and pp."name" in ('Columbus', 'Phoenix')
  {start_date_filter}
  {end_date_filter}
{limit_clause}
