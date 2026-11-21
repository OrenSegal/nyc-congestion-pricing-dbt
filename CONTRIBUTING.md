# Contributing

Open an issue before a large change. Small fixes can go straight to a pull request.

## Checks

CI runs the same commands, so a green run locally should be green there.

```bash
pip install -r requirements.txt
dbt build --vars '{landing_glob: fixtures/weekly_od_sample.parquet, min_baseline_trips: 50}'
python experiment/analyze.py --check
```

## Pull requests

One change per pull request. Say what changes and why. Add or update a test that fails without the change.

By taking part you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
