# central_chile forward test

Per-region forward test of the frozen models; not a sealed confirmation.

Fit: February 2012–December 2019. Accuracy: January 2020–December 2021 against MODIS.
Satellite comparison: January 2020–December 2025. Frozen settings and existing test functions reused.

| Check | Burning days | Hotspots |
|---|---|---|
| Cell-month error (WAPE) | 52.7% | 55.6% |
| Simple conversion cell-month error | 62.9% | 54.8% |
| Raw VIIRS cell-month error | 144.1% | 260.4% |
| Region-month error (WAPE) | 14.8% | 17.7% |
| Simple conversion region-month error | 19.9% | 13.4% |
| 80% interval coverage | 86.9% | 85.9% |
| Total bias | +6.8% | +8.4% |
| Satellite interval agreement | 94.1% | 91.3% |
| All existing checks | PASS | FAIL |

## Interpretation limits

- This was a development region: its 2012–2019 data helped choose the model. Its 2020–2021 MODIS was not used, so this is a forward test in time, not a test on an unseen region.
- The analysis box is a rectangle, not the country boundary.
- Accuracy is scored only in cells seen during the training period, as in the existing runner.
- MODIS after 2021 is not treated as reliable ground truth (Aqua orbital drift from 2022). The 2022–2025 comparison checks agreement between VIIRS satellites, not true fire counts.
- Months excluded from the accuracy window by the existing outage rule: ['2021-11'].
- No model settings were tuned and no repository model code was changed.
