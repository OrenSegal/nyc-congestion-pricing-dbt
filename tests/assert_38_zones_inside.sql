-- The derived zone list has 38 zones inside the toll zone. A change means the derivation moved.
select 1 from (select count(*) as n from {{ ref('stg_taxi_zones') }} where zone_role = 'inside_zone') c
where c.n != 38
