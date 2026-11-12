"""Work out which TLC taxi zones are inside the congestion relief zone, from the data.

A trip that starts and ends in the same taxi zone is charged the congestion fee almost
only when that taxi zone is inside the toll zone. So for each taxi zone, take March 2025
yellow taxi trips that start and end there and compute the share charged the fee.
Zones split cleanly: inside (share above 0.7), next to the boundary (0.1 to 0.5, some
routes dip into the zone), and everything else (under 0.05).

Writes seeds/cbd_zones.csv (zone_id, zone_role, same_zone_trips, share_charged).
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2025-03.parquet"
MIN_TRIPS = 20

con = duckdb.connect()
con.execute("install httpfs; load httpfs")
con.execute(f"""
copy (
    select
        PULocationID                                          as zone_id,
        case when avg((cbd_congestion_fee > 0)::int) > 0.5 then 'inside'
             else 'adjacent' end                              as zone_role,
        count(*)                                              as same_zone_trips,
        round(avg((cbd_congestion_fee > 0)::int), 3)          as share_charged
    from read_parquet('{URL}')
    where PULocationID = DOLocationID
      and PULocationID not in (264, 265)   -- unknown / outside NYC
    group by 1
    having count(*) >= {MIN_TRIPS} and avg((cbd_congestion_fee > 0)::int) >= 0.1
    order by share_charged desc
) to '{ROOT / "seeds" / "cbd_zones.csv"}' (header)
""")
print(con.execute(f"""
    select z.Zone, t.n, t.share from (
        select PULocationID id, count(*) n, round(avg((cbd_congestion_fee > 0)::int), 3) share
        from read_parquet('{URL}') where PULocationID = DOLocationID group by 1
    ) t join '{ROOT / "seeds" / "taxi_zones.csv"}' z on z.LocationID = t.id
    where z.Borough = 'Manhattan' and t.n < {MIN_TRIPS} order by t.n desc
""").fetchall())
