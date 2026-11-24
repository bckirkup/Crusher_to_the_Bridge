# CARRIER-DISTRIBUTE (D3″) — where the mouthed dose lands

Status: **implemented as selectable arms; not adopted, unmeasured**.
`hand_redeposit_mode: "carriers"` was already shipped
(NORO-HAND-CASCADE-01a); `hand_donor_mode` is now shipped beside it
(`"shedders_only"` default), and `campaigns/noro/noro_carrier_distribute_01/`
registers the R/R+D factorial of §6. Both defaults are unchanged and
bit-identical; a run without the new keys reproduces the pre-change
tree. Moved from `docs/proposals/` on implementation per the docs filing
rule.

## 0. Settled inputs (quoted, not re-derived)

- **`NORO-TOUCH-PATCH-01`** (`docs/ledger/NORO-TOUCH-PATCH-01.md`): encounters
  and delivery fixed — instance touches deliver ordinary-fomite mass to hands;
  2/18 cold cells ≥1.1, no ignition.
- **`NORO-EXTERNAL-SEQUESTER-01`** (`docs/ledger/NORO-EXTERNAL-SEQUESTER-01.md`,
  measured at `f357dd16`, seeds 8000–8019 `classic_cruise_1900`, 288 epochs,
  `item_instances`, `discrete`): retention fired on every cell; cold-cell
  mouth fraction of delivered rose 2.96% → 10.68% (S → S+R); gate missed —
  S 3/18, S+R 1/18. Frozen rule moved the bound to "mouth-touch structure or
  the challenge".
- **Dose-landing decomposition (this readout, S+R artifacts):** on seed 8016
  the partition books `sink_mouth_*` = 71.7k GEC, of which ~21k was credited
  raw on susceptibles — **~70% of mouthed mass is swallowed by
  already-infected carriers** and never becomes a challenge (dead mass;
  biologically real, not a defect). The credited remainder passes
  `susceptibility_multiplier` + the class gate to ~6k effective, and **72% of
  it sits on a single host** (1449: secretor-negative,
  `dose_response_susceptibility` = 6.9e-9 → hazard_sum 3e-5). The second
  host (205, s = 3.2e-16) brings the top-2 share to ~90%. Naive hazard 0.568,
  1 secondary.
- **Same decomposition on a hot cell:** seed 8000 credited 4.26M GEC raw
  across ≥36 hosts (90% mass on 36 hosts, max share 6%) → naive hazard 33.7
  → 36 secondaries. The cold/hot contrast is ~200× in credited volume *and*
  ~18× in the count of hosts carrying 90% of dose (both cohorts challenge
  ~1.5k hosts; the difference is concentration, not reach).
- **Susceptibility wiring verified:** the 1521 challenged hosts on 8016 drew
  `dose_response_susceptibility` with mean 0.00338 ≈
  E[Beta(0.111, 32.81)] = 0.00337 and matching quantiles — the draw is the
  declared Beta, not a wiring defect (the DOSE-FRAIL-01 class of bug is
  ruled out for this path).
- **`NORO-DOSE-LEDGER-01`:** realized secondaries ≈ summed naive hazard
  (182/184) — the challenge resolves booked hazard faithfully; it is
  measured not-binding.
- **RNG caveat (NORO-POOL-PICKUP-01):** arms adding draws perturb the shared
  stream; per-seed arm contrasts are not paired realizations — pooled
  readouts are the unit of evidence.
- **`hand_redeposit_mode: "carriers"`** is shipped
  (`_get_hand_depositors` admits non-shedder hosts with
  `pickup_gate_open(hand_load)` — a whole-copy load). Prior measurement:
  `fl_exp_12d_sens_p06_paxv` (mixed: 8073 +22, 8038 −6 infected) and a
  two-seed witness on this hull's *held* seeds
  (`NORO-HAND-REDEPOSIT-STREAM-01-WITNESS`, 8105/8106: carrier
  surface + food deposits nonzero, dose +29.7k GEC on 8105 for +1
  infected) — but never on the 8000–8019 cohort and never on the
  sequester stack, where carriers now retain mass for days.

## 1. What is wrong with the present structure

