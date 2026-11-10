# syria forward test

Per-region forward test of the frozen models; not a sealed confirmation.

Fit: February 2012–December 2019. Accuracy: January 2020–December 2021 against MODIS.
Satellite comparison: January 2020–December 2025. Frozen settings and existing test functions reused.

| Check | Burning days | Hotspots |
|---|---|---|
| Cell-month error (WAPE) | 68.9% | 76.6% |
| Simple conversion cell-month error | 80.3% | 77.7% |
| Raw VIIRS cell-month error | 259.3% | 383.9% |
| Region-month error (WAPE) | 19.5% | 27.5% |
| Simple conversion region-month error | 27.0% | 24.4% |
| 80% interval coverage | 84.1% | 82.3% |
| Total bias | +7.3% | +5.7% |
| Satellite interval agreement | 92.1% | 80.6% |
| All existing checks | PASS | FAIL |

## Interpretation limits

- This was a development region: its 2012–2019 data helped choose the model. Its 2020–2021 MODIS was not used, so this is a forward test in time, not a test on an unseen region.
- The analysis box is a rectangle, not the country boundary.
- Accuracy is scored only in cells seen during the training period, as in the existing runner.
- MODIS after 2021 is not treated as reliable ground truth (Aqua orbital drift from 2022). The 2022–2025 comparison checks agreement between VIIRS satellites, not true fire counts.
- Months excluded from the accuracy window by the existing outage rule: ['2020-08', '2020-09'].
- No model settings were tuned and no repository model code was changed.
