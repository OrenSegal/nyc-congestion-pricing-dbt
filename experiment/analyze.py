"""Readout for the congestion pricing study. Follows ANALYSIS_PLAN.md.

Reads the dbt mart fct_weekly_segment from the local DuckDB file and writes
experiment/results.md plus two charts. Run after `dbt build`. With --check it runs every
calculation and prints the tables but writes nothing (used by CI on the sample data).

The estimate, in words: for each week, take the year-over-year change (log scale) for a
treated segment and subtract the same change for the comparison group. That weekly "gap"
should sit near some level before the toll and shift after it. The effect is the shift.
"""
import sys
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parent.parent
CONTROL = "rest_of_city"
TOLL, PLACEBO = (2024, 2023), (2023, 2022)   # (season, season it is compared with)
HAC_LAGS = 4
CHECK_ONLY = "--check" in sys.argv   # CI: run every calculation, write nothing
LABEL = {"inside_zone": "Inside the zone", "crossing_zone": "Into or out of the zone",
         "manhattan_outside_zone": "Manhattan outside the zone", CONTROL: "Rest of city"}

fct = duckdb.connect(str(ROOT / "congestion.duckdb"), read_only=True).execute(
    "select * from fct_weekly_segment").df()
fct["aligned_week"] = pd.to_datetime(fct["aligned_week"])
PERIOD = fct.drop_duplicates("aligned_week").set_index("aligned_week")["period"].sort_index()


def series(metric, segment, service=None, peak=None):
    """Weekly values of a metric for one segment. Rows = aligned week, columns = season."""
    d = fct[fct.segment == segment]
    if service is not None:
        d = d[d.service == service]
    if peak is not None:
        d = d[d.is_peak == peak]
    g = d.groupby(["aligned_week", "season"])[
        ["trips", "timed_miles", "timed_minutes", "mix_weight", "mix_weighted_pace"]].sum()
    if metric == "trips":
        v = g.trips
    elif metric == "speed":          # mix-adjusted mph
        v = 60 / (g.mix_weighted_pace / g.mix_weight)
    elif metric == "raw_speed":      # plain mph, trip mix free to change
        v = g.timed_miles / (g.timed_minutes / 60)
    return v.unstack("season")


def gap(metric, segment, pair, **slice_):
    """Weekly gap: year-over-year log change in the segment minus the same for the comparison group."""
    s1, s0 = pair
    seg, ctl = np.log(series(metric, segment, **slice_)), np.log(series(metric, CONTROL, **slice_))
    return (seg[s1] - seg[s0]) - (ctl[s1] - ctl[s0])


def shift(g):
    """Average gap after the toll date minus average gap before it, Newey-West 95% CI."""
    d = pd.DataFrame({"gap": g, "period": PERIOD}).query("period != 'transition'").dropna()
    x = sm.add_constant((d.period == "after").astype(float).rename("after"))
    fit = sm.OLS(d.gap, x).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})
    lo, hi = fit.conf_int().loc["after"]
    return dict(est=fit.params["after"], lo=lo, hi=hi, se=fit.bse["after"], p=fit.pvalues["after"],
                n_before=int((d.period == "before").sum()), n_after=int((d.period == "after").sum()))


def pct(x):
    return f"{100 * (np.exp(x) - 1):+.1f}%"


def row(name, metric, segment, **slice_):
    """One results-table row: the toll-year estimate next to the placebo-year estimate."""
    m, pl = shift(gap(metric, segment, TOLL, **slice_)), shift(gap(metric, segment, PLACEBO, **slice_))
    ROWS.append((name, m, pl))
    return (f"| {name} | {pct(m['est'])} | [{pct(m['lo'])}, {pct(m['hi'])}] | "
            f"{pct(pl['est'])} | [{pct(pl['lo'])}, {pct(pl['hi'])}] |")


