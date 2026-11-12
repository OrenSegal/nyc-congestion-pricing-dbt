"""Cut a small sample of the landed data for CI and for trying the project without the
full download: every week and both services, but only trips between 24 taxi zones
(8 inside the toll zone, 4 next to it, 4 elsewhere in Manhattan, 8 in other boroughs).

Usage: python scripts/make_fixture.py   (after scripts/extract.py)
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
ZONES = [161, 230, 79, 48, 234, 231, 87, 13,      # inside the zone
         142, 237, 141, 43,                        # next to the boundary
         238, 239, 236, 41,                        # Manhattan above 60th St
         7, 181, 138, 132, 129, 61, 255, 168]      # Queens, Brooklyn, Bronx
duckdb.execute(f"""
copy (
    select * from read_parquet('{ROOT}/data/landing/*.parquet')
    where pu_zone_id in {tuple(ZONES)} and do_zone_id in {tuple(ZONES)}
    order by service, week_start, pu_zone_id, do_zone_id, is_peak
) to '{ROOT}/fixtures/weekly_od_sample.parquet' (format parquet, compression zstd)
""")
print(duckdb.execute(f"select count(*), sum(trips) from '{ROOT}/fixtures/weekly_od_sample.parquet'").fetchall())
