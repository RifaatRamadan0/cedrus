"""Region definitions shared by every pipeline step.

A region is one FIRMS country file, optionally clipped to a box (lon_min, lat_min, lon_max, lat_max).
Grid: global 0.25 degree cells, ix = floor(lon / 0.25), iy = floor(lat / 0.25).
"""
import numpy as np

CELL = 0.25

SHARED_NOTES = [
    "Counts all fires FIRMS detects, from any cause, including agricultural burning and conflict. "
    "Static heat sources (type 2) are excluded. Monthly completeness is unknown; known FIRMS data gaps are listed in the docs.",
    "Only type 0 (presumed vegetation fire) is eligible; volcano and offshore detections are also excluded. Fire causes are not classified.",
    "Accuracy is checked against MODIS only up to 2021. From 2022 the MODIS satellites drift in orbit, so 2022–2025 values "
    "are checked only by agreement between two VIIRS satellites, not against an independent record.",
    "Where a region's record includes 2026 (January–July: Portugal, Lebanon, Syria and La Rioja), it comes from FIRMS "
    "standard data, assigned to each country with Natural Earth outlines; in a test "
    "this matched FIRMS's own 2025 country files exactly. Lebanon uses the outline as it was on 30 August 2021, which "
    "matched every FIRMS Lebanon assignment in 2000–2025; the current outline differs by about 1 km on the southern border. "
    "Later months are added when FIRMS releases standard data; near-real-time data is not used.",
    # Measured 13 Nov 2026 (docs/DATA_CONTRACT.md, p10/p90; docs/TIER1_IMPLEMENTATION_STATUS.md). Wording only.
    "The 80% ranges are too narrow: in a test on 2020–2021 they held the observed MODIS value about half the time. "
    "Read the trust check and the chance figure as optimistic.",
]

# Per-region forward tests (fit 2012-2019, score 2020-2021): analysis/tier1/region_evidence/<region>/REPORT.md
FORWARD = "Forward test against MODIS, 2020–2021 (fitted on 2012–2019): "

# Regions added on 14 Nov 2026 with only the 2012-2025 files on disk (no MODIS before 2012 yet, no 2026).
START = ("Record runs {} to {}: MODIS files before 2012 are not yet on disk for this region, so it has no 2000–2011 "
         "history and no bridged months, and no 2026 data has been added.")
# The same regions once their 2000-2011 MODIS files were downloaded (14 Nov 2026): the full record, bridged months as
# for Portugal.
START_FULL = ("Record runs {} to {}, as for Portugal: Terra alone (bridged) until June 2002, observed MODIS to "
              "2021, estimates from VIIRS from 2022. The 2000–2011 MODIS files were downloaded on 14 Nov 2026. No 2026 "
              "data has been added.")
ROUND2 = ("Passed the round-2 sealed exam (hotspots, model A2; CONFIRMED with central Spain, southern Italy, southwest "
          "Australia and southern California pooled: docs/ROUND2_CONFIRMATION.md). ")
ROUND3 = ("Passed the round-3 sealed exam (burning days, model D-a; CONFIRMED with northern Algeria, southern France, "
          "South Australia and northern California pooled: docs/ROUND3_CONFIRMATION.md). ")
DEV_NOTE = ("This was a development region (its 2012–2019 data helped choose the models), so the forward test is a test "
            "forward in time, not on an unseen region. It was also a round-1 exam region, where the earlier model failed.")
DEV_AFTER = ("After its exam this region became development data for the burning-day tournament, so its burning-day "
             "forward test is a test forward in time, not on an unseen region.")
BOX_COUNTRY = ("The analysis box is a rectangle, not a boundary; it counts only FIRMS's {} file, so fires across a "
               "border inside the box are not shown.")
BOX_AREA = ("The analysis box is a rectangle downloaded from the FIRMS area service: it counts every fire in it, "
            "whatever the country.")

