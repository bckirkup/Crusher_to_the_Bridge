# VSP outbreak-level series: extraction spec

What the observed COVID discontinuity is measured on. This file specifies the
extraction only. The statistic computed from it, and the analysis, are specified
in `vsp_covid_discontinuity_findings.md`; do not compute era comparisons here.

`docs/vsp_covid_discontinuity.png` is an operator-supplied figure over
n=261 (2004-2019) and n=64 (2022-2026) posted outbreaks. The underlying
per-outbreak table has never been in the repository, so no number read off that
figure can be checked. This extraction replaces it with a table that can be.

## Source

CDC Vessel Sanitation Program posts one page per outbreak, and index tables by
year. Posting criteria, unchanged across the break and verified in both eras:
ship under VSP jurisdiction, 100+ passengers, voyage 3-21 days, and **3% or more
of passengers or crew reporting AGE symptoms to the ship's medical staff**. VSP
may also post outbreaks of public health significance that miss those criteria,
so the sample is "posted", not "≥3%".

**Every year is available from a CDC-hosted page**, so `web.archive.org` is not
the source of record for any of it. CDC maintains its own archive at
`archive.cdc.gov`, reachable directly under the `www_cdc_gov` path prefix, and
two pages there carry the entire historical series in one table each with the
counts inline:

| years | source of record | counts |
|---|---|---|
| 1993-2018 | `https://archive.cdc.gov/www_cdc_gov/nceh/vsp/surv/outbreak/archived-outbreaks-1993-2018.html` | in the table |
| 2019-2022 | `https://archive.cdc.gov/www_cdc_gov/vessel-sanitation/cruise-ship-outbreaks/earlier-outbreaks-2019-2022.html` | in the table |
| 2023-2025 | `https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/earlier-outbreaks.html` | detail page per row |
| current year | `https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/index.html` | detail page per row |

Both archive pages use one layout: a single table with columns `Cruise Line`,
`Cruise Ship`, `Sailing Dates`, `Causative Agent`, `Case Counts (Passengers)`,
`Case Counts (Crew)`, the counts formatted `84 of 1,986 (4.23%)`, and sailing
dates fully qualified with four-digit years on both ends
(`12/29/2022-1/3/2023`), so no century inference is needed. Rows through 2003,
and two rows in 2004, read **`Data not available`** in both count columns:
that is CDC's own statement, not a retrieval failure, and it must be recorded
as such rather than as a parse gap.

