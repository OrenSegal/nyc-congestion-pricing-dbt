-- Analysis table. Grain: season x aligned week x segment x service x peak/overnight.
-- Carries raw totals plus the two sums needed for a mix-adjusted speed:
--   mix-adjusted pace (minutes per mile) = weighted_pace / weight, summed over any slice.
with od as (
    select *
    from {{ ref('int_od_weekly') }}
    where aligned_week between cast('{{ var("first_week") }}' as date) and cast('{{ var("last_week") }}' as date)
      and segment != 'excluded'
)
select
    od.season,
    od.aligned_week,
    od.segment,
    od.service,
    od.is_peak,
    case
        when od.aligned_week < cast('{{ var("transition_week") }}' as date) then 'before'
        when od.aligned_week = cast('{{ var("transition_week") }}' as date) then 'transition'
        else 'after'
    end                                             as period,
    sum(od.trips)                                   as trips,
    sum(od.fee_trips)                               as fee_trips,
    sum(od.timed_trips)                             as timed_trips,
    sum(od.timed_miles)                             as timed_miles,
    sum(od.timed_minutes)                           as timed_minutes,
    sum(case when w.baseline_miles is not null then od.timed_miles end)                            as covered_miles,
    sum(case when od.timed_miles > 0 then w.baseline_miles end)                                    as mix_weight,
    sum(case when od.timed_miles > 0 then w.baseline_miles * od.timed_minutes / od.timed_miles end) as mix_weighted_pace
from od
left join {{ ref('int_cell_baseline_weights') }} w
    on  w.service = od.service
    and w.is_peak = od.is_peak
    and w.pickup_zone_id = od.pickup_zone_id
    and w.dropoff_zone_id = od.dropoff_zone_id
group by 1, 2, 3, 4, 5, 6