Mouth dose reaches hands and converts honestly — but *who holds the mass*
decides the cell. Three measured facts on the cold cells:

1. **Dead-mouth share.** ~70% of `sink_mouth_*` is swallowed by hosts that
   can no longer be challenged (already infected; superinfection is closed
   without a strain registry). Correct biology, wasted dose.
2. **Concentration lottery.** The susceptible-reached remainder concentrates
   on 1–2 hosts (72–90% share), so whether a cold cell ignites is decided by
   one or two `Beta(0.111, 32.81)` draws — a per-cell lottery, not a
   population mean.
3. **Survivorship enrichment.** The dominant carriers are enriched for
   hard-to-infect hosts (secretor-negative, low draws): infectable carriers
   leave the pool early; the ones that keep accumulating are the ones the
   challenge cannot convert. On 8016, ~20% of crediting epochs were on
   secretor-negative hosts and both dominant carriers drew s ≈ 1e-9–1e-16.

Mass stays concentrated because **a non-shedding carrier is a dead end on
every outbound route**: under `shedders_only` it cannot re-deposit to a
surface or a food pool (`_get_hand_depositors` → `_get_shedders`), and it
cannot donate hand→hand (`_direct_contact_unit` sources its donor set from
`_get_shedders`; `_hand_contact_transfers` reads the donor's hand load and
never the shedding value — the gate is the only thing that truncates the
route). Retention now holds mass on carriers for days, but the shipped
gates keep it on the first hands that touched it.

## 2. Design principle — redistribution, not magnitude

Nothing about the ~1%/h capture or the Beta draw may move (constants are
frozen). The lever that does not touch a constant is **who can give the
mass away**: let a loaded carrier deposit to surfaces/food and donate in
contact, so retained mass redistributes to *fresh susceptible hands* —
breadth (many challenged hosts instead of one lottery host) plus the food
pool's bolus-to-many-diners amplifier, the same shape hot cells already
show. This is the parked D1′ mechanism, reactivated by measurement: the
EXTERNAL-SEQUESTER verdict left "where dose lands" as the bound and this
arm is the only shipped-selector lever on it.

## 3. Mechanism

Two selectors, both default-off and bit-identical at defaults:

- `hand_redeposit_mode: "carriers"` — **shipped, config-only.** Under
  `carriers`, `_get_hand_depositors` already admits non-shedder hosts whose
  `hand_load` passes `pickup_gate_open` (≥ `SURFACE_PICKUP_MIN_GEC`), so
  they deposit into zone surface pools and zone food pools
  (`_food_deposits`) exactly like shedders do.
- `hand_donor_mode: "carriers"` — **shipped selector** (`"shedders_only"`
  default). Under `carriers`, the direct-contact donor pool in
  `_direct_contact_unit` is shedders ∪ carriers (same `pickup_gate_open`
  gate, each carrier contributing `(agent, 0.0)` as `_get_hand_depositors`
  already builds). `_hand_contact_transfers` debits `donor.
  hand_load_by_pathogen` and never uses the shedding value, so the existing
  code path moves mass unchanged once the carrier is sampled.
  Shedder-keyed semantics stay shedder-true: `total_shedding`, `zone_mix`
  attribution, and the confinement shedder set keep the real shedder list;
  only the *donor sampling pool* widens. The unit's early exit
  `if not shedders` becomes `if not donors` under the arm so a
  carrier-only unit still runs.

## 4. Why this and not the alternatives

- **vs the challenge:** measured not-binding — realized secondaries track
  summed naive hazard (182/184) and the Beta draw verifies against its
  declared parameters.
- **vs mouth-touch structure:** `contacts × f × e` is a sourced constants
  triple; moving it is constant tuning against the outcome — forbidden.
- **vs the dead-mouth leak:** ~70% swallowed by infected carriers is
  biology, not a defect — restricting retention to susceptibles would let
  the same mass inactivate instead of mouthing, which reduces dose on both
  sides of the ledger.
- **vs doing nothing:** the measured alternative is that cold-cell take-off
  is a tail event gated by one host's draw — a publishable bound, but the
  campaign should first test the only remaining structural lever.

