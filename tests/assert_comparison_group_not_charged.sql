-- Trips that never touch Manhattan should almost never pay the fee (under 2%).
select season, sum(fee_trips) * 1.0 / sum(trips) as share
from {{ ref('fct_weekly_segment') }}
where segment = 'rest_of_city'
group by 1
having sum(fee_trips) * 1.0 / sum(trips) > 0.02
