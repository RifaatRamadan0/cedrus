# CEDRUS: project page (NASA Space Apps 2026, Beirut)

Final text for the Space Apps project page fields (paste field by field). Only the YouTube links of the two demo videos remain to be pasted.
Every number here is in the repository; the source file is named in brackets so anyone can check it.

---

## Project name
CEDRUS: Same fires. Fair record.

## High-level project summary (≤ 1,000 characters)
For 25 years, NASA satellites have counted the world's fires, but the record is split between two kinds of eye. MODIS, flying since 2000, is retiring. VIIRS, flying since 2012, sees smaller fires, so a record that simply switches from one to the other jumps in 2012. That jump is the instrument changing, not the fires. CEDRUS translates every satellite count into one consistent scale and turns it into a fire calendar for any area. You draw an area and see every month from December 2000 to today: whether this month is above or below normal, how sure the estimate is, the fire records as CSV, and a 7-day fire-weather outlook against that place's normal. We proved the translation works the way exams prove a student knows the subject: rules written and dated first, then tested once on regions the model had never seen. The first exam failed and we published it. The next two passed every test. The app shows it all, in English, Spanish and Arabic.

## Link to project demo
- 30-second demo video (global judging): https://youtu.be/6etdoVmqyTE
- 2-minute video (local judging): PASTE YOUTUBE LINK

## Link to final project
- Website: https://rifaatramadan0.github.io/cedrus/
- Code and data: https://github.com/RifaatRamadan0/cedrus

## Detailed project description

**What it does**
- **A fire calendar for any area:** one of 18 regions on six continents (from Portugal, Lebanon and Syria to Chile, South Africa, Australia and California), a shape you draw, or a point and radius.
  - Every month from late 2000 on one scale: to July 2026 for Portugal, Lebanon, Syria and the La Rioja area of Argentina, to late 2025 for the other 14.
  - The challenge asks for this month against the historical median and anomalies against the multi-year average; both are there, one click apart.
- **Two ways to count:**
  - **Burning days**, the default: how many days each ~1 km square had a fire seen.
  - **Hotspots**: every satellite detection, the challenge's own unit.
  - Both are in MODIS-equivalent terms.
- **Honest uncertainty:** every estimated month has an 80% range and a trust check (reliable / use with care / too uncertain / too few fires to judge). On screen, doubt is drawn as smoke over the number.
- **Downloads:** every hotspot and every burning day inside your area as CSV, each with its weight in the harmonized total, plus the monthly record.
- **Fire weather outlook (prevention):** the next 7 days of heat, dry air, wind, rain and topsoil moisture for the selected region, combined into the Hot-Dry-Windy Index (Srock et al. 2018) and ranked against the same weeks in 2003–2025 (ERA5), with whether today is inside the region's normal fire season. It is an outlook of conditions that help fires spread, not a fire prediction. We also tested, per region, whether fire weather tracks our fire record: a moderate link in Portugal (rank correlation 0.58) and southern Europe, a weak one in Lebanon (0.28), and little in Australia; the app states it for each region.
- **Right now vs normal:** NASA's live feed for the last complete days, against the same calendar days in 2019–2025 (like-for-like NOAA-20 counts). This is the early-warning question the challenge's authors asked: is this month unusual here?
- **Made to be understood:**
  - places ignite on the map, sized by their fire;
  - a tree-ring view of 25 years;
  - a ghost flame showing this month beside a normal one;
  - a 25-years-in-25-seconds playback;
  - a story mode through the biggest months;
  - a panel showing, with the area's own numbers, why raw counts jump in 2012.
  - Every animation carries a fact from the data. "Reduce motion" turns them all still, and every colour scale is tested for colour blindness.

**How it works**
- **Translation per place and month.** For every 0.25° cell, calendar month and time of day, the model learns from 2012–2019 how many MODIS fires one VIIRS fire stands for. MODIS and Suomi NPP flew together in those years.
  - Cells with little history lean on their region's ratio, which keeps estimates stable.
  - For burning days, the ratio is learned separately for four classes of fire power, because how many of VIIRS's fires MODIS also sees depends on how strong they are.
- **Continuity after Suomi NPP.** Suomi NPP stopped delivering data on 2 November 2026. NASA's own guidance is to switch to NOAA-20 and NOAA-21, with no cross-calibration. We calibrate NOAA-20 to Suomi NPP on the months both flew, so the record carries on without a step. In the exam, the two satellites' estimates agreed in 97.3% of months.
- **From 2022 the record is estimated from VIIRS.** Terra and Aqua have left their planned orbits and now cross each place at a different time of day. The app's satellite check shows this drift.

