# pipeline/confirm — the frozen model on the sealed regions

This runs [docs/CONFIRMATION_PLAN.md](../../docs/CONFIRMATION_PLAN.md), **once**, on Morocco, Tunisia, Central Chile
and the Western Cape. The results go to [docs/CONFIRMATION_RESULTS.md](../../docs/CONFIRMATION_RESULTS.md), which is
generated. Don't edit it by hand.

```bash
python -m pipeline.confirm.run                              # the confirmation (the four "confirm" regions)
python -m pipeline.confirm.run --regions portugal lebanon \
    --report data/processed/confirm/dev_report.md           # development regions only, for debugging
```

Model A is the bake-off's own code (`pipeline/bakeoff/models.py`, unchanged since commit f0823f9), with a = 30. It is
refitted on each region's own 2012–2019 rows. Nothing is tuned. The report records the git commit, whether the
bake-off code differs from f0823f9, and a fingerprint of each model file.

A region is used only when its `manifest.json` lists every file from 2012 to 2025: MODIS, Suomi NPP and NOAA-20
(NOAA-20 from 2018). Raw folders are named after the FIRMS country, so they are `data/raw/chile` and
`data/raw/south_africa`.

Every invocation is appended to `data/processed/confirm/runs.jsonl`, and the report lists the confirmation runs, so
a re-run is visible.

| File | What it does |
|---|---|
| `data.py` | 2012–2025 detections (bake-off filters), rows, outage days |
| `tests.py` | Test 1, Test 2, seam check, drift check for one region |
| `report.py` | Writes docs/CONFIRMATION_RESULTS.md |
| `run.py` | The entry point |
