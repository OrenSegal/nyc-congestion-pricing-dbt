-- After the start, at least 80% of trips inside the zone are charged, in the first
-- toll season and the next one. Guards the zone list and confirms the charge is still on.
select season, sum(fee_trips) * 1.0 / sum(trips) as share
from {{ ref('fct_weekly_segment') }}
where segment = 'inside_zone'
  and ((season = 2024 and period = 'after') or season = 2025)
group by 1
having sum(fee_trips) * 1.0 / sum(trips) < 0.8
