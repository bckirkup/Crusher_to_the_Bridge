---
name: searching-literature-evidence
description: Search the peer-reviewed literature with the Consensus MCP server to source a model constant, check an anchor, or find measurements of a mechanism — query construction, filter discipline, what the results do and do not contain, how to escalate when the abstract will not settle a definition, and how a hit becomes a provenance comment. Use whenever a constant, rate, fraction, kernel or anchor needs a citation, or when asked what the literature says about a mechanism.
---

# Searching the Literature (Consensus MCP)

The `consensus` MCP server has one tool, `search`, over ~220M papers
(Semantic Scholar, PubMed, Scopus, ArXiv). It returns title, authors, year,
journal, citation count, DOI, a Consensus URL, the abstract, and — with
`include_full_text_chunks=true` — query-relevant excerpts from the paper body:
Results and Discussion prose, Methods, and tables rendered as markdown.

```
mcp_tool(command="call_tool", server="consensus", tool_name="search",
         tool_args='{"query": "fomite contact rate shared surface touches per hour",
                     "include_full_text_chunks": true, "page_size": 3}')
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

## Full-text chunks: on by default for sourcing

`include_full_text_chunks=true` is the default for any query whose purpose is to
source a constant, check a definition, or verify a number a document already
claims. It is not a fallback for when the abstract is thin, and paywall status
does not predict whether it works — a paywalled *J Infect Dis* paper returned its
Results and both dose stratifications while two open-access transfer papers
returned no chunks at all.

Retrieval is **query-relevant**, so the query has to carry the quantity **and
its unit**: `copies/g of stool`, `GEC/ml`, `log10 per day`, `genome copies per
day`, `RT-PCR units`, `% transfer`, `copies/m³`, `half-life in hours`. A query
naming only the mechanism returns the paper's framing sections and misses the
number.

What chunks contain: a handful of body excerpts per paper, each labelled with the
section it came from, plus tables as markdown. What they do not contain: the
whole paper, every stratum of a table, or any guarantee that the specific
sub-population you need was in the excerpt selected. The pattern to expect is
one paper with several origins — a peak load body-verified in Results, a duration
in the same Results, and an illness duration that is in the abstract only.

Record where the number was read, in the register's axis-3 vocabulary
(`docs/parameter_provenance_register.md` §1): `R`, `Tn`, `Fn·dig`, `Me`, `Ab`,
`Sec`, `Tr`, or `?nr`. `Ab` on a Grade A constant is not a contradiction — it is
the defect this axis exists to expose.

**"Not in the chunks" is not a null result.** Absence from the excerpts returned
is not evidence that the paper omits the quantity, and zero chunks is not
evidence that a paper is inaccessible. Record it as `?nr` — *not retrieved* — and
only after at least two differently-phrased attempts, one of them naming the
table or figure the value is supposed to be in. A null result about the
literature requires that you queried the quantity by name and unit and still got
nothing; a `?nr` never licenses one.

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
  definition. When the constant matters, re-run the query with
  `include_full_text_chunks=true`, naming the quantity and its unit, and read
  what was counted in Methods and Results. Open the DOI when the chunks do not
  reach the stratum you need — and record which of the two you actually read.
- Consensus asks for numbered inline citations with hyperlinked titles and the
  exact URLs it returned. Preserve the DOI when it gives one.

## When the abstract is not enough

This is the dominant failure mode, not a rare one: a review of eight recent
literature-sourcing sessions found six of them stalled for want of full text.
Abstracts settle magnitudes; they almost never settle a **definition** — units
(infectivity vs RNA), endpoint, denominator, sampling times, matrix — and those
are what decides whether a number can be adopted at all.

So a paywall is not the end of the search. The ladder, in order:

1. `consensus` MCP `search` **with `include_full_text_chunks=true`** — ranking,
   DOI, abstract, and the body excerpts the section above describes. Always
   first, and it now settles many definitions outright: paywall status does not
   predict whether the body comes back. Re-query before climbing, naming the
   quantity and its unit, then the table or figure by number.
2. The DOI itself, then the open routes for the same article: PubMed Central,
   Europe PMC, the publisher's own HTML, an author or institutional copy.
   Supplementary tables live here and are frequently where the time-resolved
   measurements are. This is where to go when the chunks reach the paper but not
   the stratum you need — the common case is a table whose aggregate row returns
   and whose subgroup row does not.
3. A richer interface, when 1 and 2 cannot settle the definition. Available to
   this project, by asking rather than by a scripted call: **Consensus Pro
   reports**, **edison/aviary literature analysis**, and **Google Literature
   Insights**. Use these to have the *text* read and reduced to the measured
   quantity, not to re-rank titles.

Record which interface produced each conclusion, alongside the citation. A
figure that came out of a synthesis interface and a figure read off the paper's
own table are not the same evidence, and the register has to be able to tell
them apart.

Rung 1 is not optional before rungs 2 and 3, and it changes what "blocked"
means: a paper whose body returned chunks is not access-blocked, and a paper
that returned none has not been shown to be — the ladder is about the *quantity*
remaining unsettled, not about the paper being unreachable.

**A blocked read is not a null result.** "No paper measures this" is a finding
about the literature and is the honest route to a declared Grade C. "The paper
that measures this could not be opened" is a finding about our access: it blocks
the grade, and it must be escalated up the ladder or reported as still blocked.
Collapsing the second into the first manufactures a Grade C that the literature
does not support.

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
empty is the failure mode this skill exists to prevent — and so is filing an
unread paper as a null result, which is the separate case above.

This holds for chunk retrieval too, and is where it is easiest to get wrong: a
quantity missing from the excerpts a query returned is `?nr`, not absent from the
paper, and not absent from the literature. Say which of the three you have
actually established.
