# Fiction Contam PRJ Physical Realism Audit

Date: 2026-07-18 (updated: realistic openings)  
Scope: hobbyist-plus `data/platforms/*/contam/platform.prj` for
`destroyer_baseline`, `enterprise_constitution_tos`, `enterprise_galaxy_tng`,
`mega_cruise_5000`.

**Question:** Are these PRJs accidentally unrealistic, or intentionally
simplified fiction twins of native ACH JSON?

**Short answer:** Internally consistent fiction twins of native ACH/fan
graphs. **Named openings are now physically sized** with day/night open–closed
schedules. Remaining gaps: passive cross-zone still `fan_cvf`, and
`OAFracW` ignores per-AHU OA overrides. AHS design flows remain sound.

---

## Cross-cutting

| Item | Finding | Class |
|------|---------|-------|
| AHS `Fahs` | `Q_des = ACH × ΣV`; supply/return per room and recirc `(1−oa)×Q_des` match native HVAC zones | **Sound** |
| Envelope leaks | `0.0001 m²` EnvLeak | **Intentional** (ContamX Jacobian / ambient reference) |
| Named doors / passageways | Catalog areas **doorway 1.8 / passageway 2.0 / hatch 0.36 / ladder 0.6–0.8 / stairs–elevators 1.5–4 / open voids 5–10 m²**; `cabin_relief` 0.02 m² | **Sound** (realistic open areas) |
| Opening schedules | `DoorTrafficW` (day ~0.95, night undercut 0.08), `HatchOccasionalW`, `ShaftOpenW` (~0.85–1.0); never zero | **Sound** (wired on adjacency paths) |
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
\(\rho=1.204\) → **≈2784 m³/h per m² at 1 Pa** (≈5.0×10³ m³/h for a 1.8 m² doorway).

---

## Per platform

### `destroyer_baseline` — **improved** (openings fixed)

| HVAC | ACH | Vol m³ | Q_des m³/h | Fahs/room ≡ m³/h |
|------|-----|--------|------------|------------------|
| zone_upper (Bridge alone) | 6 | 80 | 480 | 480 |
| zone_main | 8 | 225 | 1800 | 600 |
| zone_lower | 10 | 350 | 3500 | 1750 |

- Adjacency: Passage 2.0 / Hatch 0.36 / Ladder 0.8 m² with Door/Hatch/Shaft schedules.
- Cross-zone: 11 `fan_cvf` paths; rates = native÷room×room (16.7 / 13.3 / 10 m³/h).
- Bridge is **solo AHS** → no AHS room↔room synth; Bridge→ship coupling must come from fans + orifices.
- Ducts only on `zone_main` / `zone_lower` (override) — OK.
- Prior compare-suite ContamX `n_paths=6` (= AHS2 synth only) was consistent with crack-scale orifices dropping; **re-run** `contam_flow_compare --run-contamx` after this resize.

### `enterprise_constitution_tos` — **improved** (openings); OAFrac still buggy

- AHS Fahs match ACH×V; Bridge shares 3-room AHS → synth coupling exists.
- Ops AHU `oa_fraction=0.35` but `OAFracW` still fo=0.2.
- Orifices now doorway-scale; passive corridor_ring still `fan_cvf`.

### `enterprise_galaxy_tng` — **improved** (openings); OAFrac still buggy

- AHS Fahs match ACH×V; logistics/drive ACH (12–16) is fiction-aggressive but intentional.
- Medical OA override 0.40 vs schedule fo=0.2.
- Typed openings use catalog sizes after type remaps.

### `mega_cruise_5000` — **improved** (openings); scale artifacts remain

- ΣV ≈ 4.0×10⁵ m³; ΣQ_des ≈ 3.7×10⁶ m³/h; engine AHU 20 ACH is extreme fiction.
- **1283** `fan_cvf` paths after combinatorial expansion; cabin_relief 0.02 m² undercuts OK; promenade/stair now full-size.
- **No** `duct_hvac_ids` filter → ducts on all multi-room AHUs (129 jct / 109 seg).
- Pax OA override 0.15 / medical 0.40 vs schedule fo=0.2.

---

## ContamX→Crusher implications

| Path kind | Contam physics | Crusher fate if ΔP≈0 / SIM≈0 |
|-----------|----------------|------------------------------|
| Envelope orifice | Tiny intentional | Skipped (envelope) |
| Adjacency orifice | Full-size doors + schedules | Should carry substantial Q when ΔP≠0 |
| `fan_cvf` | Forced volume | Should be non-zero; if SIM≈0 → **export/solver/join bug** |
| AHS Fahs | Forced design | Skipped as edges; feed AHS synth |
| Duct spines | Contam-only | Invisible to Crusher Flow0 |

Crack-scale openings are fixed. Forced fans *should* still couple Bridge on destroyer; confirm with `contam_flow_compare --run-contamx` + SIM dump before calibrating native ACH to ContamX.

---

## Remaining fixes (priority)

1. ~~**Resize orifice catalog**~~ — done (this change).
2. **Wire per-AHU `oa_fraction` into Contam schedules** (or drop misleading overrides).
3. **Export passive cross-zone links as orifices** (sized for native m³/h at a reference ΔP), keep `fan_cvf` only when `is_hvac_ducted: true`.
4. **Mega:** restrict `duct_hvac_ids`; reconsider combinatorial fan expansion vs shaft orifices.
5. **Windows:** `contam_flow_compare --run-contamx` on destroyer to verify fan/orifice path_nr → Flow0 before calibrating native ACH to ContamX.

The four PRJs remain fiction ACH twins, now with **physically plausible openings** — fix OAFrac wiring and passive `fan_cvf` next before treating ContamX as the sole physical ground truth for calibration.
