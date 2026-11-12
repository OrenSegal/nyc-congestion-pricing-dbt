"""Extract step: land NYC TLC trip records as weekly origin-destination counts.

Reads only the needed columns straight from the TLC's public parquet files (DuckDB range
requests, so whole files are never downloaded) and writes one small parquet per
service-month to data/landing/. Trip-level rows never touch disk.

Grain of the output: service, week (Monday start), pickup zone, dropoff zone, and
whether the trip started in the toll's peak hours (5am-9pm weekdays, 9am-9pm weekends,
per the MTA schedule).

Re-running skips months already landed. The TLC server rate-limits, so the script
pauses between files and waits out 403s. Row counts go to data_manifest.csv.

Usage: python scripts/extract.py
"""
import csv
import datetime as dt
import sys
import time
from pathlib import Path

import duckdb

BASE = "https://d37ci6vzurychx.cloudfront.net/trip-data/"
# October-June "seasons". The toll started 5 Jan 2025, in the middle of the 2024-25 season.
SEASONS = [2022, 2023, 2024, 2025]          # season start years
MONTHS = [(0, 10), (0, 11), (0, 12), (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6)]
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "landing"
MANIFEST = ROOT / "data_manifest.csv"
PAUSE_SECONDS = 45

# Yellow taxi files have no trip_time column, so derive minutes from the timestamps.
SERVICES = {
    "yellow": dict(pickup="tpep_pickup_datetime", miles="trip_distance",
                   minutes="date_diff('second', tpep_pickup_datetime, tpep_dropoff_datetime) / 60.0"),
    "fhvhv": dict(pickup="pickup_datetime", miles="trip_miles", minutes="trip_time / 60.0"),
}
# A trip counts toward speed only if its duration, distance and speed are plausible.
VALID = "minutes between 1 and 180 and miles between 0.1 and 100 and miles / (minutes / 60) < 80"

SQL = """
copy (
    with t as (
        select
            cast({pickup} as date)           as pickup_date,
            case when isodow({pickup}) >= 6 then hour({pickup}) between 9 and 20
                 else hour({pickup}) between 5 and 20 end as is_peak,
            PULocationID                     as pu_zone_id,
            DOLocationID                     as do_zone_id,
            cast({miles} as double)          as miles,
            cast({minutes} as double)        as minutes,
            {fee}                            as fee
        from read_parquet('{url}')
        where {pickup} >= date '{start}' and {pickup} < date '{start}' + interval 1 month
    )
    select
        '{service}'                                       as service,
        date_trunc('week', pickup_date)::date             as week_start,
        is_peak,
        pu_zone_id,
        do_zone_id,
        count(*)                                          as trips,
        count(*) filter (where fee > 0)                   as fee_trips,
        count(*) filter (where {valid})                   as timed_trips,
        coalesce(sum(miles) filter (where {valid}), 0)    as timed_miles,
        coalesce(sum(minutes) filter (where {valid}), 0)  as timed_minutes
    from t
    group by all
) to '{out}' (format parquet)
"""


def with_retry(fn):
    for attempt in range(6):
        try:
            return fn()
        except duckdb.HTTPException as e:
            if attempt == 5:
                raise
            print(f"server refused ({str(e)[:60]}...), waiting 10 min", flush=True)
            time.sleep(600)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("install httpfs; load httpfs")
    new_manifest = not MANIFEST.exists()
    with MANIFEST.open("a", newline="") as fh:
        log = csv.writer(fh)
        if new_manifest:
            log.writerow(["file", "pulled_on", "trips_in_month"])
        for service, cols in SERVICES.items():
            for season in SEASONS:
                for add_year, m in MONTHS:
                    y = season + add_year
                    name = f"{service}_tripdata_{y}-{m:02d}.parquet"
                    out = OUT / f"{service}_{y}-{m:02d}.parquet"
                    if out.exists():
                        continue
                    url = BASE + name
                    columns = with_retry(lambda: [r[0] for r in con.execute(
                        f"describe select * from read_parquet('{url}')").fetchall()])
                    fee = "cbd_congestion_fee" if "cbd_congestion_fee" in columns else "0"
                    tmp = out.with_suffix(".tmp")
                    sql = SQL.format(url=url, service=service, start=f"{y}-{m:02d}-01",
                                     out=tmp, valid=VALID, fee=fee, **cols)
                    with_retry(lambda: con.execute(sql))
                    tmp.rename(out)  # only complete files get the final name
                    n = con.execute(f"select sum(trips) from '{out}'").fetchone()[0]
                    log.writerow([name, dt.date.today().isoformat(), n])
                    fh.flush()
                    print("landed", out.name, n, flush=True)
                    time.sleep(PAUSE_SECONDS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
