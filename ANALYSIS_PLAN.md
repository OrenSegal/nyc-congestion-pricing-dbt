# Analysis plan

Written and committed before any result by segment was computed. The git history shows
this file landing before `experiment/results.md` exists. What I had seen at this point:
total trip counts per file, and the March 2025 fee column used to map the toll zone.

## Question

New York started charging vehicles to enter Manhattan south of 60th St on 5 January 2025.
Using taxi and Uber/Lyft trip records, did trips inside the zone get faster, and did the
number of trips change, compared with what happened in the rest of the city?

What this data can and cannot say: taxis and Uber/Lyft do not pay the $9 daily toll.
Their passengers pay a per-trip charge ($0.75 taxi, $1.50 Uber/Lyft). So trip speed here
is a measure of traffic conditions as for-hire vehicles experience them, and trip volume
reflects a small price increase plus any change in traffic. Neither is a count of private cars.

## Data and groups

- TLC trip records, yellow taxi and high-volume for-hire (Uber/Lyft), October to June for
  four seasons: 2022-23, 2023-24, 2024-25 (toll starts mid-season), 2025-26.
- Toll-zone taxi zones are found from the data (zones where same-zone trips are charged
  the fee), not from a hand-typed list.
- Treated: trips with both ends inside the zone. Also reported: trips with one end inside.
- Comparison group: trips with neither end in Manhattan.
- Spillover check group: Manhattan trips that never enter the zone.
- Dropped: unknown zones and Newark Airport.

## Estimate

Each week is compared with the same week 364 days earlier (same weekday pattern), for the
treated group and the comparison group. The weekly gap between those two year-over-year
changes is the series of interest. The effect is the average gap in the weeks after
5 January 2025 minus the average gap in the weeks before it (October to December 2024).
The week containing 5 January is left out.

- **Primary metric:** average speed of trips inside the zone, all hours, holding the mix
  of trips fixed (each service, zone pair and time-of-day cell keeps its 2023-24 weight),
  so a shift toward shorter or longer trips cannot fake a speed change.
- **Secondary metric:** number of trips inside the zone and crossing into or out of it.

## Checks, fixed in advance

1. **Break at the start date.** The weekly gap should be flat before 5 January and move
   after it. Shown as a chart.
2. **Placebo year.** The same estimate one year earlier (2023-24 vs 2022-23, with a fake
   start date of 8 January 2024), when nothing changed. It should be near zero.
3. **Peak vs overnight.** Private cars pay $9 in peak hours and $2.25 overnight, so a
   traffic effect should be larger in peak hours.
4. **Spillover.** Speed and trips in Manhattan above 60th St, which could get worse if
   traffic is displaced.

Also reported, described as a description and not a test: whether the gap is still there
in the 2025-26 season.

## How I will read the results

- Uncertainty: 95% intervals from the weekly series using Newey-West standard errors
  (4 lags), because neighbouring weeks are not independent.
- There is one toll zone and one start date, so the interval understates the real
  uncertainty. The placebo result is the honest yardstick: if the placebo estimate is
  more than half the size of the main estimate, I will report that this design cannot
  separate the toll's effect from ordinary year-to-year drift.
- Whatever direction the numbers go, they get reported.
