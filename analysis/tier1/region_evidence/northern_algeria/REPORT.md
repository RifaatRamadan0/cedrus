# northern_algeria forward test

Per-region forward test of the frozen models; not a sealed confirmation.

Fit: February 2012–December 2019. Accuracy: January 2020–December 2021 against MODIS.
Satellite comparison: January 2020–December 2025. Frozen settings and existing test functions reused.

| Check | Burning days | Hotspots |
|---|---|---|
| Cell-month error (WAPE) | 49.5% | 49.8% |
| Simple conversion cell-month error | 64.6% | 53.9% |
| Raw VIIRS cell-month error | 134.3% | 263.7% |
| Region-month error (WAPE) | 10.6% | 8.2% |
| Simple conversion region-month error | 33.0% | 16.2% |
| 80% interval coverage | 82.6% | 82.9% |
| Total bias | +2.6% | +1.0% |
| Satellite interval agreement | 90.6% | 87.7% |
| All existing checks | PASS | PASS |

## Interpretation limits

- This region was not used for development: it was a sealed exam region, opened once for its confirmation after the model was frozen. This rerun uses the same frozen models on its own 2012–2019 data.
- The analysis box is a rectangle, not the country boundary.
- Accuracy is scored only in cells seen during the training period, as in the existing runner.
- MODIS after 2021 is not treated as reliable ground truth (Aqua orbital drift from 2022). The 2022–2025 comparison checks agreement between VIIRS satellites, not true fire counts.
- Months excluded from the accuracy window by the existing outage rule: [].
- No model settings were tuned and no repository model code was changed.
