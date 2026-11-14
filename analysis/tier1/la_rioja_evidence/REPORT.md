# La Rioja model diagnostic

Exploratory test; not a new sealed confirmation.

Fit: February 2012–December 2019. Accuracy: January 2020–December 2021.
Satellite comparison: January 2020–December 2025. Frozen settings and existing test functions reused.

| Check | Burning days | Hotspots |
|---|---|---|
| Cell-month error (WAPE) | 59.9% | 62.8% |
| Simple conversion cell-month error | 69.1% | 61.9% |
| Raw VIIRS cell-month error | 132.9% | 259.9% |
| Region-month error (WAPE) | 11.0% | 13.4% |
| Simple conversion region-month error | 19.9% | 13.7% |
| 80% interval coverage | 81.2% | 79.6% |
| Total bias | -4.4% | -4.8% |
| Satellite interval agreement | 93.1% | 93.1% |
| All existing checks | PASS | PASS |

## Interpretation limits

- The box includes parts of neighbouring provinces; it is not the exact provincial boundary.
- Accuracy is scored only in cells seen during the training period, as in the existing runner. New cells are not validated by that score.
- Day and night are separate burning-day observations. Values do not measure burned area or distinct incidents.
- MODIS after 2021 is not treated as reliable ground truth. The 2022–2025 comparison checks agreement between VIIRS satellites, not true fire counts.
- Satellite agreement means overlapping uncertainty intervals, not equal point estimates.
- Existing outage rule excludes these accuracy-window months: []. Sensitivity results are in results.json where applicable.
- Frozen checksums, dependencies, source hashes, exclusions, yearly totals, and test verdicts are recorded in results.json.
- No model settings were tuned, and no application or repository source files were changed.

## Pass rules used

All five original checks passed for each unit:

1. Cell-month WAPE no more than 1 percentage point worse than the simple conversion, and lower than raw VIIRS.
2. The nominal 80% interval contains MODIS in 70–90% of active cell × month × day/night rows.
3. Total estimate within 10% of observed MODIS.
4. Region-month WAPE no more than 1 percentage point worse than the simple conversion.
5. At least 80% of eligible satellite-month uncertainty intervals overlap (each estimate at least 10).

## Findings that qualify the pass

- Burning days improve cell-month WAPE from 69.1% to 59.9%, and region-month WAPE from 19.9% to 11.0%.
- Hotspot cell-month WAPE is slightly worse than the simple conversion: 62.8% versus 61.9%. It passes because the predefined rule permits a 1 percentage point margin. A pass does not mean superiority on every measure.
- Local cell-month errors near 60% are substantial. Regional totals are more dependable than fine local estimates in this test.
- In the burning-day test, all 159 active rows where MODIS detected fire but Suomi NPP detected none fall outside the model interval. Overall active-row coverage is nevertheless 81.2%; the aggregate coverage conceals this weak subgroup.
- Annual burning-day totals are underestimated in both years: 1,703 versus 1,776 in 2020, and 1,469 versus 1,544 in 2021. Both observed totals sit just above the runner's approximate annual 80% intervals. The five pass rules do not test annual interval coverage.
- All 24 accuracy-test months and all 72 satellite-comparison months were retained; the existing outage rule excluded none.
- Across 2020–2025, the existing test omits detections in cells first seen after fitting: 14 Suomi NPP, 9 NOAA-20, and 1 Terra detection. These counts are reported separately from scored data.

This result supports cautious inclusion of the La Rioja area, especially for regional burning-day summaries. It does not independently establish accuracy during 2022–2025 or in other Argentine regions.
