Verified against available documentation on **31 October 2026**. Critical corrections: the current FIRMS API documents **five-day requests**; Earth Engine’s VIIRS ID has changed; daily fire masks are observation-effort proxies; burned-area products are not fully independent validation.

**1. FIRMS fields, processing and access**

- **`scan` / `track`:** ground-pixel dimensions in kilometres across-track and along-track, respectively—not angles. `scan × track` approximates footprint area. They describe sensor geometry, not burned area. [NASA explanation](https://forum.earthdata.nasa.gov/viewtopic.php?t=5157).
- **Recovering angles:** numerically invert sensor-specific footprint geometry or a lookup table against both dimensions. VIIRS requires its aggregation zones; rounded FIRMS dimensions cannot recover exact geometry or scan-side sign. Prefer original geolocation products—MOD03/MYD03 or VNP03IMG/VJ103IMG/VJ203IMG—or full fire lists containing VZA. For spherical geometry, satellite scan angle \(\theta\) and ground view zenith \(z\) satisfy \(\sin z=(R+h)\sin\theta/R\). [Geometry equations](https://doi.org/10.5194/gmd-19-10123-2026), [VIIRS fields](https://www.earthdata.nasa.gov/s3fs-public/2024-07/VIIRS_C2_AF-375m_User_Guide_1.0.pdf).
- **VIIRS FRP:** detection uses 375 m I-bands, but FRP retrieval uses dual-gain **750 m M13**, because I4 saturates readily. M-band FRP is divided equally among the collocated **detected I-band fire pixels**, rather than copied in full to each. Summing those allocations reconstructs the parent retrieval; treating them as independent physical fires is inappropriate. [Primary research](https://arroma.uiowa.edu/docs/publication/paper_pdf/2024/deng_et_al_2024.pdf).
- **SP versus NRT:** the core fire algorithms are shared; expedited processing changes input availability, geolocation and quality screening. NRT location errors are usually small but can reach kilometres around anomalies/manoeuvres. Prefer SP for training and replace provisional NRT when SP arrives. **MCD14ML** is the monthly standard fire-location product; FIRMS distributes a subset. **MCD14DL** is the NRT vector product. [NASA processing comparison](https://forum.earthdata.nasa.gov/viewtopic.php?t=5134), [product definition](https://modaps.modaps.eosdis.nasa.gov/services/about/products/c61-nrt/MCD14DL-NRT.html).
- **Versions/types:** VIIRS collection identifiers use `002`; FIRMS uses version strings such as `2.0NRT`, `2.0RT`, `2.0URT`. Preserve strings and processing source separately. `type`: **0** presumed vegetation fire; **1** active volcano; **2** other static land source; **3** offshore. NRT generally lacks this attribution; missing `type` must not become zero. [VIIRS guide](https://www.earthdata.nasa.gov/s3fs-public/2024-07/VIIRS_C2_AF-375m_User_Guide_1.0.pdf), [version suffixes](https://forum.earthdata.nasa.gov/viewtopic.php?t=5195).
- **Repeated observations:** MODIS scan overlap creates bow-tie redundancy; VIIRS bow-tie deletion reduces within-swath redundancy but does not remove overlapping-orbit observations. Separate duplicate ingestion from legitimate repeated looks. Define the counting unit explicitly—pixel detections, cell-pass or cell-day. [Geometry analysis](https://doi.org/10.5194/gmd-19-10123-2026), [NASA orbit-overlap explanation](https://forum.earthdata.nasa.gov/viewtopic.php?t=5159).

API paths, under `https://firms.modaps.eosdis.nasa.gov`:

```text
/api/area/csv/{KEY}/{SOURCE}/{west,south,east,north}/{days}/{YYYY-MM-DD}
/api/data_availability/csv/{KEY}/ALL
```

The [current documentation](https://firms.modaps.eosdis.nasa.gov/api/area/) specifies **1–5 days**, starting at the supplied date, and **5,000 transactions/10 minutes**; one request can consume multiple transactions. NOAA-21 FIRMS coverage starts **2024-01-17**, independently of its launch date. Current SP/NRT boundaries require the availability query; I did not execute it without a key. For 2026, use those streams or the [archive request interface](https://firms.modaps.eosdis.nasa.gov/download/), which accepts Earthdata/email authentication rather than requiring MAP_KEY. [NASA availability example](https://firms.modaps.eosdis.nasa.gov/content/academy/data_api/firms_api_use.html).

**2. Observation effort**

Use these verified Earth Engine collections:

| Sensor | Collection | Coverage band |
|---|---|---|
| Terra | [`MODIS/061/MOD14A1`](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD14A1) | `FireMask`, low four bits |
| Aqua | [`MODIS/061/MYD14A1`](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MYD14A1) | Same |
| S-NPP | [`NASA/VIIRS/002/VNP14A1`](https://developers.google.com/earth-engine/datasets/catalog/NASA_VIIRS_002_VNP14A1) | `FireMask` |

The suggested `NOAA/VIIRS/001/VNP14A1` ID was **not verified**. VNP14A1 is a **1 km daily composite of the 750 m fire product**, not the FIRMS 375 m mask.

Common classes: **3 water, 4 cloud, 5 clear non-fire land, 6 unknown, 7/8/9 low/nominal/high-confidence fire**. Other classes represent missing/unprocessed pixels; VIIRS class 1 denotes bow-tie deletion.

**Cheapest recommendation:** Earth Engine batch reductions, separately per satellite and month. Using native-resolution pixel areas and a fixed land mask, export:

\[
E=\frac{\sum_{\text{days,pixels}}a_p\,1(FireMask\in\{5,7,8,9\})}
{D_{\text{month}}\sum_{\text{land pixels}}a_p}.
\]

Also export cloud, unknown and missing fractions. Include missing dates in the denominator and flag incomplete product delivery.

Call \(E\) **clear-observed land-day fraction**. Daily compositing loses individual overpasses, so it cannot exactly normalize raw FIRMS detection counts. Exact effort needs L2 fire masks/geolocation. [VIIRS compositing documentation](https://viirsland.gsfc.nasa.gov/PDF/VIIRS_activefire_User_Guide.pdf).

Alternatives: [AppEEARS supports VNP14A1.002](https://forum.earthdata.nasa.gov/viewtopic.php?t=4982); [Planetary Computer](https://planetarycomputer.microsoft.com/catalog) lists MODIS daily fire data. VIIRS availability there was unverified. [Harmony](https://harmony.earthdata.nasa.gov/docs) and OPeNDAP support subsetting, but collection-specific compatibility must be checked; neither is a universal fire-product endpoint.

**3. Timing, drift and diurnal correction**

Parse `acq_time` as zero-padded UTC `HHMM`:

\[
t_{\rm mean\ solar}=(HH+MM/60+\mathrm{longitude}/15)\bmod24.
\]

Use east-positive longitude and carry date rollover. Apparent solar time additionally requires the equation of time.

Verified timeline:

| Platform | Timing evidence |
|---|---|
| Terra | Approximately 10:30 originally; final inclination maintenance in 2020; approximately 10:15 in autumn 2022; approximately **09:00 in February 2026** |
| Aqua | Approximately 13:35 maintained through 2021; free drift January 2022; exceeded 13:45 February 2023; approximately **15:15 in February 2026** |
| S-NPP / NOAA-20 / NOAA-21 | Nominal **13:30 ascending / 01:30 descending** |

Sources: [Terra chronology](https://terra.nasa.gov/about/terras-orbit-changes/terra-orbital-drift-information), [Aqua chronology](https://aqua.nasa.gov/sites/default/files/AquaStatus.pdf), [March 2026 MODIS presentation](https://modis.gsfc.nasa.gov/sci_team/meetings/202603/presentations/Session%201/Lin%20-%20modis_geo_update_n_orbit_drift_20260311after.pdf), [NOAA ATBD](https://www.star.nesdis.noaa.gov/pub/smcd/akhuff/ACC_Product_Documentation/GBBEPx_V5_ATBD_2024.pdf). Orbital separation of 50 minutes does **not** imply a 50-minute difference in nominal equator-crossing solar time.

**SEVIRI:** LSA SAF `FRP-PIXEL`/LSA-502 provides 15-minute observations; Portugal and Lebanon lie within MSG viewing coverage. Access HDF5 through the registered [LSA SAF data service](https://lsa-saf.eumetsat.int/en/data/products/fire-products/). Sensitivity deteriorates away from nadir.

**Argentina:** use GOES-East `ABI-L2-FDCF`, especially `Power`, `Mask`, and quality fields. GOES-16 supplies historical observations; **GOES-19 replaced it on 7 April 2025**. GOES-18’s western position gives poorer Argentina geometry. [Product guide](https://www.goes-r.gov/users/docs/PUG-L2%2B-vol5.pdf), [NOAA transition](https://www.ospo.noaa.gov/operations/goes/status.html).

**Hackathon minimum:** retain solar time, satellite and day/night as model covariates; plot timing drift. Use geostationary data for a few large-fire diurnal examples. A validated national correction for small-fire counts is beyond a credible weekend implementation.

**4. Validation**

- **MCD64A1.061 / VNP64A1.002:** monthly, nominal **500 m**, available through Earthdata/LP DAAC. Both use reflectance **and active-fire inputs**: useful seam/season checks, not independent truth. [NASA comparison](https://wiki.earthdata.nasa.gov/spaces/FIRMS/blog/2025/09/08/461800781/New%2BVIIRS%2BGlobal%2BBurned%2BArea%2BProduct%2BAdded%2Bto%2BFIRMS).
- **EFFIS:** Portugal **and Lebanon** appear in [2024 burned-area results](https://publications.jrc.ec.europa.eu/repository/bitstream/JRC144093/JRC144093_01.pdf). [Downloads/services](https://forest-fire.emergency.copernicus.eu/applications/data-and-services) include current perimeters; historical extracts may require requests. Prefer supervised MODIS/Sentinel-2 perimeters; VIIRS-derived perimeters inherit hotspot dependence.
- **Sentinel-2:** keyless [Earth Search collection](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a), assets `nir08`/B8A, `swir22`/B12 and `scl`, all suitable for 20 m processing. Apply asset scale/offset, cloud/shadow masks; compute \(NBR=(NIR-SWIR2)/(NIR+SWIR2)\), then pre-minus-post dNBR. Validate interpreted scars rather than imposing a universal threshold.
- **Argentina:** [CONAE’s challenge notice](https://www.argentina.gob.ar/noticias/desafio-nasa-space-apps-challenge-2026-crea-soluciones-para-monitorear-incendios-con-datos) links its hotspot/burned-area catalogue. [INTA](https://www.argentina.gob.ar/inta/tecnologias/productos-satelitales-para-la-deteccion-y-monitoreo-de-eventos-extremos) provides event products; a comprehensive downloadable ground archive was unverified.
- **Lebanon:** [FireLab](https://firelab.balamand.edu.lb/Firelabweb_monjez/firedanger) chiefly provides danger forecasts. [CNRS reports](https://reports.cnrs.edu.lb/report/environment) provide Sentinel-2-based assessments. Public event-level ground-truth APIs were unverified.

**5. Static web stack and scale**

Recommend **Vite/TypeScript + MapLibre + [Terra Draw](https://maplibre.org/maplibre-gl-js/docs/examples/draw-geometries-with-terra-draw/) + [DuckDB-WASM](https://duckdb.org/docs/2.0/clients/wasm/data_ingestion)** in a worker. Keep the existing regular grid; H3 adds migration work and is [not equal-area](https://h3geo.org/docs/core-library/restable/).

Use [Observable Plot cells](https://old.observablehq.com/plot/marks/cell) for the 12-column calendar. ECharts offers [ARIA descriptions/patterns](https://echarts.apache.org/handbook/en/best-practices/aria/); D3 offers maximum customization. Recommend cividis/viridis counts, a diverging anomaly ramp, explicit missing-data patterns, keyboard access and a numeric table.

Calculated dense global size: **1,036,800 cells × 312 months = 323,481,600 rows**. Three float32 estimates alone occupy **3.88 GB**; a 32-byte row occupies **10.35 GB**, before compression. Compression must be measured.

Country sizing assumptions: at 100–150 CSV bytes/hotspot, **100,000 / 1 million / 10 million** records require approximately **10–15 MB / 100–150 MB / 1–1.5 GB**. These are estimates, not measured country totals.

Use [PMTiles](https://docs.protomaps.com/pmtiles/) for rendering; [FlatGeobuf](https://flatgeobuf.org/) for spatially indexed feature retrieval. Keep authoritative CSV exports sourced from full-resolution records. Test HTTP Range/CORS. GitHub Pages has a [1 GB site limit](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).

**6. Recent changes**

S-NPP delivery cessation at **2 November 2026, 13:00 UTC** is independently [confirmed by NOAA](https://forecast.weather.gov/product.php?format=CI&glossary=1&issuedby=NES&product=ADM&site=AFG&version=39). FIRMS links the [requested transition blog](https://www.earthdata.nasa.gov/news/blog/transitioning-from-suomi-npp-viirs-omps-what-firms-users-need-know), but its body returned 403; its exact publication date/text remain unverified here.

NASA’s [January 2026 continuity note](https://landweb.modaps.eosdis.nasa.gov/displayissue?id=1254) confirms substantially increased drift impacts in late 2024. LSA SAF introduced 1 km/10-minute MTG FRP demonstration data in 2025 and [suspended FRP-GRID in June 2026](https://lsa-saf.eumetsat.int/en/news/notifications/).

## RECOMMENDED DATA & APP ARCHITECTURE

```text
pipeline/                 ingest, coverage, harmonize, validate
app/src/                  map, calendar, query-worker, export
app/public/data/
  manifest.json           versions, dates, availability, provenance
  cells/{region}.parquet
  monthly/{region}/{year}.parquet
  uncertainty/{region}/{year}.parquet
  hotspots/{country}/{year}.parquet
  maps/{region}.pmtiles
```

Precompute Lebanon, Portugal and Chilecito; fetch only selected partitions. Keep API keys in the build pipeline.

Aggregate VIIRS FRP into candidate MODIS footprints before applying detection curves; then calibrate residuals and uncertainty. Validate against your existing shrinkage baseline.

For drawn areas, disclose fractional-cell approximation and resolution limits. Aggregate **joint uncertainty draws**, not interval endpoints. Derive probability above historical median and minimum detectable change from those draws. Compare incomplete months with matching historical elapsed days. Export original hotspots separately from harmonized estimates, with processing provenance and observation coverage.