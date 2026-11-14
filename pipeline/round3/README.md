# pipeline/round3 — D-a (burning days) on the round-3 sealed regions, once

Runs the round-3 sealed exam of [docs/TOURNAMENT_PLAN.md](../../docs/TOURNAMENT_PLAN.md) (pre-registered at commit
fa2c956), with the entrant set by the ruling added at its end: D-a, the tournament's C3 refitted in burning days, frozen
in `data/processed/tournament/frozen_round3.json` (see [docs/TOURNAMENT_RESULTS.md](../../docs/TOURNAMENT_RESULTS.md),
Freeze). The tests and pass rules are round 2's ([docs/ROUND2_PLAN.md](../../docs/ROUND2_PLAN.md)), applied in burning
days, with F0 and F1 in burning days too. The confirmation writes docs/ROUND3_CONFIRMATION.md, which is generated.
Don't edit it by hand.

```bash
python -m pipeline.round3.test_round3                # hand checks and refusals (about 20 seconds)
python -m pipeline.tournament.test_tournament        # C3, D-a's code, unchanged
python -m pipeline.round2.test_round2                # R1 (F1), s for J-S, totals(), unchanged

python -m pipeline.round3.confirm --regions central_spain southern_italy sw_australia s_california portugal
                                                     # debugging on development regions only (about 30 seconds)
python -m pipeline.round3.confirm --i-am-the-lead-running-it-once
                                                     # THE confirmation: once, by the lead, on the four sealed regions
```

`confirm` refuses to start unless frozen_round3.json has the SHA-256 recorded at the freeze
(f3130df9…4357a2). It refuses sealed regions unless it gets the flag, and then it runs exactly the four sealed regions
(northern_algeria, southern_france, south_australia, n_california). Both refusals come before any file is opened.
With the flag, it also refuses to start unless every MODIS and Suomi NPP file for 2012–2025 and every NOAA-20 file for
2018–2025 is in their manifests. A debugging run writes `data/processed/round3/confirm_dev_report.md`, never docs/.

It reuses round 2's guard, rows, outage rule, R1 (F1), s for J-S, totals' variance, the swap counting rule and the
Test 1 verdict (`round2/data.py`, `round2/models.py`, `round2/validate.py`, `round2/confirm.py`); the tournament's
class counts, burning-day unit, C3 and J-S view (`tournament/data.py`, `tournament/candidates.py`); and the bake-off's
filters, exact CRPS and weights. All are unchanged.

| File | What it does |
|---|---|
| `data.py` | The frozen file and its SHA-256 check, the completeness check, detections 2012–2025 with FRP and scan, the one-region table in burning days |
| `model.py` | D-a refitted with the frozen a, its predictive parts (mean, variance, k for the s bootstrap, the f0 part), J-S |
| `confirm.py` | The entry point: Test 1, Test 2, seam, drift, swap metrics, the f0 list |
| `report.py` | Writes docs/ROUND3_CONFIRMATION.md (or the debugging report) |
| `test_round3.py` | Hand checks on toy tables, the refusals, and rows against the tournament's table |

Intermediate files go to `data/processed/round3/` (ignored by git):
- `<region>/pixels.pkl`, rebuilt when a raw file's SHA-256 changes;
- `confirm_*` / `confirm_dev_*` row and region-month tables and `*_results.json`;
- `confirm_runs.jsonl`: every invocation, so a re-run can't go unseen.
