-- Zone Analysis Query
-- Used by: ontrac.maintenance.generate_zones
--
-- Joins invoice zone data with PCS production site info to determine
-- the actual zone used for each ZIP code and production site combination.
--
-- Parameters:
--   {created_filter} - Optional filter on po.createddate (e.g., ">= '2025-01-01'")

with trackingnumbers as (
    select
        orderid
        , trackingnumber
        , row_number() over (partition by orderid order by id desc) as row_nr
    from bi_stage_dev_dbo.pcsu_sentparcels
)
, pcs_orders as (
    select
        tn.trackingnumber
        , po.shippingzipcode as shipping_zip_code
        , po.shippingregion as shipping_region
        , pp."name" as production_site
    from bi_stage_dev_dbo.pcsu_orders po
    join bi_stage_dev_dbo.pcsu_productionsites pp on pp.id = po.productionsiteid
    join bi_stage_dev_dbo.pcsu_shippingproviders ps on ps.id = po.shippingproviderid
    left join trackingnumbers tn on tn.orderid = po.id and tn.row_nr = 1
    where 1=1
    and pp."name" in ('Columbus', 'Phoenix')
    and ps.extkey = 'ONTRAC'
    {created_filter}
)
, ontrac_invoices as (
    select
        tracking_number as trackingnumber
        , zone as actual_zone
        , delivery_area_surcharge as das_charge
        , extended_area_surcharge as edas_charge
    from poc_landing.ontrac
    where 1=1
    and service_charge > 0
)
select
    pcs.shipping_zip_code
    , pcs.shipping_region
    , pcs.production_site
    , inv.actual_zone
    , inv.das_charge
    , inv.edas_charge
from pcs_orders pcs
join ontrac_invoices inv on pcs.trackingnumber = inv.trackingnumber
