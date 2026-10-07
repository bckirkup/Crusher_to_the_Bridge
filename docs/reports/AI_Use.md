# Crusher_to_the_Bridge — development & testing retrospective (Jul 3 – Oct 7, 2026)

## Corpus

- **800 PRs** in the window; 789 merged (98.9%), 8 closed-unmerged, 3 open. 696 authored by devin-ai-integration, 104 by bckirkup.
- Velocity: **60 (Jul) → 153 (Aug) → 437 (Sep) → ~21/day (Oct to date)**. Median merge latency ~25 min; 55% merge inside 30 min.
- **2,407 commits** on main, +1.85M / −122k lines. Touches: tests/ 882 commits, docs/ 1,033, engines/ 306, .github/ 20.
- Test suite at HEAD: 339 files, ~5,838 test functions. Guard tests on top: unit-safety, ledger-header schema, law-compliance (`global` ban), image-build-context, schema validation, sanity checker, hull change detectors.
- `docs/ledger/`: 159 entries — 126 measured, 14 open, 12 closed, 5 declared, 2 superseded. The per-file ledger convention itself is a September artifact (all entries dated Sep–Oct).
- Sessions: 386 Devin sessions for this user in the window (all repos). Outcomes: 195 suspended-inactivity, 152 suspended-user_request, 20 exit, 7 out_of_quota, 2 usage_limit, 2 error.
- Nightly (full tier, 3.11+3.12 ×2 shards): failed 5 consecutive nights Sep 25–29, green Oct 2–5, failed Oct 6.

The window splits into three eras: **July** — human-driven platform/ContamX interop work; **August** — transition (Sonar onboarding, first AWS Batch mega campaigns); **Sep–Oct** — the campaign-science era: conditioned arrays, per-pathogen anchors, ledger verdicts, mechanism sweeps.

---

## What was done well

### Development

1. **Measurement-first campaign science.** Admissibility criteria are frozen in the design file before cells run; verdicts are delivered with SHAs and seed sets; six entire mechanism classes were retired by measured verdicts (`geometry_incapable`, `delivery_incapable`, `susceptibility_structure_incapable` — SEED-GEOM-V1, HEAT-V1, SUSCEPT-V1) instead of being tuned indefinitely. That is unusually honest science for a model this size.

2. **Default-ON mechanisms with labelled baselines.** Every shipped mechanism (hygiene_cycle, cabin compartments, near-field two-box, caregiver, droplet field split, defiant escalation) lands default-ON with a named pre-change baseline arm kept for paired attribution. Combined with `config_overrides` arming, any moved golden can be reproduced flag-off — the attribution recipe exists and is used.

3. **Provenance discipline.** Constants carry source + evidence grade at definition; the register blocks fitting to VSP/Park/attack-rate anchors; CONSENSUS tranches document what literature could not license (`∅lit` — a measured null, not an unretrieved claim). Declared-vs-measured-vs-hypothesis is enforced in reports.

4. **The campaign machinery matured into a real platform.** July's ad-hoc submit scripts became `campaigns/<pathogen>/<name>/` grammar + generic `campaign_entrypoint.py` worker + `scripts/campaign` CLI + digest-pinned jobdefs + canary gates + watchdog automations. OUTBREAK-01 ran 12,000 voyages, zero failures, ~3h on Spot; the spirit extension ran 16,000 voyages + 180 funnel dumps, zero failures, per-seed join verified 1:1.

5. **Failure→guard metabolism.** Almost every incident became a durable defense: the OOM'd 1.5GB zip member → streaming ranged reads; the degenerate prevalence-point cells → parameter-not-tag canary witnesses; CloudShell-reaped restores → `nohup`+`ps` verify rule; containerOverrides 8192-char cap → seed_range compression + local `-c` replay before registering. The `.agents/skills` library + AGENTS.md + per-pathogen ledgers now encode most of this.

6. **Ledger as durable handoff.** Session crashes that used to lose 4–7 days of state now lose almost nothing — the committed ledger, not chat, is the handoff medium, and the bounded-research-session rule enforces it.

### Testing

