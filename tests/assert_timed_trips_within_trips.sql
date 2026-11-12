select * from {{ ref('fct_weekly_segment') }}
where timed_trips > trips or timed_trips < 0 or timed_minutes < 0 or timed_miles < 0