## 5. What the arm can change (bound, not result)

`carriers` redeposit moves each loaded carrier's mass into pools other
hosts sample, and donor mode moves it directly: expected effect is
*breadth* (hosts_for_90pct from ~2 toward the hot-cell ~36) and de-
lotteried draws, plus food-pool bursts where a carrier is a food handler.
Whether that lifts ≥9/18 cold cells over 1.1 is exactly what the campaign
measures; mean Σhazard is ~invariant under redistribution in the linear
regime, so the spec claims a structural change, not a number.

## 6. Frozen criteria (for `noro_carrier_distribute_01`, written before any cell runs)

A two-arm factorial on the same 20-cell cohort (seeds 8000–8019,
`classic_cruise_1900`, 288 epochs, `norwalk_gi`) stacked on the measured
S+R stack (`item_instances`, `hand_sequester_fill: "any_load"`,
`hand_residual_mouthing: "per_epoch"`, `contamination_solver: "discrete"`)
— 40 cells:

- **Arm R (redeposit):** `hand_redeposit_mode: "carriers"`,
  `hand_donor_mode: "shedders_only"` — isolates the surface+food
  redistribution the shipped selector already provides.
- **Arm R+D (redeposit + donation):** `hand_redeposit_mode: "carriers"`,
  `hand_donor_mode: "carriers"` — adds carrier→hand donation.

8105/8106 stay held for the full-campaign decision.

Audit invariants — a violation is an instrument defect, not a null result:

- `len(epoch_mass_ledger) == 288` per cell; the four counter
  reconciliations within 1e-9 relative; the hand-loss partition
  `sources = sinks + residual` closes ≤1e-9 relative, with
  `internal_host_transfer*` and `sink_redeposited` witnessing the
  redistributed mass.
- **Off arm = shipped baseline, enforced by the bit-identity gate** — both
  selectors at defaults reproduce the pre-change tree on one seed.
- **Carrier provenance witness:** every non-shedder that deposits or
  donates must have a witnessed earlier positive accessible acquisition —
  the same provenance convention as EXTERNAL-SEQUESTER.
- Resolved stamps per cell: `hand_redeposit_mode_resolved` and
  `hand_donor_mode_resolved` (a dropped override is a witnessed fact).

Reported, never selected on, per cell:

- the dose-landing decomposition — `hosts_credited_any_dose`,
  `max_host_share`, `hosts_for_50/90/95/99pct`, dead-mouth share
  (1 − `credited_raw` / `sink_mouth_*`), raw→scaled ratio;
- carrier activity — count of non-shedder depositors/donors and the mass
  they moved;
- Σhazard, secondaries, take-off; wall-clock multiplier vs arm S+R.

Selection / decision rules (frozen Σhazard ≥ 1.1 gate, 18 cold cells per
arm):

- **Arm R+D ignites, arm R does not:** hand→hand donation was the missing
  hop — promotion to default-on is a *separate* change and decision.
- **Arm R ignites:** deposit-route redistribution was sufficient —
  promotion is a separate change and decision.
- **Breadth rises materially (hosts_for_90pct ≥ ~8 median) but neither
  ignites:** dose landing is fixed and aggregate delivered volume is still
  short — the bound becomes the measured multiplier to hot-cell credited
  mass (~200×); report, change nothing else.
- **Breadth flat on both arms:** carriers never deposited/donated —
  the provenance witness decides whether the mechanism even fired; the
  carriers mechanism is measured bounded; report, change nothing else.

## 7. Out of scope / follow-ups this spec does not authorize

- Any change to a shipped constant, draw family, band or rate (mouth
  contacts, transfer fractions, the Beta pair, the sequester band, pickup
  floor).
- Promotion of `hand_redeposit_mode`/`hand_donor_mode` to default — that
  is a separate decision the campaign informs.
- Schedule/rhythm (D3′), secretor-gate semantics, challenge-model changes,
  strain/superinfection — all parked or measured-not-binding.
- Campaign submission — gated on user approval of this design, then the
  usual preflight (smoke → dry-run count → pinned digest → canary ≥20
  seeds → stop and report).
