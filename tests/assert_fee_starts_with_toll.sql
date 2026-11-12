-- The fee column is the data's own record of the start date: nothing charged before
-- the transition week.
select *
from {{ ref('int_od_weekly') }}
where fee_trips > 0
  and week_start < cast('{{ var("transition_week") }}' as date)
