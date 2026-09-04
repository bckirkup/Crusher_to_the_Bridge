---
name: searching-literature-evidence
description: Search the peer-reviewed literature with the Consensus MCP server to source a model constant, check an anchor, or find measurements of a mechanism — constants, rates, fractions, kernels and anchors in the transmission and natural-history model. Use whenever a constant, rate, fraction, kernel or anchor needs a citation, or when asked what the literature says about a mechanism. Pairs with the org-level consensus-literature-retrieval skill, which owns retrieval mechanics.
---

# Searching the Literature (Consensus MCP)

## Retrieval mechanics are in the org-level skill

Load `consensus-literature-retrieval` (`~/.agents/skills/`) before searching. It
owns the tool surface, `include_full_text_chunks: true` — which is mandatory and
returns Results, Methods and tables, including for paywalled articles — query
construction, filter behaviour, result handling, and recording which section of
the paper a number was read from.

This skill is the other half: what needs sourcing in [this transmission and natural-history model], and what a hit is
allowed to become here.

## Query construction

- Good: `surface touch frequency shared surfaces per hour office video observation` (also: `fomite contact rate shared surface touches per hour`)

## Filter discipline

- `medical_mode` — clinical-evidence questions (drug efficacy, guidelines), not
  behavioural or environmental measurements. It restricts to ~8M top medical
  documents and will drop the built-environment, food-microbiology and
  indoor-air journals that most fomite and shedding constants come from.

- `human` drops exactly the in-vitro transfer and surrogate work (MNV1, Phi6,
  MS2) that quantifies fomite and hand routes.

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
empty is the failure mode this skill exists to prevent.
