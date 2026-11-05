> **Start with [ANALYST_REALITY_CHECK.md](ANALYST_REALITY_CHECK.md).** This Lebanon task is the deeper, optional follow-up; parts of its setup notes predate the current pipeline, so ask before running the pipeline steps.

# Task: Lebanon's fire history, and how much we can trust a small area

**For:** our data analyst · **Size:** a first pass in 3–4 days · **Tools:** Python + pandas + matplotlib (or anything you prefer)

## Why this matters

Our project turns 25 years of NASA satellite fire detections into a **fire calendar**:
which months and years burn most, and whether this month is unusual. Two satellite
instruments recorded those years. MODIS (2000–) is retiring. VIIRS (2012–) sees many
more small fires. If you join their records without care, fire activity seems to jump
in 2012. We correct that.

Your job gives us two things no other team has:

1. **The Lebanon story.** We found no published fire calendar for Lebanon. You'll
   build the first one from the data, and it's our local-impact angle for the judges.
2. **The numbers behind our "trust check".** Lebanon is small and has few fires, so
   random noise is large. We need to know how big a change has to be before it's real,
   not noise. Every other team ignores this.

You don't need to know satellites. Treat each row as "a satellite saw something
burning at this place and time".

## Setup (15 minutes)

```bash
git clone https://github.com/hyounes-svg/cedrus.git
cd cedrus
pip install -r requirements.txt
python pipeline/01_download.py --country Lebanon
```

This downloads about 40 small CSV files into `data/raw/lebanon/` (2000–2025).
`manifest.json` in that folder records where each file came from. Keep it. Every
number we publish has to be traceable to its source.

⚠️ **Don't run `02_aggregate.py`–`04_export_web.py` for Lebanon yet.** They're set up
for Portugal: the area box is fixed in `pipeline/common.py`, so they would throw away
every Lebanon row. Work in a notebook straight from the raw CSVs.

Put your work in `analysis/` (notebook, a `figures/` folder, and your findings file).
Don't commit `data/`: it's ignored on purpose.

## What's in a row

| File | Columns you need |
|---|---|
| `modis_<year>_Lebanon.csv` | `latitude, longitude, acq_date, acq_time` (UTC, HHMM), `satellite` (Terra/Aqua), `confidence` (0–100), `frp` (fire power, MW), `daynight` (D/N), `type` |
| `viirs-snpp_<year>_...` / `viirs-jpss1_<year>_...` | same, but `confidence` is `l`/`n`/`h` (low/nominal/high). Suomi NPP = `viirs-snpp`, NOAA-20 = `viirs-jpss1` |

**Use the same filters as our main test** (see `docs/TEST_PLAN.md`), so your numbers
match ours:
- `type == 0` (vegetation fire; drops gas flares, volcanoes, factories)
- MODIS `confidence >= 30`; VIIRS `confidence` in `n`, `h`
- Lebanon box: longitude 35.10–36.65, latitude 33.05–34.70 (the country file can include border spill)

## Part 1: Lebanon's fire calendar (the story)

Answer each question with **one chart plus one or two plain sentences**.

1. **How many detections per year?** MODIS 2001–2025, Suomi NPP 2012–2025 and NOAA-20 2018–2025 on one chart. You should see VIIRS far above MODIS. That gap is the problem we're solving.
2. **The calendar.** A month × year heatmap, one for MODIS and one for VIIRS. Use a colour-blind-safe ramp (`cividis` or `YlOrRd`) and show zero months in light grey. When is Lebanon's fire season?
3. **Season dates.** For each year, find the day when 10%, 50% and 90% of that year's detections had happened (start, middle, end). This is the same definition we used for Portugal. Give the median and spread across years. Do the 10%/50%/90% dates look sensible for Lebanon? If you think another definition fits better, say why.
4. **How much more does VIIRS see?** Over 2012–2022, divide Suomi NPP detections by MODIS detections, by month and separately for day and night. Portugal came out at about 2.7×. Is Lebanon similar? Does it change with the season?
5. **The south.** Split at latitude 33.4°N. That's roughly the Litani river and only an approximation, so say so. Plot yearly detections for the south vs the rest. Does 2023–2025 jump in the south only? These fires are linked to the conflict, so our app will label them "known non-weather cause" and keep them out of the "normal" baseline. Your chart is the evidence for doing that.
6. **The burning ban.** Lebanon bans burning near forests from 1 July to 31 October. What share of each year's detections falls inside that window?

## Part 2: How much can we trust a small area? (the statistics)

Fire counts are noisy. If an area normally has 4 fires in August, a year with 6 might be random luck.

7. **Noise floor for our Portugal test.** Our Portugal score was 52.8% error, measured cell by cell and month by month. Even a perfect model can't beat random noise.
   - Get the held-out MODIS counts by running the Portugal pipeline: steps 01–03, as in the README.
   - Treat each cell-month's real count as the true average λ. Simulate Poisson(λ) draws and compute the same error measure: Σ|draw − λ| ÷ Σλ.
   - What's the floor? If it's near 50%, our model is closer to the best possible than it looks. That changes our story for the judges.
8. **Smallest change we can detect.** Build a table for an area with a normal monthly count of 1, 2, 5, 10, 20, 50 and 100. How big must a month's count be before it's genuinely unusual (say 90% sure, using a Poisson or negative-binomial model)? Express it as "+X% above normal". Then compute where Lebanon as a whole, and one Lebanese district, sit in that table for August.
   - This becomes the trust check in our app: "*This area can show changes larger than X%.*"

## Rules we work by

- **Write down what you expect before you look.** A few lines at the top of your findings file is enough. If the data surprises you, that's a finding.
- **Plain language.** Write for a fire chief, not a statistician.
- **Say what you don't know.** Detections aren't burned area. The 33.4°N split is approximate. Small numbers are noisy.
- **Cite every source.** It's a Space Apps rule, and teams lose awards for missing citations.

## What to hand back

- `analysis/lebanon.ipynb`, which runs top to bottom on a fresh clone after the setup step
- `analysis/figures/`: one PNG per question
- `analysis/LEBANON_FINDINGS.md`: per question, one or two sentences plus the chart, and a short "what surprised me" section

Open a pull request on a branch such as `analysis/lebanon`. Ask in Slack whenever you're stuck. A quick question beats a day lost.

## Reading (only if you want depth)

- **Giglio, Csiszar & Justice (2006)**, *Global distribution and seasonality of active fires*, JGR 111:G02016, doi:10.1029/2005JG000142. How scientists define peak fire month and season length.
- **Schroeder et al. (2014)**, *The new VIIRS 375 m active fire detection data product*, RSE 143:85–96, doi:10.1016/j.rse.2013.12.008. Why VIIRS sees more small fires.
- **NASA FIRMS**: https://firms.modaps.eosdis.nasa.gov/, the source of all our fire data.
- **Lebanon context:**
  - The forest burning ban is reported by the National News Agency (search "Environment Minister warns against burning dry weeds").
  - University of Balamand FireLab daily fire-danger forecasts: https://firelab.balamand.edu.lb/
  - Government figures on conflict-related fires in the south: L'Orient Today (2023: 37% of forest fires; Oct 2023–Aug 2026: 16,000 ha). These are official figures, not independently verified, so say that wherever we use them.
