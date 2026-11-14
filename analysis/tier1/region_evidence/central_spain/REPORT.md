# central_spain forward test

Per-region forward test of the frozen models; not a sealed confirmation.

Fit: February 2012–December 2019. Accuracy: January 2020–December 2021 against MODIS.
Satellite comparison: January 2020–December 2025. Frozen settings and existing test functions reused.

| Check | Burning days | Hotspots |
|---|---|---|
| Cell-month error (WAPE) | 92.1% | 94.2% |
| Simple conversion cell-month error | 111.6% | 98.3% |
| Raw VIIRS cell-month error | 134.1% | 234.7% |
| Region-month error (WAPE) | 26.1% | 28.0% |
| Simple conversion region-month error | 44.2% | 33.8% |
| 80% interval coverage | 75.7% | 75.6% |
| Total bias | -4.7% | -5.4% |
| Satellite interval agreement | 89.9% | 100.0% |
| All existing checks | PASS | PASS |

## Interpretation limits

- This was a development region: its 2012–2019 data helped choose the model. Its 2020–2021 MODIS was not used, so this is a forward test in time, not a test on an unseen region.
- The analysis box is a rectangle, not the country boundary.
- Accuracy is scored only in cells seen during the training period, as in the existing runner.
- MODIS after 2021 is not treated as reliable ground truth (Aqua orbital drift from 2022). The 2022–2025 comparison checks agreement between VIIRS satellites, not true fire counts.
- Months excluded from the accuracy window by the existing outage rule: [].
- No model settings were tuned and no repository model code was changed.
