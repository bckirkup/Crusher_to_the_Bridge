---
name: searching-literature-evidence
description: Search the peer-reviewed literature with the Consensus MCP server to source a model constant, check an anchor, or find measurements of a mechanism — query construction, filter discipline, what the results do and do not contain, and how a hit becomes a provenance comment. Use whenever a constant, rate, fraction, kernel or anchor needs a citation, or when asked what the literature says about a mechanism.
---

# Searching the Literature (Consensus MCP)

The `consensus` MCP server has one tool, `search`, over ~220M papers
(Semantic Scholar, PubMed, Scopus, ArXiv). It returns title, authors, year,
journal, citation count, DOI, a Consensus URL, and the abstract.

```
mcp_tool(command="call_tool", server="consensus", tool_name="search",
         tool_args='{"query": "fomite contact rate shared surface touches per hour"}')
```

Run `mcp_tool(command="list_tools", server="consensus")` for the full,
current parameter list before using an unfamiliar filter.

## Query construction

Query in the vocabulary of the paper you want, not the question you have. The
useful query names the **measured quantity plus its setting**:

- Good: `surface touch frequency shared surfaces per hour office video observation`
- Weak: `how often do people touch things`

If a search returns reviews and models rather than measurements, add the words
a measurement paper would carry — `video observation`, `tracer`, `quantitative`,
`per hour`, `log10 reduction`, `transfer efficiency`, `titre` — and search
again. Two or three re-phrasings are normal and cheaper than reading twenty
review abstracts.

Search for the mechanism, then separately for the number. The paper that
establishes that a route matters is usually not the paper that measured its
rate.

## Filter discipline

Default to **no filters**. Every filter silently removes evidence, and the
corpus ranking is already topical. Set a filter only when the task states the
constraint:

- `year_min` — only for "recent" / "since 20XX" asks. A 2013 fingerpad transfer
  study is not stale; transfer physics did not move.
- `exclude_preprints=true` — when a value must be peer-reviewed to earn its grade.
- `study_types` / `medical_mode` — clinical-evidence questions (drug efficacy,
  guidelines), not behavioural or environmental measurements. `medical_mode`
  restricts to ~8M top medical documents and will drop the built-environment,
  food-microbiology and indoor-air journals that most fomite and shedding
  constants come from.
- `domain` — academic field codes (`med,bio,env,eng`), not web domains.
- `sjr_max=1` for Q1-only. Do not reach for `sjr_min`; it *excludes* the top
  tiers, which is almost never wanted.
- `human`, `controlled`, `sample_size_min`, `citation_min` — only when asked.
  Filtering to human studies drops exactly the in-vitro transfer and surrogate
  work (MNV1, Phi6, MS2) that quantifies fomite and hand routes.

Verified behaviour of the ranking: with `domain` and `year_min` set, the top hit
for the same query changes. Filters reorder as well as remove, so a value found
under one filter set should be re-checked without them before it is called *the*
measurement.

## Result handling

- Default page returns 20 papers; `page_size` narrows it (5 works). `page=1`
  returns a genuinely different set on this organisation's plan, so paginate
  when the first page is all reviews.
- Twenty abstracts overflow the tool result. The output is truncated and the
  full text written to a file named in the truncation notice — **read that
  file**. Items 15-20 are frequently the measurement papers, because reviews
  rank higher.
- The abstract is often enough for a magnitude and never enough for a
  definition. When the constant matters, open the DOI and read what was
  counted.
- Consensus asks for numbered inline citations with hyperlinked titles and the
  exact URLs it returned. Preserve the DOI when it gives one.

## Turning a hit into a sourced constant

Read `.agents/skills/model-parameter-provenance/SKILL.md` first; this section is
only the search half of that discipline.

Capture, at the point of use: **what was measured**, **in what setting**, the
value with its range, and author + year + journal. That is exactly the material
a provenance comment needs:

```python
# Stainless steel -> fingerpad, MNV1 infectivity, 40 min drying,
# 2.0 +/- 2.0%. Tuladhar et al. 2013, Int J Food Microbiol
# (DOI: 10.1016/j.ijfoodmicro.2013.09.018). Grade B: surrogate virus,
# food-contact surface standing in for a cabin fixture.
TRANSFER_FRACTION_SURFACE_TO_HAND = 0.020
```

The setting is what sets the grade — A for this quantity in this setting, B for
an analogous setting, C for inferred or assumed. A search that returns a number
does not by itself produce a Grade A constant, and an abstract's headline figure
is not evidence about the definition of the quantity: all-surface touch rates
and shared-surface touch rates differ by ~10x under the same title.

## What this search must never be used for

Do not search for a value that makes an anchor come out right. Sourcing a
constant independently is what makes the later comparison against VSP, Park, or
the passenger/crew ratio a real test; screening candidate papers by which value
helps destroys that test just as surely as fitting the scalar by hand.

Practically: fix the query and the filters from the definition of the quantity,
before looking at what the model needs. If several papers measure it, take a
stated central value or the midpoint of the range and say which — not the end
that helps.

Report a null result as a result. "No paper measures total high-touch surface
area per cabin in m²" is a finding worth recording, and is the honest route to a
declared Grade C. Inventing a plausible number because the search came back
empty is the failure mode this skill exists to prevent.
