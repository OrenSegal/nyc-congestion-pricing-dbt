-- Typed and renamed landing data. A week that spans a month boundary arrives split
-- across two files, so re-sum to one row per service, week, period and zone pair.
select
    case service when 'fhvhv' then 'uber_lyft' else 'yellow_taxi' end as service,
    cast(week_start as date)                        as week_start,
    cast(is_peak as boolean)                        as is_peak,
    cast(pu_zone_id as {{ dbt.type_int() }})        as pickup_zone_id,
    cast(do_zone_id as {{ dbt.type_int() }})        as dropoff_zone_id,
    sum(trips)                                      as trips,
    sum(fee_trips)                                  as fee_trips,
    sum(timed_trips)                                as timed_trips,
    sum(timed_miles)                                as timed_miles,
    sum(timed_minutes)                              as timed_minutes
from {{ source('tlc', 'weekly_od') }}
group by 1, 2, 3, 4, 5
