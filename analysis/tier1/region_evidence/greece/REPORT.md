# greece forward test

Per-region forward test of the frozen models; not a sealed confirmation.

Fit: February 2012–December 2019. Accuracy: January 2020–December 2021 against MODIS.
Satellite comparison: January 2020–December 2025. Frozen settings and existing test functions reused.

| Check | Burning days | Hotspots |
|---|---|---|
| Cell-month error (WAPE) | 102.1% | 101.0% |
| Simple conversion cell-month error | 115.3% | 108.3% |
| Raw VIIRS cell-month error | 227.5% | 294.3% |
| Region-month error (WAPE) | 19.4% | 16.8% |
| Simple conversion region-month error | 35.5% | 27.0% |
| 80% interval coverage | 84.2% | 84.0% |
| Total bias | +8.2% | +5.0% |
| Satellite interval agreement | 90.3% | 92.3% |
| All existing checks | PASS | PASS |

## Interpretation limits

- This was a development region: its 2012–2019 data helped choose the model. Its 2020–2021 MODIS was not used, so this is a forward test in time, not a test on an unseen region.
- The analysis area is the whole FIRMS country file, not a rectangle.
- Accuracy is scored only in cells seen during the training period, as in the existing runner.
- MODIS after 2021 is not treated as reliable ground truth (Aqua orbital drift from 2022). The 2022–2025 comparison checks agreement between VIIRS satellites, not true fire counts.
- Months excluded from the accuracy window by the existing outage rule: ['2021-08'].
- No model settings were tuned and no repository model code was changed.
