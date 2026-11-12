-- Headline numbers per season, segment and period (before/after the toll's calendar date).
select
    season,
    segment,
    period,
    count(distinct aligned_week)                                     as weeks,
    sum(trips) / count(distinct aligned_week)                        as trips_per_week,
    sum(timed_miles) / (sum(timed_minutes) / 60.0)                   as avg_mph,
    60.0 / (sum(mix_weighted_pace) / sum(mix_weight))                as mix_adjusted_mph,
    sum(fee_trips) * 1.0 / sum(trips)                                as share_charged_fee
from {{ ref('fct_weekly_segment') }}
where period != 'transition'
group by 1, 2, 3
