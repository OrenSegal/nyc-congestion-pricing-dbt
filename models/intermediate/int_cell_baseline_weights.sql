-- Fixed weights for the mix-adjusted speed. A cell is one service, zone pair and
-- peak/overnight period. Its weight is the miles it carried in the baseline season.
-- Small cells are dropped because their weekly speed is mostly noise.
select
    service,
    is_peak,
    pickup_zone_id,
    dropoff_zone_id,
    segment,
    sum(timed_trips)                                as baseline_timed_trips,
    sum(timed_miles)                                as baseline_miles
from {{ ref('int_od_weekly') }}
where season = {{ var('baseline_season') }}
  and aligned_week between cast('{{ var("first_week") }}' as date) and cast('{{ var("last_week") }}' as date)
  and segment != 'excluded'
group by 1, 2, 3, 4, 5
having sum(timed_trips) >= {{ var('min_baseline_trips') }}
