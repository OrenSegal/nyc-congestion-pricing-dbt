-- One row per TLC taxi zone with its role in the study.
select
    z.locationid                                    as zone_id,
    z.borough,
    z.zone                                          as zone_name,
    case
        when z.borough in ('Unknown', 'EWR', 'N/A') or z.locationid in (264, 265) then 'excluded'
        when c.zone_role = 'inside'                 then 'inside_zone'
        when c.zone_role = 'adjacent'               then 'adjacent_to_zone'
        when z.borough = 'Manhattan'                then 'manhattan_other'
        else 'rest_of_city'
    end                                             as zone_role
from {{ ref('taxi_zones') }} z
left join {{ ref('cbd_zones') }} c on c.zone_id = z.locationid
