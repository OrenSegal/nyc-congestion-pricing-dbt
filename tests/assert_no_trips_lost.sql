-- The zone joins and segment logic must keep every landed trip exactly once.
select 1
from (select sum(trips) as n from {{ ref('int_od_weekly') }}) a
cross join (select sum(trips) as n from {{ source('tlc', 'weekly_od') }}) s
where a.n != s.n
