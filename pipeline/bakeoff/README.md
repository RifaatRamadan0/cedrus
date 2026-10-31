# pipeline/bakeoff — model A vs model B

Runs the bake-off exactly as pre-registered in [docs/BAKEOFF_PLAN.md](../../docs/BAKEOFF_PLAN.md).
The results go to [docs/BAKEOFF_RESULTS.md](../../docs/BAKEOFF_RESULTS.md), which is generated. Don't edit it by hand.

```bash
python -m pipeline.bakeoff.run          # from the repo root
python -m pipeline.bakeoff.test_nb      # NB2 / Poisson maximum likelihood recovers known parameters
python -m pipeline.bakeoff.test_crps    # summed CRPS matches the closed forms
```

You need `pandas`, `numpy` and `scipy` (requirements.txt). The models are fitted with our own maximum
likelihood code (`nb.py`), so statsmodels isn't needed.

It reads `data/raw/<region>/{modis,viirs-snpp}_<year>_<Country>.csv` for 2012–2019 only, for every
development region in `pipeline/regions.py` whose files are all listed in its `manifest.json`. Regions
with missing files are left out, and the results file names them. Sealed regions are never opened.
`--regions portugal lebanon` runs a subset for development. That output is not the bake-off.

| File | What it does |
|---|---|
| `data.py` | Filters, the cell × month × day/night rows, the outage rule |
| `units.py` | Suomi NPP passes, fire units, Aqua matching, chance control (cKDTree) |
| `nb.py` | NB2 and Poisson maximum likelihood with analytic gradients |
| `models.py` | Candidate A (Poisson–gamma ratio) and candidate B (g(FRP) + NB2 + empirical Bayes) |
| `scores.py` | Exact CRPS by summation, 10th/90th percentiles, predictive mean |
| `validate.py` | Inner and outer leave-one-year-out, summary scores, bootstrap, decision rule |
| `report.py` | Writes docs/BAKEOFF_RESULTS.md |
| `run.py` | The entry point |

Intermediate files go to `data/processed/bakeoff/` (ignored by git):
- per-region caches `<region>/pixels.pkl`, `rows.pkl` and `units.pkl`, rebuilt when a raw file's SHA-256 changes;
- per-row scores, `loyo_rows.pkl` and `forward_rows.pkl`;
- `results.json`;
- `frozen_<winner>.json`: every parameter of the chosen model, refit on all of 2012–2019.