HEAD = ("| | Toll year (2024-25 vs 2023-24) | 95% CI | Placebo year (2023-24 vs 2022-23) | 95% CI |\n"
        "|---|---|---|---|---|")
ROWS, out = [], []
p = out.append

# --- What is in the data -------------------------------------------------------------
weeks = PERIOD.value_counts()
p("## Data")
p(f"- Seasons: {', '.join(str(int(x)) for x in sorted(fct.season.unique()))} (start year). Weeks per season: {len(PERIOD)} "
  f"({weeks['before']} before the toll date, 1 transition week left out, {weeks['after']} after).")
tot = fct.groupby(["season", "segment"]).trips.sum().unstack("segment")
p("- Trips in the comparison window, millions:\n")
p("| Season | " + " | ".join(LABEL[s] for s in LABEL) + " |")
p("|---|" + "---|" * len(LABEL))
for s in tot.index:
    p(f"| {s}-{str(s + 1)[2:]} | " + " | ".join(f"{tot.loc[s, seg] / 1e6:.1f}" for seg in LABEL) + " |")
cov = fct.groupby("segment").apply(
    lambda g: g.covered_miles.sum() / g.timed_miles.sum(), include_groups=False)
p(f"\n- Mix-adjusted speed uses cells that cover {100 * cov['inside_zone']:.0f}% of timed miles (all seasons) inside "
  f"the zone and {100 * cov[CONTROL]:.0f}% in the rest of the city.")

# --- Speeds in plain numbers ---------------------------------------------------------
p("\n## Average speed in mph (mix-adjusted), January-June weeks")
p("| Season | Inside the zone | Rest of city |")
p("|---|---|---|")
after = PERIOD[PERIOD == "after"].index
for s in sorted(fct.season.unique()):
    vals = [series("speed", seg).loc[after, s].mean() for seg in ("inside_zone", CONTROL)]
    p(f"| {s}-{str(s + 1)[2:]} | {vals[0]:.2f} | {vals[1]:.2f} |")

# --- Primary and secondary ------------------------------------------------------------
p("\n## Primary: speed inside the zone (mix-adjusted, all hours)")
p(HEAD)
p(row("Speed inside the zone", "speed", "inside_zone"))
primary, placebo = ROWS[-1][1], ROWS[-1][2]
ratio = abs(placebo["est"]) / abs(primary["est"])
p(f"\n- Decision rule from the plan: placebo is {100 * ratio:.0f}% the size of the main estimate "
  f"({'ABOVE' if ratio > 0.5 else 'below'} the 50% line).")
p(f"- Smallest shift this design would reliably detect (2.8 x standard error): {100 * 2.8 * primary['se']:.1f}%.")

p("\n## Secondary: number of trips")
p(HEAD)
p(row("Trips inside the zone", "trips", "inside_zone"))
p(row("Trips into or out of the zone", "trips", "crossing_zone"))

p("\n## Check: peak vs overnight (speed inside the zone)")
p(HEAD)
p(row("Peak hours", "speed", "inside_zone", peak=True))
p(row("Overnight", "speed", "inside_zone", peak=False))

p("\n## Check: spillover to Manhattan outside the zone")
p(HEAD)
p(row("Speed, Manhattan outside the zone", "speed", "manhattan_outside_zone"))
p(row("Trips, Manhattan outside the zone", "trips", "manhattan_outside_zone"))

p("\n## Sensitivity (same estimate, different choices)")
p(HEAD)
p(row("Speed inside, trip mix not held fixed", "raw_speed", "inside_zone"))
p(row("Speed inside, Uber/Lyft only", "speed", "inside_zone", service="uber_lyft"))
p(row("Speed inside, yellow taxi only", "speed", "inside_zone", service="yellow_taxi"))
p(row("Trips inside, Uber/Lyft only", "trips", "inside_zone", service="uber_lyft"))
p(row("Trips inside, yellow taxi only", "trips", "inside_zone", service="yellow_taxi"))

