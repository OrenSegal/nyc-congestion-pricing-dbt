select season, aligned_week, segment, service, is_peak, count(*) as n
from {{ ref('fct_weekly_segment') }}
group by 1, 2, 3, 4, 5
having count(*) > 1