1. **A real tiered CI.** Fast tier (`-m 'not slow'`) sharded by module ×2 interpreters on every push; nightly runs the whole suite including posterior-recovery fits; xdist inside shards; separate Picard/Presidio slice workflow; CodeQL + zizmor + SonarCloud on top.

2. **Structural guard tests that catch the repo's own recurring bug classes.** Unit-safety guard scans all committed JSON for undeclared epoch keys; ledger-header test enforces the measurement format; image-build-context test catches `.dockerignore`/`Dockerfile` drift; law-compliance bans `global`; schema validation gates `data/`.

3. **Golden change-detectors with a real attribution protocol.** Hull cells (diamond_princess, greg_mortimer) pin seeded witness tuples; moves require flag-off reproduction on both interpreters before repinning, and the repin comment records drift-hop vs mechanism-hop separately. This is the right shape for a stochastic model: detect change, attribute it, then accept it.

4. **Determinism used as an oracle.** Seeded runs, byte-identical baselines (wash_reuptake ≡ spike_decay on the covid path — itself a measured structural fact), per-epoch state digests, paired-seed deltas as the primary readout statistic. Inert-arm discrimination (k=0 byte-identical) separates stream-reorder from mechanics.

5. **Instrumented measurement, not vibes.** Packet-arrival probes, observation-channel funnels, per-rung decomposition, caregiver route witnesses, RSS samplers in zips — the model gets instrumented before being asked questions.

6. **Compute routed sensibly.** Voyage-burning tests are opt-in-gated out of CI; heavy cells go to Batch; campaigns are the integration test.

---

## What was done badly

### Development

1. **The golden-pin treadmill.** The hull detector file was touched ~15 times in the last 7 days alone; the nightly failed 5 straight nights (Sep 25–29) to pin drift, then again Oct 6. Every mechanism merge re-rolls the shared RNG stream and moves *every* pathogen's pins — the detector detects change but can't separate it. Two-hop repins (drift + own mechanism) are now routine. The substrate works, but it costs a repin session per mechanism and oscillates red/green continuously.

2. **Cross-pathogen coupling discovered late.** All pathogens board every spec and share delivery machinery: noro's hand rebuild silently cut flu confined-slot dose ~5–8×; PRESENT-SHARE-01 moved covid's replay surface ~−800 onsets. These were found after the fact — the repo had no "which other pathogen's anchors does this move?" step until it became a rule.

3. **Default-ON mid-campaign landings voided frozen invariants.** #936's door-drop factor landed during MEAL-SVC-01 and voided "expected bit-identical" pairing clauses between baseline SHA and campaign SHA. The fix was documented (union the draw, re-bind invariants to what the mechanism doesn't touch) — but the mechanism landed first and the invariant check came second.

4. **Sibling-session collisions.** Parallel sessions on one repo repeatedly collided: parallel duplicate helper modules, the single-line `sonar.coverage.exclusions` merge magnet (last-wins property file, silent failures), branches off stale-HEAD dropping files, a remembered "#850" being a sibling's PR. Coordination rules now exist but were paid for in dead work.

