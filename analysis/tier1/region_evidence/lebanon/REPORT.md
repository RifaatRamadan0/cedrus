# lebanon forward test

Per-region forward test of the frozen models; not a sealed confirmation.

Fit: February 2012–December 2019. Accuracy: January 2020–December 2021 against MODIS.
Satellite comparison: January 2020–December 2025. Frozen settings and existing test functions reused.

| Check | Burning days | Hotspots |
|---|---|---|
| Cell-month error (WAPE) | 78.4% | 82.3% |
| Simple conversion cell-month error | 102.4% | 99.2% |
| Raw VIIRS cell-month error | 375.1% | 471.3% |
| Region-month error (WAPE) | 28.3% | 34.7% |
| Simple conversion region-month error | 58.0% | 57.7% |
| 80% interval coverage | 89.5% | 89.5% |
| Total bias | -16.0% | -21.4% |
| Satellite interval agreement | 100.0% | 100.0% |
| All existing checks | FAIL | FAIL |

## Interpretation limits

- This was a development region: its 2012–2019 data helped choose the model. Its 2020–2021 MODIS was not used, so this is a forward test in time, not a test on an unseen region.
- The analysis box is a rectangle, not the country boundary.
- Accuracy is scored only in cells seen during the training period, as in the existing runner.
- MODIS after 2021 is not treated as reliable ground truth (Aqua orbital drift from 2022). The 2022–2025 comparison checks agreement between VIIRS satellites, not true fire counts.
- Months excluded from the accuracy window by the existing outage rule: [].
- No model settings were tuned and no repository model code was changed.
