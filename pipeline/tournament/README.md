# pipeline/tournament — C0–C8, the burning-day unit, headroom

Runs [docs/TOURNAMENT_PLAN.md](../../docs/TOURNAMENT_PLAN.md), pre-registered at commit fa2c956 before any of this
code existed. It writes [docs/TOURNAMENT_RESULTS.md](../../docs/TOURNAMENT_RESULTS.md), which is generated. Don't edit
it by hand.

```bash
python -m pipeline.tournament.run                # the tournament, 17 development regions, both units
python -m pipeline.tournament.test_tournament    # hand checks of C3-C8, the floor, the J-S view, no fit on 2020+
python -m pipeline.round2.test_round2            # C0 / C1 / C2 are round 2's A2 / R1 / Rm, unchanged
python -m pipeline.bakeoff.test_crps             # the exact CRPS every score uses
```

The tournament reads only development regions (role "dev" in `pipeline/regions.py`), 2012–2021 files, through
`pipeline.round2.data.guard`, which refuses sealed regions. Every fit refuses rows after 2019-12. The 2020–2021 rows
are only scored, in the swap-stability metric (no MODIS).

It reuses round 2's rows, guard, outage rule, R1 / Rm / A2, s for J-S, the moment-matched negative binomial and the
dispersion fit (`round2/data.py`, `round2/models.py`), and the bake-off's filters, A, exact CRPS and weights
(`bakeoff/data.py`, `bakeoff/models.py`, `bakeoff/scores.py`, `bakeoff/validate.py`), all unchanged.

| File | What it does |
|---|---|
| `data.py` | Detections with FRP and scan, round 2's rows plus class counts and the burning-day unit, the J-S view |
| `candidates.py` | C0–C8: fit on a training mask, forecast as (kind, a, b), nested inner tuning |
| `nbreg.py` | C6's negative-binomial regression (maximum likelihood, analytic gradient, expected information) |
| `validate.py` | One fold of one candidate, the scores, swap stability, the Poisson floor, the selection rules |
| `run.py` | The entry point: the table, the jobs (cached), the results, champion.json |
| `report.py` | Writes docs/TOURNAMENT_RESULTS.md |
| `test_tournament.py` | Hand checks on toy tables |

Intermediate files go to `data/processed/tournament/` (ignored by git):
- `<region>/pixels.pkl`, rebuilt when a raw file's SHA-256 changes; `table.pkl`, the row table of all 17 regions;
- `cache/<unit>_<candidate>_<fold>.pkl`, one per fitted fold, keyed by a hash of the code;
- `rows_{px,bd}_{loyo,forward}.pkl` (per-row scores), `swap_{px,bd}.pkl` (region-month totals), `results.json`;
- `champion.json`: the champion and every setting needed to refit it on a new region.