**How we know it works: three sealed exams**
Each exam's rules and pass marks were committed, dated, before its regions were downloaded, and the model sat it once ([docs/](../)).
- **Exam 1 failed.** On Morocco, Tunisia, central Chile and the Western Cape, one ratio per region beat our model, and the satellite handover agreed only 69%. We published the failure, found the two causes, and fixed them ([CONFIRMATION_RESULTS.md](../CONFIRMATION_RESULTS.md)).
- **Exam 2 confirmed** the hotspot model on central Spain, southern Italy, southwest Australia and southern California. All five tests passed ([ROUND2_CONFIRMATION.md](../ROUND2_CONFIRMATION.md)).
- **Exam 3 confirmed** the burning-day model, the winner of a nine-model tournament, on northern Algeria, southern France, South Australia and northern California ([ROUND3_CONFIRMATION.md](../ROUND3_CONFIRMATION.md)):
  - square-by-square error 29.7%, against 36.2% for one simple ratio;
  - region-month error 11.6%;
  - the 80% ranges held the real value 83.8% of the time;
  - totals within 7%;
  - 97.3% handover agreement.
- **Every region in the app was also tested on its own data**, and where a region does worse, the app says so in that region's notes.

**Benefits and intended impact**
- **For fire services and planners:** in Lebanon, Syria and Argentina, where fire calendars are scarce, they can see when the season runs in their own district, whether this month is unusual, and how far to trust the number.
- **For researchers:** a 25-year record that does not jump in 2012 and keeps going after Suomi NPP, with every weight downloadable.
- **For everyone:** the method and the tests are open (Apache-2.0), and every number can be rebuilt from the code.

**Tools and languages:** Python (pandas, NumPy, SciPy, matplotlib) for the pipeline and the tests. A static web app in plain JavaScript with MapLibre GL, terra-draw and three.js, on NASA GIBS imagery, hosted on GitHub Pages. GitHub Actions refresh the live data daily. No server: the whole app is static files.

## Use of NASA data
- **NASA FIRMS active fire data,** the core of the project:
  - MODIS Collection 6.1 (Terra and Aqua, 1 km);
  - VIIRS 375 m from Suomi NPP and NOAA-20, standard-quality archive, January 2012 to July 2026 (MODIS from November 2000);
  - the near-real-time NOAA-20 feed for the "right now" comparison.
- **NASA GIBS** Blue Marble and Black Marble imagery for the map and globe.
- **NASA Goddard Scientific Visualization Studio** footage in the demo videos (svs.gsfc.nasa.gov/4820 and /4741).
- **NASA documentation:**
  - the MODIS C6/C6.1 and VIIRS 375 m active fire user guides;
  - the Earthdata notices on the Suomi NPP transition.

## Use of space agency partner data
- No partner-agency data products.
- The challenge was authored by CONAE (National Space Activities Commission of Argentina, a 2026 Space Agency Partner); our La Rioja / Chilecito region follows its example.

## References
- Giglio, L., Schroeder, W., Justice, C. O. (2016). The collection 6 MODIS active fire detection algorithm and fire products. *Remote Sensing of Environment* 178, 31–41. doi:10.1016/j.rse.2016.02.054
- Schroeder, W. et al. (2014). The New VIIRS 375 m active fire detection data product. *Remote Sensing of Environment* 143, 85–96. doi:10.1016/j.rse.2013.12.008
- Giglio, L., Csiszar, I., Justice, C. O. (2006). Global distribution and seasonality of active fires as observed with the Terra and Aqua MODIS sensors. *JGR* 111, G02016. doi:10.1029/2005JG000142
- NASA FIRMS: https://firms.modaps.eosdis.nasa.gov/ (Davies et al. 2009, doi:10.1109/TGRS.2008.2002076)
- NASA Earthdata, "Transitioning from Suomi NPP VIIRS & OMPS: what FIRMS users need to know" (2026)
- Related 2026 work on fusing MODIS and VIIRS fire radiative power: *Remote Sensing* 18, 01650 (2026). We fuse counts per place and month instead, and test on unseen regions.
- Software: MapLibre GL JS, terra-draw, three.js, pandas, NumPy, SciPy, matplotlib; country outlines from Natural Earth.
- Weather: Open-Meteo forecast and ERA5 archive APIs (CC BY 4.0). Srock, A. F. et al. (2018). The Hot-Dry-Windy Index: a new fire weather index. *Atmosphere* 9(7), 279. doi:10.3390/atmos9070279
- EFFIS / EU Joint Research Centre (2026), 2025 wildfire season; UNEP (2022), *Spreading like Wildfire*.
- Demo videos: music "Hymn To The Dawn" by Scott Buckley (CC BY 4.0); flame mascot drawn by Team CEDRUS.

## Use of artificial intelligence (AI)
AI assistants (Anthropic's Claude, OpenAI's Codex) helped us write code, search the literature and draft text.
The method, the exam rules and the decisions are the team's. Every number shown comes from code and data in the repository and can be rebuilt from it. The exam plans were committed before their results existed.
The narration in both demo videos is an AI voice (ElevenLabs text-to-speech); this is stated on the videos' end cards and in their descriptions. No AI-generated images or video are used, and no NASA branding appears in anything we generated.
