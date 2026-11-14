# sw_australia forward test

Per-region forward test of the frozen models; not a sealed confirmation.

Fit: February 2012–December 2019. Accuracy: January 2020–December 2021 against MODIS.
Satellite comparison: January 2020–December 2025. Frozen settings and existing test functions reused.

| Check | Burning days | Hotspots |
|---|---|---|
| Cell-month error (WAPE) | 55.3% | 63.9% |
| Simple conversion cell-month error | 60.9% | 66.3% |
| Raw VIIRS cell-month error | 206.9% | 458.5% |
| Region-month error (WAPE) | 12.8% | 20.4% |
| Simple conversion region-month error | 17.2% | 19.4% |
| 80% interval coverage | 86.5% | 84.4% |
| Total bias | +10.8% | +20.1% |
| Satellite interval agreement | 95.7% | 82.9% |
| All existing checks | FAIL | FAIL |

## Interpretation limits

- This was a development region: its 2012–2019 data helped choose the model. Its 2020–2021 MODIS was not used, so this is a forward test in time, not a test on an unseen region.
- The analysis box is a rectangle, not the country boundary.
- Accuracy is scored only in cells seen during the training period, as in the existing runner.
- MODIS after 2021 is not treated as reliable ground truth (Aqua orbital drift from 2022). The 2022–2025 comparison checks agreement between VIIRS satellites, not true fire counts.
- Months excluded from the accuracy window by the existing outage rule: ['2020-08', '2020-10', '2021-09', '2021-11', '2021-12'].
- No model settings were tuned and no repository model code was changed.