The two live pages carry no counts at all — `Cruise Line`, `Cruise Ship`,
`Sailing Dates`, `Causative Agent` only — so each row's linked detail page is
required. Detail pages carry `Number of passengers who ... reported being ill
during the voyage out of total number of passengers[ onboard]: 135 of 1318
(10.24%)` and the corresponding crew sentence. Wording varies ("who have
reported" vs "who reported", with/without "onboard", "Final case counts:"), so
match on the numeric `N of M (P%)` pattern within the passenger/crew sentence
rather than on exact prose.

### Cross-source reconciliation, mandatory

The first extraction of this series took 1994-2019 from a `web.archive.org`
snapshot of the retired `cdc.gov/nceh/vsp/surv/gilist.htm` and its per-outbreak
detail pages. That gives an independent path to the same numbers, and it is kept
for exactly that purpose. Reconcile the two row by row, keyed on cruise ship
plus sailing dates, and log:

- rows present in one path and absent from the other;
- rows where any of the four counts disagree, with both values and both URLs.

Where they disagree the CDC-hosted page wins and the disagreement stays in the
log. Agreement across two independently retrieved paths is the strongest
evidence available here that a count is what CDC published; silent divergence is
the failure mode this whole exercise exists to prevent.

## Output

`telemetry_buffer/observation_model/vsp_outbreak_series.csv`, one row per posted
outbreak, sorted by `voyage_end` descending, columns exactly:

```
year,cruise_line,ship,voyage_dates_raw,voyage_end,causative_agent,
pax_ill,pax_total,pax_pct_page,crew_ill,crew_total,crew_pct_page,
era,counts_published,source_url,retrieved
```

- `year` — calendar year of the index table the row came from, integer.
- `voyage_dates_raw` — the page's date string, verbatim, unparsed.
- `voyage_end` — ISO date of the end of the voyage, resolved against `year`
  (legacy pages write `12/13 – 1/3, 2019`, so the end year can differ from the
  index year); empty if it genuinely cannot be resolved.
- `causative_agent` — verbatim, lowercased, e.g. `norovirus`, `unknown`,
  `e. coli`.
- `pax_pct_page`, `crew_pct_page` — the percentage **as printed on the page**,
  not recomputed. Empty where the page omits it.
- counts — integers with separators stripped. Empty where the page omits the
  crew sentence entirely (some legacy pages do). Never impute.
- `counts_published` — `full` where both the passenger and crew counts are
  present, `passenger_only` / `crew_only` where one is, `data_not_available`
  where the source says so in as many words, and `unparsed` where the source
  appears to publish counts that could not be read. The last value means a
  defect; the fourth does not, and collapsing the two loses the distinction
  between what CDC never published and what we failed to read.
- `era` — `pre` for `voyage_end` in 2004-01-01..2019-12-31, `shutdown` for
  2020-01-01..2021-12-31, `post` for 2022-01-01 onward, `legacy_pre2004`
  before that. Keep every row; the analysis selects. The 2019-2022 archive page
  carries the 2020 and 2021 voyages, and they belong in the CSV as `shutdown`
  even though nothing scores them — an era whose rows are absent cannot be
  distinguished from an era with no outbreaks.
- `source_url` — the exact URL the counts were read from (detail page where a
  detail page was used, index page otherwise), including the
  `web.archive.org/web/<timestamp>/` prefix where applicable.
- `retrieved` — ISO date of the fetch.

Also write `vsp_outbreak_series_extraction_log.md` next to it recording: rows
per year, which layout each year used, the snapshot timestamps used, every row
where a count was missing or unparseable (with its URL), and every row that
failed the consistency check below. Unresolved rows stay in the log, and the
CSV keeps them with empty fields; nothing is dropped silently.

## Consistency checks, all mandatory

1. **Printed-percentage check.** For every row with counts and a printed
   percentage, `100 * ill / total` must agree with `pct_page` to within 0.06
   percentage points, or 0.5 percentage points where the page prints a
   whole-number percentage. Report every failure in the log with its URL. Do
   not "fix" a mismatch by overwriting either field — a mismatch is either a
   parse error or a CDC error and both must be visible.
2. **Row-count check.** Rows extracted per year must equal the number of data
   rows in that year's index table. Report both numbers per year in the log.
3. **Plausibility check.** `0 < ill <= total`, `total >= 100` for passengers,
   `pax_pct_page <= 100`. Log violations; keep the rows.
4. **Threshold check.** Report, per era, how many rows have both
   `pax_pct_page < 3` and `crew_pct_page < 3` — these are the discretionary
   "public health significance" postings, and the analysis needs to know how
   many there are. Do not drop them.
4b. **Printed-percentage triage.** Classify every failure of check 1 into: CDC
   truncating rather than rounding (`7.9654` printed as `7.9`), a CDC error of
   another kind (`0.7375` printed as `0.07`), or a parse error on our side.
   Resolve each against the CDC-hosted page's own text and say which it is; a
   bare list of mismatches does not tell a reader whether the dataset is sound.
5. **Idempotence.** Re-running the fetch script against the raw cache must
   reproduce the CSV byte-for-byte.

## Script

`telemetry_buffer/observation_model/fetch_vsp_outbreaks.py`, stdlib plus
whatever is already in `requirements.lock.txt` only. Requirements:

- Caches every fetched page under a path outside the repository, default
  `~/vsp_cache/`, keyed by URL; `--refresh` refetches, default reuses the cache.
  The committed CSV must be reproducible from the cache without network.
- Polite: serial fetches, a delay between requests, retry with backoff on 429
  and 5xx from `web.archive.org`, and a clear failure if a page cannot be
  retrieved rather than a silently short table.
- `--out` for the CSV path, `--log` for the extraction log.
- No era comparison, no statistics, no plotting. Extraction and checks only.
