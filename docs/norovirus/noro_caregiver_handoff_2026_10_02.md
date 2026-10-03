# Norovirus caregiver handoff — 2026-10-02

Handoff record: reports no new numbers. Every figure is quoted from a
committed artifact with the SHA that measured it. Written at the close
of the NORO-CAREGIVER-01 implementation stage; the session that
follows should start by reading `docs/norovirus/norovirus_open_ledger.md`
§1 (every dose figure is void pending a refit) and the two ledgers below.

## 1. The question

Does the **party-mediated caregiver mechanism** — a responder drawn
from a travelling party (or a steward, per the VSP immediate-cleanup
mandate) who moves *toward* an emesis event, takes a high-dose cleanup
exposure, and in doing so discovers the case — move the two broken
conversion links of the observation funnel (infected→symptomatic,
eligible→reported) on dose physics and discovery rather than on fitted
constants? Success looks like the CHANNEL-03 rungs rising on the same
scored-voyage harness without any constant having been chosen to make
them rise. Failure looks like the funnel flat or the caregiver share of
transmissions exceeding its plausible bound (>10% is the declared
report-immediately trigger in the design).

## 2. Current hypothesis

The anchor gap is a shared conversion defect, and the caregiver event
is one mechanism that plausibly feeds both broken links: the cleanup
touch is among the highest-dose events the engine can express (the
dose-conditional Korkin/Teunis Hill pair already shipped), and the same
event is the discovery moment the self-report-only channel lacks. The
mechanism is implemented and default-ON; whether it moves the funnel
enough to reach the anchors is **unmeasured** — that is the next
campaign, not a conclusion.

## 3. Evidence for

- **Conversion gap is measured, not asserted** — NORO-CHANNEL-03
  (`docs/norovirus/noro_channel_03_readout.md`, `docs/ledger/
  NORO-CHANNEL-03.md`, measured at `d6c51c14`): symptomatic-course/
  infected 0.170–0.413 vs declared 0.6 on all 9 cells;
  eligible→reported 0.168–0.321 vs declared 0.4 on 8/9; the
  symptomatic→eligible rung intact at ~1.0.
- **Outbreaks are real but clinically invisible** — NORO-OUTBREAK-01
  (`docs/ledger/NORO-OUTBREAK-01.md`, measured at `bc4de6f5` +
  `d6c51c14`): takeoff 53–100% across three classes; **zero postings on
  4,000 spirit voyages** vs ~17–22 expected under the A9 posting rate.
- **The dose→symptom channel exists** — presentation is dose-conditional
  under the Korkin/Teunis Hill pair (Korkin 2008 / Teunis 2008, register
  §3.1); a cleanup bolus sits orders of magnitude above a handrail
  pickup, so it lands on the saturating part of the draw.
- **Cleanup contact intensity is sourced** — Overbey et al. 2021
  (doi:10.1016/j.jhin.2021.08.006): 9–34 fomite contacts per soiled-room
  entry, Grade B, shipped as `CAREGIVER_CLEANUP_CONTACTS`.
- **Mechanism engages end-to-end (1-seed smoke, unmeasured)** — spirit
  s8000 reported/eligible = 0.632 vs the 0.168–0.321 CHANNEL-03 band.
  One seed: directional only, registered here so the successor does not
  re-derive it.

## 4. Evidence against / unexplained

- Party-size distribution is **∅ published** — the dealt
  {1:.75, 2:.18, 3:.05, 4:.02} is a declaration bounded only by
  occupancy arithmetic (105–108.5% lower-berth occupancy ⇒ ~5–17% of
  cabins hold 3+); a real industry party-size source would tighten it.
- Cleanup-contact source is hospital environmental-service workers, not
  cruise stewards or family members — a proxy by setting, flagged in the
  register row.
- Whether the caregiver dose reaches the saturating part of the Hill
  pair depends on the emesis bolus magnitude, which inherits the
  withdrawn-dose caveat: magnitudes are recorded, absolute levels are
  not anchored.

## 5. PRs landed this session

1. #829 — NORO-OUTBREAK-01 declared (manifest, readout, overlay image)
2. #844 — NORO-OUTBREAK-01 measured (12,000 voyages, all anchors fail)
3. #848 — spirit extension + NORO-CHANNEL-03 declared
4. #854 — spirit extension + CHANNEL-03 measured (shared conversion gap)
5. **#855 (open) — NORO-CAREGIVER-01 implemented, default-ON**
   (`transmission.caregiver.mode`; `off` is the labelled pre-change
   baseline and draws no RNG)

## 6. Running jobs

None. All Batch arrays are complete (`campaign/noro_outbreak_01/`,
`campaign/noro_channel_03/` — merged SHAs `bc4de6f5` / `d6c51c14`). No
next campaign has been submitted: the caregiver funnel re-measurement
awaits the #855 merge SHA for its image.

## 7. What is now void

Nothing re-measured. Once #855 merges, **any funnel figure quoted at
"current defaults" changes meaning**: CHANNEL-03's rungs (`d6c51c14`)
become the labelled pre-caregiver baseline (reproducible via
`transmission.caregiver.mode: off`), and the next measurement is a
new-stack number, not a bug-for-bug continuation. `docs/norovirus/
norovirus_open_ledger.md` §1 still governs: all dose magnitudes are void
pending refit; ranges and tails only.

## 8. The single open decision

**Run the funnel re-measurement canary.** Once #855 merges: build the
campaign image at the merge SHA, run ≥20 seeds at the expedition
scr-mid cell (the CHANNEL-03 canary cell, so the rungs pair against a
measured baseline), then **stop and report** per the campaign gate —
the user decides whether the full 180-run funnel re-measurement and the
anchor re-score proceed. The admissibility gates are frozen in
`docs/norovirus/noro_caregiver_01_design.md` §Admissibility; the
report-immediately triggers (caregiver share >10%, zero responses at
0.9, caregiver report on a non-emetic course) stand.

Operational loose end (not a modeling decision): ~64 GB of pre-stack
campaign prefixes await deletion under `campaign/`; the picard role has
no `s3:DeleteObject` — either Benjamin runs the provided `aws s3 rm`
command under his own profile or grants the role scoped delete on
`campaign/*`.

## 9. Do not reopen

- No fitting any constant to VSP/Park/attack-rate anchors — including
  the five new caregiver constants (frozen intervals + grades in
  register §3.1; the Grade C declared ones stay declared, not "tuned").
- `mode: off` must remain bitwise-identical to the pre-mechanism tree —
  it returns before any RNG draw and `assign_parties` draws no RNG; do
  not add a draw to either path.
- Caregiver dose flows through the standard accumulators under route
  `caregiver`; do not bypass `_resolve_pathogen_challenge` with a
  direct infection call (the susceptibility, secretor and strain
  bookkeeping live there).
- The stamp is once-per-illness and must keep clearing on report or
  symptom end (`_consume_caregiver_stamps`) — a stamp that survives into
  a later illness fabricates a report.