5. **Copy-paste tooling churn.** Readout/probe tools were cloned per-campaign and hit the ≤3% duplication gate at least five times (24.9% on #886) before the `tools/diag` + `covid_screen_readout_common` delegation pattern emerged. New tools still pay a 3–5 gate-failure discovery tax on first PR (coverage exclusion, S3776, S1244, S8707) because most Sonar rules can't be verified locally.

6. **Deploy/submit failure tax.** A 160-child canary died on an ENTRYPOINT argv mismatch; `Ref::` parameters silently dropped re-ran cells 0–57 instead of 58–59; the 8192-char containerOverrides cap burned whole arrays (twice, for two different splice bugs); wrong `cells/` prefix shape left 24 orphan keys with no DeleteObject to clean them; wrong jobdef revs are registered permanently (no deregister permission). Most of these are now in memory/skills — but they were each paid for with a fleet-scale failure.

7. **Process waste around sessions.** 386 sessions with long inactivity suspensions, 7 out_of_quota kills, plus the earlier multi-day crashes that motivated the bounded-session rule. Handed-off human commands repeatedly failed unverified: `--no-paginate` silently returning 1/4 of keys, a pasted space breaking 4,000 restore calls, CloudShell reaping restore loops mid-run.

### Testing

1. **Instrument/harness bugs produced false verdicts.** Audits that read payload keys at the wrong paths made every conforming cell look "violating"; prevalence-point cells silently re-ran the rung midpoint as *tagged-but-degenerate replicates* — every cell in the array was a clone of its neighbors and only a parameter-level canary witness caught it; the A9 either-channel scoring defect faked an engine miss; a `bp`-token filename regex silently dropped whole cell classes from listings. The weakest layer in the stack is the scorer/readout layer, and it only gets one pair of eyes.

2. **Pins are reactive, not preventive.** Slow-tier hull cells only run nightly — an engine-semantics merge is green on PR CI and red the next morning, when the attribution is already stale and the next merge has landed on top (hence two-hop repins). The detector can't run on PR tier as configured, so the feedback loop is ~24h late by construction.

3. **Semantic defects escape the unit layer entirely.** The `symptomatic_fraction` share-vs-hazard defect (re-rolled per day, ~15 draws/course → P(never present) ≈ 0) was only found by a campaign readout decomposing the H2 miss — unit tests pass because the wiring works; the semantics were wrong. Same class: either-channel VSP trigger, either-channel A9, renewal-rung prevalence degeneracy. The suite tests mechanics; the campaigns test meaning — the gap between them is where the worst bugs lived.

4. **Fixture fragility under default-ON drift.** Tests asserting delivery plumbing silently become fixture-invalid when a mechanism lands default-ON (legitimate zero counts read as failures); tiered-sweep invariants on saturated tiers flip under any stream reorder. Each incident was individually attributed, but the class keeps recurring.

5. **Coverage/duplication gates gamed or bypassed.** Exclusion lines are appended at tool-creation (documented convention, but it's still "declare yourself exempt"); a 24.9%-duplication PR merged because SonarCloud wasn't a required check; new test files hit S1244/S9073 repeatedly (~20 fixes post-hoc) because the guards aren't run pre-push by default.

6. **Thin coverage where it's declared thin.** Dashboard/GUI is untested by policy — and the two known dashboard bugs (widget-key crash masking later tabs; mixed-type ArrowInvalid) were both found by use, not tests. Acceptable trade-off, but it's a standing hole, not an accident.

7. **Infra noise.** `setup-uv` flakes kill jobs indiscriminately; the token can't rerun CI (403), so retriggering costs an empty commit; merge-conflicted PRs get zero CI signal (only CodeQL runs) — each of these has produced at least one misdiagnosis.

---

## Net read

The development culture is genuinely good — arguably the strongest part of the operation. Anchors are scored, verdicts are measured with SHAs and seeds, constants aren't tuned to fit, failures turn into guards, and the campaign infrastructure went from shell scripts to a fleet-scale platform in ~6 weeks. The model itself got substantially better: noro went from a withdrawn dose ledger to a link-by-link decomposed conversion gap; covid exhausted whole mechanism classes with quantified bounds rather than infinite tuning.

The weak layer is the **testing/measurement substrate under throughput it wasn't built for**: a single shared RNG stream + golden pins + nightly-only slow tier means the repo oscillates between "green and verified" and "red and attributing"; the scorer/readout harness — the layer that turns simulations into verdicts — has produced multiple false-verdict classes and is the least-tested code in the repo; and merge velocity (~8 PRs/day) means stale pins, stale docs, and stale-session collisions are structural, not incidental.

The three highest-leverage changes, in order:

1. **Decouple the RNG stream per pathogen (or per mechanism block).** Most pin churn, most cross-pathogen silent re-dosing, and most "fixture move" incidents trace back to the shared stream. This is the single structural fix.
2. **Move the hull change detector (or a 1-cell version of it) onto PR tier for engine-semantics diffs.** Catching a pin move at merge time is a 5-minute attribution; catching it the next morning is a two-hop repin.
3. **Treat the scoring/readout harness as first-class code.** It produced the only false *verdicts* in the record. Parameter-level canary witnesses are already the fix — make them mandatory per array, and add witness tests to the harness itself (it currently has fewer tests per line than the engine it scores).
