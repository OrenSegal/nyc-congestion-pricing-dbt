-- Each season, segment, service and period must cover the same 37 weeks.
select season, segment, service, is_peak, count(*) as weeks
from {{ ref('fct_weekly_segment') }}
group by 1, 2, 3, 4
having count(*) != 37
