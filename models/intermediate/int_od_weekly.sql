-- Every zone pair gets a segment (how the trip relates to the toll zone), a season,
-- and a position on the shared 2024-25 calendar so seasons can be compared week for week.
with od as (
    select
        t.*,
        pz.zone_role                                as pickup_role,
        dz.zone_role                                as dropoff_role,
        case when extract(month from t.week_start) >= 10
             then extract(year from t.week_start)
             else extract(year from t.week_start) - 1
        end                                         as season
    from {{ ref('stg_tlc__weekly_od') }} t
    join {{ ref('stg_taxi_zones') }} pz on pz.zone_id = t.pickup_zone_id
    join {{ ref('stg_taxi_zones') }} dz on dz.zone_id = t.dropoff_zone_id
)
select
    service,
    is_peak,
    pickup_zone_id,
    dropoff_zone_id,
    cast(season as {{ dbt.type_int() }})            as season,
    week_start,
    -- 364 days is exactly 52 weeks, so a Monday stays a Monday
    {{ add_days('week_start', '364 * (2024 - cast(season as ' ~ dbt.type_int() ~ '))') }} as aligned_week,
    case
        when pickup_role = 'excluded' or dropoff_role = 'excluded'           then 'excluded'
        when pickup_role = 'inside_zone' and dropoff_role = 'inside_zone'    then 'inside_zone'
        when pickup_role = 'inside_zone' or dropoff_role = 'inside_zone'     then 'crossing_zone'
        when pickup_role = 'rest_of_city' and dropoff_role = 'rest_of_city'  then 'rest_of_city'
        else 'manhattan_outside_zone'
    end                                             as segment,
    trips,
    fee_trips,
    timed_trips,
    timed_miles,
    timed_minutes
from od