# --- Did it last? (description, not a test) -------------------------------------------
if 2025 in fct.season.unique():
    p("\n## Second toll season (2025-26 vs 2023-24), description only")
    p("Average gap over the same January-June weeks, minus the pre-toll gap from autumn 2024.")
    for name, metric, seg in [("Speed inside the zone", "speed", "inside_zone"),
                              ("Trips inside the zone", "trips", "inside_zone"),
                              ("Trips into or out of the zone", "trips", "crossing_zone")]:
        base = gap(metric, seg, TOLL)[PERIOD == "before"].mean()
        g2 = gap(metric, seg, (2025, 2023))
        p(f"- {name}: {pct(g2[PERIOD == 'after'].mean() - base)} "
          f"(first toll season, same weeks: {pct(gap(metric, seg, TOLL)[PERIOD == 'after'].mean() - base)})")

print("\n".join(out))
if CHECK_ONLY:
    sys.exit(0)
(ROOT / "experiment" / "results.md").write_text(
    "# Results (generated by experiment/analyze.py, do not edit by hand)\n\n"
    "Every estimate is a shift in the weekly gap between a segment and the rest of the city, "
    "after vs before the toll's calendar date, shown as a percent. See ANALYSIS_PLAN.md.\n\n"
    + "\n".join(out) + "\n")

# --- Charts ----------------------------------------------------------------------------
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharex=True)
for ax, (metric, title) in zip(axes, [("speed", "Speed inside the zone"), ("trips", "Trips inside the zone")]):
    for pair, color, name in [(PLACEBO, "#9aa0a6", "Year before (no toll)"), (TOLL, "#C44E52", "Toll year")]:
        g = gap(metric, "inside_zone", pair)
        g = g - g[PERIOD == "before"].mean()   # centre on the autumn level so the two years compare
        ax.plot(g.index, 100 * (np.exp(g) - 1), color=color, lw=2, label=name)
    ax.axvline(pd.Timestamp("2025-01-05"), color="black", ls=":", lw=1)
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_title(title)
    ax.set_ylabel("Change vs rest of city (%)")
    ax.set_xticks(pd.to_datetime(["2024-10-07", "2024-12-02", "2025-02-03", "2025-04-07", "2025-06-02"]),
                  ["Oct", "Dec", "Feb", "Apr", "Jun"])
axes[0].legend(frameon=False, fontsize=9)
axes[0].annotate("toll starts\n5 Jan", (pd.Timestamp("2025-01-05"), axes[0].get_ylim()[1]),
                 xytext=(5, -28), textcoords="offset points", fontsize=9)
fig.suptitle("Weekly year-over-year change relative to the rest of the city (autumn average = 0)", fontsize=11)
fig.tight_layout()
fig.savefig(ROOT / "charts" / "weekly_gap.png", dpi=150)

fig, ax = plt.subplots(figsize=(8.5, 0.5 * len(ROWS) + 1.6))
y = np.arange(len(ROWS))[::-1]
for off, idx, color, name in [(0.16, 1, "#C44E52", "Toll year"), (-0.16, 2, "#9aa0a6", "Placebo year")]:
    est = np.array([100 * (np.exp(r[idx]["est"]) - 1) for r in ROWS])
    lo = np.array([100 * (np.exp(r[idx]["lo"]) - 1) for r in ROWS])
    hi = np.array([100 * (np.exp(r[idx]["hi"]) - 1) for r in ROWS])
    ax.errorbar(est, y + off, xerr=[est - lo, hi - est], fmt="o", color=color, capsize=3, label=name)
ax.axvline(0, color="grey", lw=0.8)
ax.set_yticks(y, [r[0] for r in ROWS])
ax.set_xlabel("Shift after the toll date, relative to rest of city (%), with 95% CI")
ax.legend(frameon=False, fontsize=9)
fig.tight_layout()
fig.savefig(ROOT / "charts" / "estimates.png", dpi=150)
