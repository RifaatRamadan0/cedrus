# southern_france forward test

Per-region forward test of the frozen models; not a sealed confirmation.

Fit: February 2012–December 2019. Accuracy: January 2020–December 2021 against MODIS.
Satellite comparison: January 2020–December 2025. Frozen settings and existing test functions reused.

| Check | Burning days | Hotspots |
|---|---|---|
| Cell-month error (WAPE) | 105.0% | 104.1% |
| Simple conversion cell-month error | 121.8% | 113.2% |
| Raw VIIRS cell-month error | 182.5% | 249.3% |
| Region-month error (WAPE) | 29.6% | 31.1% |
| Simple conversion region-month error | 56.6% | 49.8% |
| 80% interval coverage | 83.1% | 82.8% |
| Total bias | -4.6% | -8.1% |
| Satellite interval agreement | 100.0% | 95.7% |
| All existing checks | PASS | PASS |

## Interpretation limits

- This region was not used for development: it was a sealed exam region, opened once for its confirmation after the model was frozen. This rerun uses the same frozen models on its own 2012–2019 data.
- The analysis box is a rectangle, not the country boundary.
- Accuracy is scored only in cells seen during the training period, as in the existing runner.
- MODIS after 2021 is not treated as reliable ground truth (Aqua orbital drift from 2022). The 2022–2025 comparison checks agreement between VIIRS satellites, not true fire counts.
- Months excluded from the accuracy window by the existing outage rule: [].
- No model settings were tuned and no repository model code was changed.
