# turkey forward test

Per-region forward test of the frozen models; not a sealed confirmation.

Fit: February 2012–December 2019. Accuracy: January 2020–December 2021 against MODIS.
Satellite comparison: January 2020–December 2025. Frozen settings and existing test functions reused.

| Check | Burning days | Hotspots |
|---|---|---|
| Cell-month error (WAPE) | 73.4% | 77.2% |
| Simple conversion cell-month error | 89.0% | 81.5% |
| Raw VIIRS cell-month error | 177.3% | 254.4% |
| Region-month error (WAPE) | 20.2% | 22.7% |
| Simple conversion region-month error | 34.9% | 29.3% |
| 80% interval coverage | 82.5% | 81.6% |
| Total bias | +11.7% | +7.0% |
| Satellite interval agreement | 90.5% | 87.3% |
| All existing checks | FAIL | PASS |

## Interpretation limits

- This was a development region: its 2012–2019 data helped choose the model. Its 2020–2021 MODIS was not used, so this is a forward test in time, not a test on an unseen region.
- The analysis area is the whole FIRMS country file, not a rectangle.
- Accuracy is scored only in cells seen during the training period, as in the existing runner.
- MODIS after 2021 is not treated as reliable ground truth (Aqua orbital drift from 2022). The 2022–2025 comparison checks agreement between VIIRS satellites, not true fire counts.
- Months excluded from the accuracy window by the existing outage rule: ['2021-12'].
- No model settings were tuned and no repository model code was changed.
