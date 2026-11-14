# Task: does our fire calendar match what really happened?

**For:** our data analyst · **Time:** about 3 days, done in small steps · **Skills:** spreadsheets, careful searching, a few copy-paste commands. No coding needed.

## What this is, in plain words

Our app says things like "October 2017 had 10 times more fire than a normal October in Portugal". Judges will ask: **how do you know that's real?**

Your job is to collect what *official* sources say happened, and compare it with our app. You fill in two small spreadsheets, and a script we wrote does the comparison and writes a report with charts.

This work **stays useful whatever we change later.** The official numbers are facts and don't change. If we improve the algorithm, we re-run one command and the report updates itself. Your spreadsheets become our permanent "reality check".

---

## Step 0: Set up your computer (once, about 30 minutes)

1. **Get access.** Send Hussein your GitHub username. He'll invite you to the repository, and you accept the invitation from your email or at https://github.com/RifaatRamadan0/cedrus/invitations
2. **Install Git:** https://git-scm.com/downloads, keeping all the default options.
3. **Install Python 3.11 or newer:** https://www.python.org/downloads/. **On Windows, tick "Add python.exe to PATH"** on the first screen of the installer.
4. Open a terminal. On Windows that's **PowerShell** (press Start and type *PowerShell*); on a Mac it's **Terminal**. Then copy these lines **one at a time**:

```bash
git clone https://github.com/RifaatRamadan0/cedrus.git
cd cedrus
python -m venv .venv
```

Then turn on the project's own Python. Use the line for your computer:

```bash
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Mac:
source .venv/bin/activate
```

If Windows says "running scripts is disabled", run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer `Y`, and try again.

Then:

```bash
pip install -r requirements.txt
git checkout -b analysis/reality-check
python tools/check_reality.py
```

✅ **Setup worked if** the last command prints `Wrote ...analysis\reality\REPORT.md`. The report will be mostly empty, because your sheets are empty.

**Every later session** starts in the `cedrus` folder with the "turn on" line above (`.venv\Scripts\Activate.ps1`, or `source .venv/bin/activate` on a Mac).

---

## Step 1: Write down what you expect, before you look (10 minutes)

Create a file `analysis/reality/EXPECTATIONS.md` with 3–4 sentences. For example: *"I expect Portugal's worst official years (I think 2003, 2005 and 2017) to also be our biggest years. I expect Lebanon to be harder, because its fires are small."*

Why: if you write expectations **before** seeing the results, a surprise is a real finding. Scientists call this pre-registration, and the judges value it.

---

## Step 2: Official burned area per year (1–1.5 days)

Open `analysis/reality/official_yearly.csv` in Excel or Google Sheets. It has these columns:

| column | what to write | example |
|---|---|---|
| `country` | exactly `Portugal` or `Lebanon` | `Portugal` |
| `year` | the year | `2017` |
| `burned_area_ha` | officially burned area that year, in **hectares**, a plain number with no commas | `539921` |
| `source_name` | who published it | `ICNF annual report 2017` |
| `source_url` | the **exact** page or PDF you took it from | `https://...` |
| `notes` | page or table number, anything odd | `Table 2, p. 14; mainland only` |

The example row only shows the format. Don't copy its number.

**Portugal: every year 2001–2024.**
- Use **mainland Portugal** ("Portugal Continental") only, because our map doesn't include the Azores or Madeira.
- Good places to look:
  - **PORDATA** (search "PORDATA área ardida");
  - **ICNF**, Portugal's forest institute (search "ICNF estatísticas incêndios rurais");
  - the **EFFIS annual fire reports** at https://effis.jrc.ec.europa.eu/reports-and-publications/annual-fire-reports, where each yearly report has a Portugal section.
- Take all years from one source if you can, so the numbers are consistent. Note it in `notes` if you have to mix sources.

