---
name: searching-literature-evidence
description: Search the peer-reviewed literature with the Consensus MCP server to source a model constant, check an anchor, or find measurements of a mechanism — constants, rates, fractions, kernels and anchors in the transmission and natural-history model, and how to escalate when the abstract will not settle a definition. Use whenever a constant, rate, fraction, kernel or anchor needs a citation, or when asked what the literature says about a mechanism. Pairs with the org-level consensus-literature-retrieval skill, which owns retrieval mechanics.
---

# Searching the Literature (Consensus MCP)

## Retrieval mechanics are in the org-level skill

Load `consensus-literature-retrieval` (`~/.agents/skills/`) before searching. It
owns the tool surface, `include_full_text_chunks: true` — which is mandatory and
returns Results, Methods and tables, including for paywalled articles — query
construction, filter behaviour, result handling, and recording which section of
the paper a number was read from.

This skill is the other half: what needs sourcing in this transmission and
natural-history model, and what a hit is allowed to become here.

## Query construction

- Good: `surface touch frequency shared surfaces per hour office video observation`
- Weak: `how often do people touch things`

## Filter discipline

Filters that are specifically wrong for this repo's literature:

- `medical_mode` — clinical-evidence questions (drug efficacy, guidelines), not
  behavioural or environmental measurements. It restricts to ~8M top medical
  documents and will drop the built-environment, food-microbiology and
  indoor-air journals that most fomite and shedding constants come from.
- `human` drops exactly the in-vitro transfer and surrogate work (MNV1, Phi6,
  MS2) that quantifies fomite and hand routes.

## When the abstract is not enough

This is the dominant failure mode, not a rare one: a review of eight recent
literature-sourcing sessions found six of them stalled for want of full text.
Abstracts settle magnitudes; they almost never settle a **definition** — units
(infectivity vs RNA), endpoint, denominator, sampling times, matrix — and those
are what decides whether a number can be adopted at all.

So a paywall is not the end of the search. The ladder, in order:

1. `consensus` MCP `search` with `include_full_text_chunks` — ranking, DOI,
   abstract, and query-relevant excerpts of the body, tables included. Always
   first, and often enough to settle the definition on its own. The chunks are
   query-relevant rather than exhaustive, so silence there is *not retrieved*,
   not *not measured*.
2. The DOI itself, then the open routes for the same article: PubMed Central,
   Europe PMC, the publisher's own HTML, an author or institutional copy.
   Supplementary tables live here and are frequently where the time-resolved
   measurements are.
3. A richer interface, when 1 and 2 cannot settle the definition. Available to
   this project, by asking rather than by a scripted call: **Consensus Pro
   reports**, **edison/aviary literature analysis**, and **Google Literature
   Insights**. Use these to have the *text* read and reduced to the measured
   quantity, not to re-rank titles.

Record which interface produced each conclusion, alongside the citation. A
figure that came out of a synthesis interface and a figure read off the paper's
own table are not the same evidence, and the register has to be able to tell
them apart.

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

Report a null result as a result. "No paper measures total high-touch surface
area per cabin in m²" is a finding worth recording, and is the honest route to a
declared Grade C. Inventing a plausible number because the search came back
empty is the failure mode this skill exists to prevent — and so is filing an
unread paper as a null result, which is the separate case above.
