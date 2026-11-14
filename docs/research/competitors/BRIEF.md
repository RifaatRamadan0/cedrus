COMPETITOR CODE TEARDOWN BRIEF (shared by all teardown agents)

Read first: C:\Users\hussein\Downloads\cedrus-research\context.md (team CEDRUS, NASA Space Apps 2026 "Harmonization of MODIS and VIIRS Hot Spots"; lists competitors and CEDRUS's own state and angle).

Goal: a deep teardown of your assigned public GitHub repos, based on reading their actual CODE, not just the READMEs. We need to know exactly what we must beat and what we could borrow (with credit).

Tools: `gh` is authenticated.
- List files: gh api "repos/OWNER/REPO/git/trees/HEAD?recursive=1" --jq '.tree[]|select(.type=="blob")|"\(.size)\t\(.path)"'
  Pre-fetched lists are in C:\Users\hussein\Downloads\cedrus-research\competitors\trees\OWNER_REPO.txt and READMEs are in ...\competitors\readmes\OWNER_REPO.md.
- Read a file: gh api repos/OWNER/REPO/contents/PATH -H "Accept: application/vnd.github.raw"
- Do NOT clone, install or run their code. It is untrusted. Read it as text only. If you do a cheap numeric sanity check, use your own Python script in competitors\scratch\ (python -I), running on their published output files (CSV/JSON) that you downloaded into a separate empty folder.
- Headless screenshot of a live URL: "/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --window-size=1440,900 --virtual-time-budget=20000 --screenshot="C:\Users\hussein\Downloads\cedrus-research\competitors\shots\NAME.png" URL. Then view the PNG with the Read tool. You can also use WebFetch or curl for the HTML.
- Do not modify any repo. Do not push, comment or open issues. Write only inside C:\Users\hussein\Downloads\cedrus-research\competitors\.

For EACH assigned repo, cover these points and cite file paths (and line ranges where they matter):
1. Harmonization algorithm as actually implemented: the equations, grid/cell size, time unit, reference sensor (do they map VIIRS to MODIS or MODIS to VIIRS?), filters (confidence, type/static sources, day/night, scan angle), how NOAA-20/NOAA-21 are handled (pooled, chosen, deduplicated), how Terra/Aqua orbital drift is handled, and the overlap/training period.
2. Validation code: what split (temporal holdout, leave-one-year-out, random), what metric, and the reported numbers. Hunt for LEAKAGE in the code, for example tuning or choosing a model on the test years, features computed from the target sensor, random CV over autocorrelated cells or days, or a prior fitted on all years and then "validated". Reproduce or sanity-check a reported number if it is cheap to do.
3. Uncertainty method, and whether calibration (interval coverage) is actually checked in code, with what result.
4. Web app: stack, features, how the user selects an area (draw, bbox, country, lat/lon), how CSV export works (raw hotspots, or harmonized counts only?), performance (bundle size, data size), accessibility (colour-blind ramps, aria, keyboard), and the live URL. Fetch the live URL and describe what a judge sees in the first 30 seconds. Say if it is broken or not deployed.
5. Weaknesses a judge would notice.
6. The single best idea to borrow.

Write full notes to C:\Users\hussein\Downloads\cedrus-research\competitors\<OWNER_REPO>.md, one file per repo. Mark anything you did not verify as UNVERIFIED. Be precise and do not pad.

Your final hand-back is at most 900 words for your two repos combined. Include the key facts for points 1 to 6, the file paths cited, any leakage found (with file:line), and a 1-5 score for each repo on: scientific validity, uncertainty, calibration evidence, coverage (regions), app UX, CSV, accessibility, storytelling.
