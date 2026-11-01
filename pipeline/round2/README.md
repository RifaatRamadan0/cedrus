# pipeline/round2 — R1 / Rm / A2 and the NOAA-20 method, then the confirmation

Runs [docs/ROUND2_PLAN.md](../../docs/ROUND2_PLAN.md), pre-registered at commit e7763f7 before any of this code
existed. The selection writes [docs/ROUND2_SELECTION.md](../../docs/ROUND2_SELECTION.md) and the confirmation writes
docs/ROUND2_CONFIRMATION.md. Both are generated. Don't edit them by hand.

```bash
python -m pipeline.round2.select                     # selection, development regions only (about 2 minutes)
python -m pipeline.round2.test_round2                # hand checks: R1/Rm means, A2 sums, no fit on 2020+, NB, totals
python -m pipeline.bakeoff.test_nb                   # the bake-off's NB2 / Poisson tests
python -m pipeline.bakeoff.test_crps                 # the bake-off's CRPS tests (scores.py is reused)

python -m pipeline.round2.confirm --regions portugal lebanon     # debugging on development regions only
python -m pipeline.round2.confirm --i-am-the-lead-running-it-once  # THE confirmation: once, by the lead,
                                                                   # after the frozen selection is reviewed and committed
```

The selection reads only development regions (role "dev" in `pipeline/regions.py`), 2012–2021 files, through
`data.guard`, which refuses sealed regions. Every fit refuses rows after 2019-12. The 2020–2021 rows are only scored,
in the NOAA-20 swap. `confirm` refuses sealed regions unless it gets the flag, and then it runs exactly the four
sealed regions. With the flag, it also refuses to start unless every 2012–2025 file is in their manifests.
A debugging run writes `data/processed/round2/confirm_dev_report.md`, never docs/.

It reuses the bake-off's filters (`bakeoff/data._read`), outage rule (`bakeoff/data.outages`), A (`bakeoff/models.fit_A`,
`predict_A`), exact CRPS (`bakeoff/scores.py`) and weights (`bakeoff/validate.py`), all unchanged.

| File | What it does |
|---|---|
| `data.py` | The sealed-region guard, detections 2012–2025 (bake-off filters, box clip), rows, outage days |
| `models.py` | R1 / Rm (ratio, b, α by maximum likelihood, year-block bootstrap of r), A2, s for J-S, totals' variance |
| `validate.py` | Folds, scores, the 2% rule, the swap table and the J-S / J-M rule |
| `select.py` | The selection entry point; writes `frozen.json` |
| `confirm.py` | The confirmation entry point |
| `report.py` | Writes both generated documents |
| `test_round2.py` | Hand checks on a toy table |

Intermediate files go to `data/processed/round2/` (ignored by git):
- `<region>/pixels_<last year>.pkl`, rebuilt when a raw file's SHA-256 changes;
- `loyo_rows.pkl`, `forward_rows.pkl`, `swap_js.pkl` and `swap_jm.pkl`, plus `selection.json`;
- `frozen.json`: the chosen pair and every setting needed to refit it on a new region;
- `confirm_*` files and `confirm_runs.jsonl`: every confirmation invocation, so a re-run can't go unseen.