**Lebanon: every year you can find.**
- The **EFFIS annual reports** above have a Lebanon section in many years, with the number of fires and the burned area.
- Also try the Lebanese Ministry of Environment, and the University of Balamand FireLab (https://firelab.balamand.edu.lb/).
- Lebanon has gaps. That's fine: only enter years you actually found.

**Rules:**
- **Never guess or estimate a number.** If you can't find a year, leave that year out.
- **Every row needs a `source_url`.** The script lists rows without one as problems.
- Save the file as **CSV** (File → Save As → CSV UTF-8), keeping the same name and folder.

Run `python tools/check_reality.py` whenever you like, to see the report grow.

---

## Step 3: Known big fires (1 day)

Open `analysis/reality/known_fires.csv`. Find **10 big fires in Portugal and 10 in Lebanon**, between 2003 and 2025, that news or official reports describe.

| column | what to write | example |
|---|---|---|
| `country` | `Portugal` or `Lebanon` | `Lebanon` |
| `place` | town or area | `Mechref / Damour` |
| `start_date` | the day it started, **written exactly like `2019-10-14`** (year-month-day) | `2019-10-14` |
| `end_date` | the day it was out, if known (same format) | `2019-10-16` |
| `burned_area_ha` | hectares, if reported | `1200` |
| `lat`, `lon` | where it was: right-click the town in Google Maps and click the numbers to copy them | `33.70`, `35.46` |
| `source_name`, `source_url` | where you read it | `L'Orient Today`, `https://...` |
| `notes` | anything useful | `several fires the same night` |

The example row only shows the format. Check every date and number in your own source.

**Leads to start from.** These are search terms, not facts: check every date yourself.
- **Portugal:**
  - Pedrógão Grande (June 2017);
  - the October 2017 fires in central Portugal;
  - Monchique (August 2018);
  - the Aveiro and Viseu fires (September 2024);
  - the big years 2003 and 2005.
- **Lebanon:**
  - the October 2019 fires (Mechref, Damour, Chouf);
  - the Akkar / Qobayat fires (July 2021);
  - Lebanon's fire statistics in the EFFIS reports.

**Pick a mix:** very big fires, medium ones, and fires in unusual months (spring or late autumn). Fires in unusual months are the best test of our calendar.

---

## Step 4: Run the check and read the report (half a day)

```bash
python tools/check_reality.py
```

Open `analysis/reality/REPORT.md` (GitHub shows it nicely once it's pushed) and the charts in `analysis/reality/figures/`.

The report answers two questions:
1. **Do our big years match the official big years?**
   - "Rank agreement" runs from −1 to 1. Near 1 means our busy years are the officially busy years.
   - It's also given for the **raw joined record**, which is what you get without our correction. If ours scores higher, that's evidence our correction helps.
2. **Did our calendar see each known fire?** For every fire, the report gives:
   - that month's value and its "normal";
   - how many times normal it was;
   - its rank among all 301 months;
   - whether it got the ▲ flare-up mark;
   - how hot the fire's own map square was.

Then write `analysis/reality/FINDINGS.md`, **5–8 plain sentences** for a fire chief, not a scientist:
- What matched?
- What didn't?
- Did anything surprise you, compared with your EXPECTATIONS.md?
- One honest limit. For example: "burned area and burning days are different things", or "Lebanon's records have gaps".

**Do not edit `REPORT.md` by hand.** It's rewritten every time the script runs.

---

## Step 5: Send it to the team (15 minutes)

```bash
git add analysis/reality
git commit -m "Reality check: official burned area and known fires"
git push -u origin analysis/reality-check
```

Then open https://github.com/RifaatRamadan0/cedrus. GitHub shows a yellow bar saying **"Compare & pull request"**. Click it, write two lines about what you did, and click **Create pull request**.

You can push again as often as you like while you work: `git add`, `git commit`, `git push`.

### You're done when

- [ ] `official_yearly.csv` has Portugal 2001–2024 and every Lebanon year you found, each with a source link
- [ ] `known_fires.csv` has about 10 Portugal and about 10 Lebanon fires, each with a date, place, coordinates and source link
- [ ] `REPORT.md` section 3 ("Sheet problems") says **None.**
- [ ] `EXPECTATIONS.md` (written first) and `FINDINGS.md` (written last) are there
- [ ] the pull request is open

**Only change files inside `analysis/`.** If something in the app or the script looks wrong, write it in Slack. Don't fix it yourself.

---

## Extra ways to help (small, each one useful on its own)

Pick any of these whenever you want a break from Step 2–3. Each takes 1–3 hours.

1. **Sources and credits list.** Space Apps requires us to credit every dataset, tool, image and video, and teams lose prizes over this. Create `docs/SOURCES.md` with a table: *name · what we use it for · link · licence*.
   - Start with: NASA FIRMS (MODIS and VIIRS fire data), NASA GIBS (the map background), MapLibre (the map), terra-draw (drawing on the map), Python, pandas, NumPy, SciPy and matplotlib.
   - **Important:** find out where the background video `web/assets/wildfire.mp4` and its picture `web/assets/wildfire-poster.jpg` came from, and whether we're allowed to use them. Ask Hussein who added them. If nobody knows, write that down: we may have to replace them.
2. **Test the app like a user.** Hussein can run the app for you, or once it's online you open the link.
   - Try it on your phone and on a laptop. Pick Lebanon, draw an area, download a CSV, press play, try Story mode.
   - Every time something is confusing or broken, open a **GitHub issue**: on the repository page click **Issues → New issue**. Write the title, then: what you did, what you expected, what happened, and a screenshot.
3. **Plain-language FAQ.** Create `docs/FAQ.md` with 8 short questions a journalist or a mayor might ask, each answered in 2–3 sentences. For example: *"What is a burning day?"*, *"Why does the raw satellite count jump in 2012?"*, *"How far back does it go?"*, *"Can I use it for my village?"* Read the README for the answers, and ask in Slack if unsure.
4. **Arabic version of the key texts** (if you read Arabic). Translate the FAQ and the app's main headings into `docs/FAQ_ar.md`. Our local-impact angle is Lebanon, and an Arabic page helps a lot.
5. **Screenshots for our project page.** Take clean screenshots (full screen, no other windows) of:
   - Portugal October 2017;
   - Lebanon's calendar;
   - the tree-rings view;
   - the "Two eyes, one fire" panel;
   - a drawn area.

   Put them in `docs/screenshots/` with simple names such as `lebanon_calendar.png`.

Push these on the same branch, or a new one, the same way as in Step 5.

**Stuck for more than 20 minutes? Ask in Slack.** A quick question beats a lost afternoon.