REGIONS = {
    # role: "dev" = bake-off development, "product" = shown in the app, "sealed" = never opened before freeze,
    # "confirm" = formerly sealed, opened once for docs/CONFIRMATION_PLAN.md after the model was frozen
    "portugal": {"country": "Portugal", "box": (-9.6, 36.9, -6.1, 42.2), "roles": {"dev", "product"},
                 "notes": [FORWARD + "met every pass rule in both units, with regional monthly error 15.3% against 30.8% "
                           "for a simple conversion and the total 3.8–4.3% too high. This provides evidence for "
                           "regional-level performance in 2020–2021. It does not show accuracy after 2021 or for single "
                           "grid cells, where errors are 78–80%."]},
    "lebanon": {"country": "Lebanon", "box": (35.10, 33.05, 36.65, 34.70), "roles": {"dev", "product"},
                "notes": [FORWARD + "failed the check that the total is within 10%, underestimating by 16% in burning days "
                          "and 21% in hotspots. It still beat a simple conversion by a wide margin (regional monthly error "
                          "28.3% against 58.0%). Lebanon has few fires (245 MODIS burning days in the two years), so one "
                          "large fire moves the total; grid-cell errors are 78–82%.",
                          "11 of Lebanon's 28 grid cells lie on the border and also cover land in Syria; they hold 23% of "
                          "Lebanon's estimated values. Each cell counts only Lebanon's records; Syria's fires in the same "
                          "cell are in the Syria view.",
                          "One 2026 Suomi NPP detection (24 June, 0.1 km inside the eastern border) fell in a grid cell "
                          "with no earlier Lebanon fires and is left out, so the 2000–2025 grid and its values stay "
                          "exactly as published."]},
    # Cyprus and Jordan were removed from the app on 10 Nov 2026 (no "product" role): their forward tests had too few
    # fires to measure (139 and 81 MODIS burning days in 2020-2021) and grid-cell errors of about 100% and 163%.
    # Results and rule: analysis/tier1/region_evidence/README.md.
    "cyprus": {"country": "Cyprus", "box": (32.1, 34.4, 34.8, 35.8), "roles": {"dev"}},
    "jordan": {"country": "Jordan", "box": (34.8, 29.0, 39.5, 33.5), "roles": {"dev"}},
    "israel": {"country": "Israel", "box": (34.2, 29.4, 35.95, 33.4), "roles": {"dev"}},
    "palestine": {"country": "Palestine", "box": (34.1, 31.1, 35.7, 32.7), "roles": {"dev"}},
    "greece": {"country": "Greece", "box": None, "export_box": (19.5, 34.75, 28.5, 42.0), "roles": {"dev", "product"},
               "notes": ["This is FIRMS's whole Greece country file, islands included; the analysis box encloses every "
                         "detection in it. Files for 2000–2011 and 2022–2025 were downloaded on 14 Nov 2026; no 2026 data "
                         "has been added, so the record ends in December 2025.",
                         FORWARD + "every check passed in both units, with regional monthly error 19.4% in burning days "
                         "against 35.5% for a simple conversion and the total 8.2% too high; 2021 was overestimated (674 "
                         "predicted against 554 observed burning days). August 2021, the month of the Evia and Attica "
                         "fires, was left out of the test by the sensor-outage rule (one Suomi NPP day with no data).",
                         "Greece's single-square (grid-cell) error of 101–102% is above the 100% limit that removed "
                         "Jordan and Cyprus from the app, and it comes from that rule: it is measured on the test months "
                         "without August 2021. Scored with August 2021 included "
                         "(a sensitivity check, not the test's rule), the single-square error is 64–66% and the total "
                         "2–4% too low. Read single squares here with care; the regional monthly figures are the "
                         "stronger result.",
                         "This was a development region (its 2012–2019 data helped choose the models), so the forward test "
                         "is a test forward in time, not on an unseen region.",
                         "Cells on Greece's borders also cover land in neighbouring countries but count only Greece's "
                         "records; fires in Turkey are in the Turkey view, and the boxes of the two overlap."]},
    "syria": {"country": "Syria", "box": (35.5, 32.2, 42.5, 37.5), "roles": {"dev", "product"},
              "notes": [FORWARD + "burning days passed every check, with regional monthly error 19.5% against 27.0% for a "
                        "simple conversion. Hotspots failed one check: regional monthly error 27.5%, slightly worse than the "
                        "simple conversion's 24.4%. 2021 was overestimated (662 predicted against 490 observed burning days). "
                        "Local grid-cell errors are 69–77%. August and September 2020 were left out of the test by the "
                        "sensor-outage rule.",
                        "Cells on Syria's borders also cover land in neighbouring countries, but count only Syria's records. "
                        "11 of them are shared with Lebanon, whose fires are in the Lebanon view; fires in Turkey are in the "
                        "Turkey view (added 14 Nov 2026); fires in Iraq and Jordan are not shown anywhere."]},
    "la_rioja": {"country": "Argentina", "name": "La Rioja area, Argentina",
                 "box": (-69.7, -32.8, -65.4, -27.7), "roles": {"product"},
                 "notes": ["Regional monthly summaries were tested against MODIS in 2020–2021. Local grid-cell errors remain substantial, around 60%. This region is outside the climates used in the earlier Mediterranean validation.",
                           "Annual totals in the 2020-2021 test were above the 80% range.",
                           "This is a rectangular area including neighboring provincial land, not the exact La Rioja province.",
                           "One 2026 NOAA-20 detection fell in a grid cell with no earlier fires and is left out, so the "
                           "2000–2025 grid and its values stay exactly as published."]},
    "turkey": {"country": "Turkey", "box": None, "export_box": (25.5, 35.75, 45.0, 42.25), "roles": {"dev", "product"},
               "notes": ["This is FIRMS's whole Turkey country file; the analysis box encloses every detection in it. "
                         "Files for 2000–2011, NOAA-20 2020 and 2022–2025 were downloaded on 14 Nov 2026; no 2026 data "
                         "has been added, so the record ends in December 2025.",
                         FORWARD + "burning days failed the check that the total is within 10%: 11.7% too high, because "
                         "2020 was overestimated (9,342 predicted against 7,572 observed burning days; 2021 was close, "
                         "8,022 against 7,974). It still beat a simple conversion (regional monthly error 20.2% against "
                         "34.9%). Hotspots passed every check (regional monthly error 22.7% against 29.3%, total 7.0% too "
                         "high). Grid-cell errors are 73–77%. December 2021 was left out of the test by the sensor-outage "
                         "rule.",
                         "This was a development region (its 2012–2019 data helped choose the models), so the forward test "
                         "is a test forward in time, not on an unseen region.",
                         "Cells on Turkey's borders also cover land in neighbouring countries but count only Turkey's "
                         "records; fires in Syria and Greece are in their own views, and their boxes overlap Turkey's."]},
    # Round 1 confirmation regions: opened once on 1 Nov 2026 (NOT CONFIRMED) -> spent; usable as development data only.
    # Added to the app on 14 Nov 2026 (product) with the 2012-2025 files on disk; forward tests in
    # analysis/tier1/region_evidence/<region>/REPORT.md (Python 3.11.0, pandas 2.3.3, numpy 2.4.6, scipy 1.17.1).
    "morocco": {"country": "Morocco", "box": None, "export_box": (-17.25, 21.25, -1.0, 36.0),
                "roles": {"dev", "spent", "product"},
                "notes": [START_FULL.format("January 2001", "December 2025") + " It starts in January 2001 because a month counts only if MODIS has a detection in its first 3 days, and Morocco's first is on 10 December 2000.",
                          "This is FIRMS's Morocco country file, which also includes Western Sahara (detections reach "
                          "21.5° N). The analysis box encloses every detection in that file.",
                          FORWARD + "burning days passed every check, with regional monthly error 31.7% against 44.8% "
                          "for a simple conversion and the total 3.2% too low. Hotspots failed the check that the total "
                          "is within 10% (10.6% too low). Morocco has few fires (603 MODIS burning days in the two years). "
                          "Grid-cell errors are 116–125%, above the 100% limit that removed Jordan and Cyprus from the app: "
                          "single cells here are not reliable.",
                          DEV_NOTE]},
    "tunisia": {"country": "Tunisia", "box": None, "export_box": (7.5, 30.0, 11.5, 37.5),
                "roles": {"dev", "spent", "product"},
                "notes": [START_FULL.format("February 2001", "December 2025") + " FIRMS has no 2000 file for Tunisia; its first detection is on 3 February 2001.",
                          "This is FIRMS's whole Tunisia country file; the analysis box encloses every detection in it.",
                          FORWARD + "burning days passed every check, with regional monthly error 19.7% against 60.0% "
                          "for a simple conversion and the total 8.5% too low. Hotspots failed the check that the total "
                          "is within 10% (10.9% too low), while still beating the simple conversion (23.1% against 44.6%). "
                          "959 MODIS burning days in the two years; grid-cell errors are 72–73%.",
                          DEV_NOTE]},
    "central_chile": {"country": "Chile", "name": "Central Chile", "box": (-73.0, -38.5, -70.0, -32.0),
                      "roles": {"dev", "spent", "product"},
                      "notes": [START_FULL.format("November 2000", "December 2025"),
                                FORWARD + "burning days passed every check, with regional monthly error 14.8% against "
                                "19.9% for a simple conversion and the total 6.8% too high. Hotspots failed one check: "
                                "regional monthly error 17.7%, worse than the simple conversion's 13.4%. Grid-cell errors "
                                "are 53–56%. November 2021 was left out of the test by the sensor-outage rule.",
                                DEV_NOTE, BOX_COUNTRY.format("Chile")]},
    "western_cape": {"country": "South_Africa", "name": "Western Cape area, South Africa",
                     "box": (17.5, -35.0, 24.0, -31.0), "roles": {"dev", "spent", "product"},
                     "notes": [START.format("January 2012", "December 2025"),
                               FORWARD + "burning days passed every check, with regional monthly error 14.5% against "
                               "20.0% for a simple conversion and the total 8.9% too high. Hotspots failed the check that "
                               "the total is within 10% (11.3% too high), and their regional monthly error (16.9%) only "
                               "matched the simple conversion's (16.7%). Grid-cell errors are 65–68%.",
                               DEV_NOTE, BOX_AREA + " It is not the Western Cape province boundary."]},
    # Round 2 confirmation regions: opened once on 1 Nov 2026 (CONFIRMED) -> spent; usable as development data only.
    "central_spain": {"country": "Spain", "name": "Central Spain", "box": (-6.0, 38.5, -2.0, 41.0),
                      "roles": {"dev", "spent", "product"},
                      "notes": [START_FULL.format("November 2000", "December 2025"),
                                ROUND2 + "Its own figures there: cell-month error 94.2% (simple conversion 98.3%), "
                                "national-month error 28.0% (33.8%), predicted total 0.946 × observed.",
                                FORWARD + "every check passed in both units: regional monthly error 26.1% in burning days "
                                "against 44.2% for a simple conversion, total 4.7% too low. Central Spain has few fires "
                                "(1,021 MODIS burning days in the two years), and grid-cell errors are 92–94%, just under "
                                "the 100% limit: single cells here are not reliable.",
                                DEV_AFTER, BOX_COUNTRY.format("Spain")]},
    "southern_italy": {"country": "Italy", "name": "Southern Italy", "box": (12.3, 36.6, 16.7, 39.0),
                       "roles": {"dev", "spent", "product"},
                       "notes": [START_FULL.format("December 2000", "December 2025"),
                                 ROUND2 + "Its own figures there: cell-month error 49.8% (simple conversion 55.0%), "
                                 "national-month error 22.5% (25.9%), predicted total 0.873 × observed; 2021 was "
                                 "underestimated (1,950 predicted against 2,505 observed MODIS detections).",
                                 FORWARD + "every check passed in both units: regional monthly error 16.7% in burning "
                                 "days against 22.2% for a simple conversion, total 2.7% too low. Grid-cell errors are "
                                 "54%. February and August 2021 were left out of the test by the sensor-outage rule.",
                                 DEV_AFTER, BOX_COUNTRY.format("Italy")]},
    "sw_australia": {"country": "Australia_SW", "name": "Southwest Australia", "box": (114.5, -35.5, 119.0, -30.5),
                     "roles": {"dev", "spent", "product"},
                     "notes": [START.format("January 2012", "December 2025"),
                               ROUND2 + "Its own figures there: cell-month error 63.4% (simple conversion 69.2%), "
                               "national-month error 19.4% (25.7%), but the predicted total was 1.187 × observed: "
                               "overestimated in both 2020 and 2021.",
                               FORWARD + "both units failed the check that the total is within 10%: burning days "
                               "10.8% too high, hotspots 20.1% too high. Burning days still beat a simple conversion "
                               "(regional monthly error 12.8% against 17.2%); hotspots did not (20.4% against 19.4%). "
                               "Grid-cell errors are 55–64%. Five months (August and October 2020, September, November "
                               "and December 2021) were left out of the test by the sensor-outage rule.",
                               DEV_AFTER, BOX_AREA]},
    "s_california": {"country": "USA_SoCal", "name": "Southern California", "box": (-121.0, 32.5, -116.0, 35.5),
                     "roles": {"dev", "spent", "product"},
                     "notes": [START.format("January 2012", "December 2025"),
                               ROUND2 + "Its own figures there: cell-month error 36.6% (simple conversion 40.6%), "
                               "national-month error 12.9% (21.4%), predicted total 0.944 × observed.",
                               FORWARD + "every check passed in both units: regional monthly error 11.7% in burning days "
                               "against 33.6% for a simple conversion, total 4.7% too low. Grid-cell errors are 34–37%.",
                               DEV_AFTER, BOX_AREA + " Its southern edge reaches the Mexican border."]},
    # Round 3 sealed regions (docs/TOURNAMENT_PLAN.md): opened once on 2 Nov 2026 for the round-3 exam (CONFIRMED,
    # docs/ROUND3_CONFIRMATION.md) -> spent. Never used for development; product since 14 Nov 2026.
    "northern_algeria": {"country": "Algeria", "name": "Northern Algeria", "box": (-1.0, 34.5, 8.5, 37.1),
                         "roles": {"spent", "product"},
                         "notes": [START_FULL.format("November 2000", "December 2025"),
                                   ROUND3 + "Its own figures there, in burning days: cell-month error 49.5% (simple "
                                   "conversion 64.6%), national-month error 10.6% (33.0%), predicted total 1.026 × "
                                   "observed.",
                                   FORWARD + "every check passed in both units (the burning-day figures are the exam's "
                                   "own, rerun): hotspots regional monthly error 8.2% against 16.2%, total 1.0% too high. "
                                   "Grid-cell errors are 50%.",
                                   BOX_COUNTRY.format("Algeria")]},
    "southern_france": {"country": "France", "name": "Southern France", "box": (3.0, 42.5, 7.7, 44.5),
                        "roles": {"spent", "product"},
                        "notes": [START_FULL.format("December 2000", "November 2025") + " December 2025 is left out: "
                                  "neither VIIRS file has a detection in its last 3 days (the record-end rule).",
                                  ROUND3 + "Its own figures there, in burning days: cell-month error 105.0% (simple "
                                  "conversion 121.8%), national-month error 29.6% (56.6%), predicted total 0.954 × "
                                  "observed.",
                                  FORWARD + "every check passed in both units, with regional monthly error 29.6% in "
                                  "burning days against 56.6% for a simple conversion. Southern France has few fires "
                                  "(633 MODIS burning days in the two years), and grid-cell errors are 104–105%, above "
                                  "the 100% limit that removed Jordan and Cyprus from the app: single cells here are not "
                                  "reliable.",
                                  BOX_COUNTRY.format("France")]},
    "south_australia": {"country": "Australia_SA", "name": "South Australia (southeast)",
                        "box": (136.5, -36.5, 141.0, -33.0), "roles": {"spent", "product"},
                        "notes": [START.format("March 2012", "December 2025") + " February 2012 is left out: the "
                                  "first MODIS detection in the box is on 16 February 2012, after the month's first 3 days.",
                                  ROUND3 + "Its own figures there, in burning days: cell-month error 65.4% (simple "
                                  "conversion 82.6%), national-month error 18.8% (40.2%), predicted total 1.041 × "
                                  "observed.",
                                  FORWARD + "every check passed in both units: hotspots regional monthly error 25.8% "
                                  "against 38.4% for a simple conversion, total 7.0% too low. Grid-cell errors are 65–70%.",
                                  BOX_AREA + " It is the southeast of the state, not the whole state."]},
    "n_california": {"country": "USA_NorCal", "name": "Northern California", "box": (-123.5, 37.5, -120.5, 40.5),
                     "roles": {"spent", "product"},
                     "notes": [START.format("January 2012", "December 2025"),
                               ROUND3 + "Its own figures there, in burning days: cell-month error 22.2% (simple "
                               "conversion 26.2%), national-month error 11.0% (16.0%), predicted total 1.081 × observed.",
                               FORWARD + "burning days passed every check (the exam's own figures, rerun). Hotspots failed "
                               "one check: grid-cell error 23.1%, more than 1 point worse than the simple conversion's "
                               "22.0%; regional monthly error 10.4% against 11.3%, total 3.7% too high. 2020 holds "
                               "17,700 of the two years' 29,049 MODIS burning days.",
                               BOX_AREA]},
}


def regions_with(role):
    return [k for k, v in REGIONS.items() if role in v["roles"]]


def cell_ids(lon, lat):
    """Global 0.25 deg cell id as 'ix_iy' strings."""
    ix = np.floor(np.asarray(lon, float) / CELL).astype(int)
    iy = np.floor(np.asarray(lat, float) / CELL).astype(int)
    return np.char.add(np.char.add(ix.astype(str), "_"), iy.astype(str))


def cell_bounds(cell_id):
    ix, iy = (int(v) for v in cell_id.split("_"))
    return ix * CELL, iy * CELL, (ix + 1) * CELL, (iy + 1) * CELL


def assert_not_sealed(region):
    if "sealed" in REGIONS[region]["roles"]:
        raise SystemExit(f"{region} is sealed until the model is frozen (docs/BAKEOFF_PLAN.md)")
