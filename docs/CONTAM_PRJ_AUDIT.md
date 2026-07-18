# Fiction Contam PRJ Physical Realism Audit

Date: 2026-07-18  
Scope: hobbyist-plus `data/platforms/*/contam/platform.prj` for
`destroyer_baseline`, `enterprise_constitution_tos`, `enterprise_galaxy_tng`,
`mega_cruise_5000`.

**Question:** Are these PRJs accidentally unrealistic, or intentionally
simplified fiction twins of native ACH JSON?

**Short answer:** Internally consistent fiction twins of native ACH/fan
graphs, with **systematic catalog artifacts** (crack-scale “doors”) and a
few export bugs. AHS design flows are sound; adjacency orifices are not.

---

## Cross-cutting

| Item | Finding | Class |
|------|---------|-------|
| AHS `Fahs` | `Q_des = ACH × ΣV`; supply/return per room and recirc `(1−oa)×Q_des` match native HVAC zones | **Sound** |
| Envelope leaks | `0.0001 m²` EnvLeak | **Intentional** (ContamX Jacobian / ambient reference) |
| Named doors / passageways | Catalog areas **0.004–0.02 m²** labeled passageway/doorway/ladder (real doorways ~0.8–2 m², ~**80–200×** undersized). At ΔP=1 Pa, Q≈28 m³/h for 0.01 m² vs thousands for a real door | **Accidental catalog artifact** |
| Cross-zone links | Always exported as `fan_cvf` (incl. native `is_hvac_ducted: false` “passive” ladder wells) | **Questionable** (matches native twin; not orifice physics) |
| `fan_cvf` element syntax | Matches ContamW 3.4 fixture (`28 fan_cvf`, `Q_m3s u_F=3`) | **Likely sound** — confirm with SIM dump |
| `OAFracW` schedule | Always `fo=0.2`; per-AHU `oa_fraction` overrides only rescale recirc Fahs | **Export bug** when override ≠ 0.2 |
| `HvacDuty` | 0.5 / 1.0 / 0.5 on supply/return; sim window often hits night half-duty | Intentional hobbyist |
| `NightSetbk` | Emitted but unwired to paths | Harmless bloat |
| Steady weather | `Ws=0` (wind Cp present but inactive in steady ContamX) | Intentional for steady demos |
| Deck ΔT / stack | Engine decks +4…+6 K; `stackD=1` | Intentional hobbyist |
| Duct spines | Contam-only Darcy trunks; **not** in Crusher Path A Flow0 | Documented; can perturb Contam ΔP without Crusher seeing ducts |
| Orifice catalog dump | Full catalog written even if unused | Bloat |

Orifice estimate: \(Q \approx C_d A \sqrt{2\Delta P/\rho}\) with \(C_d=0.6\),
\(\rho=1.204\) → **≈2784 m³/h per m² at 1 Pa**.

---

## Per platform

### `destroyer_baseline` — **questionable**

| HVAC | ACH | Vol m³ | Q_des m³/h | Fahs/room ≡ m³/h |
|------|-----|--------|------------|------------------|
| zone_upper (Bridge alone) | 6 | 80 | 480 | 480 |
| zone_main | 8 | 225 | 1800 | 600 |
| zone_lower | 10 | 350 | 3500 | 1750 |

- Adjacency: Passage 0.01 / Hatch 0.004 / Ladder 0.006 m² (crack-scale).
- Cross-zone: 11 `fan_cvf` paths; rates = native÷room×room (16.7 / 13.3 / 10 m³/h).
- Bridge is **solo AHS** → no AHS room↔room synth; Bridge→ship coupling must come from fans + orifices.
- Ducts only on `zone_main` / `zone_lower` (override) — OK.
- Compare suite ContamX `n_paths=6` (= AHS2 synth only) implies **fan SIM flows also failed to enter Crusher** — unexpected if `fan_cvf` is healthy; run `contam_flow_compare --run-contamx` to confirm zeros vs path-index join bug.

### `enterprise_constitution_tos` — **questionable**

- AHS Fahs match ACH×V; Bridge shares 3-room AHS → synth coupling exists.
- Ops AHU `oa_fraction=0.35` but `OAFracW` still fo=0.2.
- Orifices crack-scale; passive corridor_ring still `fan_cvf`.

### `enterprise_galaxy_tng` — **questionable**

- AHS Fahs match ACH×V; logistics/drive ACH (12–16) is fiction-aggressive but intentional.
- Medical OA override 0.40 vs schedule fo=0.2.
- Orifices still ≪ doorways even after type remaps (0.011–0.02 m²).

### `mega_cruise_5000` — **questionable** (largest scale artifacts)

- ΣV ≈ 4.0×10⁵ m³; ΣQ_des ≈ 3.7×10⁶ m³/h; engine AHU 20 ACH is extreme fiction.
- **1283** `fan_cvf` paths after combinatorial expansion; cabin_relief 0.002 m² undercuts are OK; promenade/stair still tiny.
- **No** `duct_hvac_ids` filter → ducts on all multi-room AHUs (129 jct / 109 seg).
- Pax OA override 0.15 / medical 0.40 vs schedule fo=0.2.

---

## ContamX→Crusher implications

| Path kind | Contam physics | Crusher fate if ΔP≈0 / SIM≈0 |
|-----------|----------------|------------------------------|
| Envelope orifice | Tiny intentional | Skipped (envelope) |
| Adjacency orifice | Crack-scale “doors” | Often ~0 → **dropped** |
| `fan_cvf` | Forced volume | Should be non-zero; if SIM≈0 → **export/solver/join bug** |
| AHS Fahs | Forced design | Skipped as edges; feed AHS synth |
| Duct spines | Contam-only | Invisible to Crusher Flow0 |

So crack-scale orifices are a real physical-model defect. Forced fans *should* still couple Bridge on destroyer; the compare-suite `n_paths=6` result needs a SIM dump before blaming Contam physics alone.

---

## Recommended fixes (priority)

1. **Resize orifice catalog** for named openings to physically plausible areas (doors ~1 m², stairs/elevators larger; keep cabin_relief / EnvLeak small).
2. **Wire per-AHU `oa_fraction` into Contam schedules** (or drop misleading overrides).
3. **Export passive cross-zone links as orifices** (sized for native m³/h at a reference ΔP), keep `fan_cvf` only when `is_hvac_ducted: true`.
4. **Mega:** restrict `duct_hvac_ids`; reconsider combinatorial fan expansion vs shaft orifices.
5. **Windows:** `contam_flow_compare --run-contamx` on destroyer to verify fan path_nr → Flow0 before calibrating native ACH to ContamX.

None of the four PRJs is “garbage,” and none is a sound as-built Contam ship. They are **native-ACH twins with crack-scale openings** — fix the openings (and OAFrac wiring) before treating ContamX as the physical ground truth for calibration.
