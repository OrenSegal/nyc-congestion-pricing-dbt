{# Date plus a number of days, returned as a date on every adapter. #}
{% macro add_days(date_expr, days_expr) -%}
    cast({{ dbt.dateadd('day', days_expr, date_expr) }} as date)
{%- endmacro %}
