# Devin Task: PRJ Configuration Fixes (v2 — PRJ as Source of Truth)

> **Status:** Implemented (merged). Living Contam guidance:
> [CONTAM_INTEROP.md](CONTAM_INTEROP.md) and [CONTAM_PRJ_AUDIT.md](CONTAM_PRJ_AUDIT.md).

## Direction of Truth

```
ContamW 3.4 .prj  ←── SOURCE OF TRUTH (airflow physics)
    ├─ Path A: ContamX ──► airflow field ──► Crusher mass balance
    └─ Path B: --simplify ──► spatial_layout.json + air_flow_paths.json
                                └──► native prescribed-flow engine

Zone naming: Crusher JSON names ARE the source for human-readable IDs.
             PRJ names are abbreviations of those IDs (≤15 chars).
             path_map.json bridges the two.
```

Going forward, the PRJ files are the primary artifacts. The JSON platform
files are DERIVED from them (via `--simplify`). The generator
(`scripts/generate_platform_contam_prj.py`) is used only for the initial
fiction bootstrap; after that, PRJs are edited directly.

The exception is **zone naming**: Crusher's agent model uses the full
human-readable JSON names. The PRJ holds abbreviated versions. The
`path_map.json` maps between them.

## 1. Zone Name Abbreviation Strategy

### Problem

109 of 129 mega cruise JSON zone names exceed ContamW's 15-char limit.
Current hard truncation + collision suffixes produce unreadable PRJ names.

### Fix

**Rename the JSON zone IDs** to be systematic and ≤15 chars. These names
propagate everywhere: JSON configs, Python code, PRJ files, path maps,
dashboard, tests. Do it once, do it right.

Abbreviation rules:
- `Pax_Corridor` → `PC`, `Crew_Corridor` → `CC`
- `Port` → `P`, `Stbd` → `S`, `Central` → `C`
- `Fwd` → `F`, `Mid` → `M`, `Aft` → `A`
- `Restaurant` → `Rest`, `Engineering` → `Eng`
- `Entertainment` → `Ent`, `Cartography` → `Carto`
- Drop `_Block`, `_Room`, `_Complex` when the parent word is unambiguous
- Use `_L`/`_U` for Lower/Upper, `_A`/`_B` for variants

| Current name | New name | Chars |
|-------------|----------|-------|
| `Pax_Corridor_D6_Port_Fwd` | `PC_D6_P_F` | 10 |
| `Pax_Corridor_D14_Central_Mid` | `PC_D14_C_M` | 11 |
| `Crew_Corridor_D3_Aft` | `CC_D3_A` | 8 |
| `Main_Dining_Room_Lower` | `MainDining_L` | 13 |
| `Main_Dining_Room_Upper` | `MainDining_U` | 13 |
| `Specialty_Restaurant_Block_A` | `SpecRest_A` | 10 |
| `Central_Park_Open_Atrium` | `CentralPark` | 11 |
| `Shopping_Retail_Block` | `ShopRetail` | 10 |
| `Spa_Fitness_Complex` | `SpaFitness` | 10 |
| `Stellar_Cartography` | `StellarCarto` | 12 |
| `Main_Engineering` | `MainEng` | 7 |
| `Engine_Control_Room` | `EngControl` | 10 |
| `Windjammer_Buffet` | `Windjammer` | 10 |
| `Transporter_Room` | `Transporter` | 11 |
| `Security_Station` | `Security` | 8 |
| `Officer_Quarters` | `OfficerQtrs` | 12 |
| `Buffet_Galley_Upper` | `BuffetGal_U` | 11 |
| `Waste_Treatment_Plant` | `WasteTreat` | 10 |

Enterprise zones follow the same rules. Destroyer zones already fit.

After renaming, ALL JSON zone names should be ≤15 chars. The
`_unique_contam_name` function becomes a no-op safety net (truncation
should never be needed).

### Improve `_unique_contam_name` as fallback

Add an abbreviation pass before truncation so any future long names
degrade gracefully:

```python
_WORD_ABBREVS = {
    "Corridor": "Cor", "Restaurant": "Rest", "Engineering": "Eng",
    "Accommodation": "Accom", "Entertainment": "Ent",
    "Cartography": "Carto", "Treatment": "Treat",
    "Quarters": "Qtrs", "Control": "Ctrl",
}

def _abbreviate_for_contam(name: str, max_len: int = 15) -> str:
    if len(name) <= max_len:
        return name
    # Apply word abbreviations
    for long, short in _WORD_ABBREVS.items():
        if len(name) <= max_len:
            break
        name = name.replace(long, short)
    # Drop underscores if still too long
    if len(name) > max_len:
        parts = name.split("_")
        name = "".join(parts)
    return name[:max_len]
```

### Files to modify

Every file that references a zone ID by string. The migration:

1. Build a `{old_name: new_name}` dict for each platform
2. Apply to `spatial_layout.json`, `air_flow_paths.json`
3. Apply to `contam/hobbyist_overrides.json` (zone_annotations,
   wall_azimuth_deg, etc.)
4. Grep Python source for old names in string literals
5. Update test fixtures
6. Regenerate PRJ files (one final time from JSON for the bootstrap)
7. Run `--simplify` on the regenerated PRJs to verify round-trip
8. The regenerated PRJs become the new source of truth

---

## 2. Per-AHU Outdoor Air Fraction in PRJ

### Problem

The `OAFracW` schedule is hardcoded to `fo=0.2`. Per-AHU overrides in
`hobbyist_overrides.json` are used for the native engine's recirculation
calculation but NOT wired into the PRJ's Contam schedules.

| Platform | AHU | Override OA | PRJ schedule |
|----------|-----|-------------|-------------|
| Constitution | zone_saucer_ops | 0.35 | OAFracW fo=0.2 |
| Galaxy | zone_saucer_medical | 0.40 | OAFracW fo=0.2 |
| Mega | AHU_Dedicated_Medical | 0.40 | OAFracW fo=0.2 |
| Mega | AHU_Pax_Deck_* (9 AHUs) | 0.15 | OAFracW fo=0.2 |

This means ContamX runs with wrong OA fractions for medical and pax spaces.

### Fix

For each AHU with a non-default OA fraction, emit a dedicated day/week
schedule pair and wire it onto that AHU's recirculation path.

```
! Day schedule
  N    2    0    1    0 OAFr_Medical
Medical OA fraction (40%)
 00:00:00 0.4
 24:00:00 0.4
! Week schedule
  N    1    0 OAFr_MedW
 N N N N N N N N N N N N
```

The AHS recirculation Fahs path then references the AHU-specific week
schedule number instead of the global OAFracW.

**Edit directly in the PRJ files** after the final generator run, or
implement in the generator for the fiction bootstrap.

### Files to modify

- `tools/contamw34_prj.py` — AHS schedule emission and path wiring
- `tools/contam_hobbyist.py` — verify `oa_fraction_for_hvac()` reads overrides

---

## 3. Zone Temperatures from Deck Offsets

### Problem

Mega cruise engine rooms are 293.15 K (20°C) despite override
`deck_temp_offset_K: {"0_Engine": 5.0, "1_Engine": 4.0}`.

The destroyer works correctly (engine at 298.15 K).

### Fix

Verify the deck name key matching between `zone.deck` in the JSON and
`deck_temp_offset_K` keys in the override file. The destroyer uses simple
names (`lower`), the mega cruise uses compound names (`0_Engine`).
Ensure `_hobby.deck_temp_k()` matches on the JSON deck value.

### Files to modify

- `tools/contam_hobbyist.py` — `deck_temp_k()` key matching logic
- Verify with a test that prints deck→temp for all mega cruise zones

---

## 4. Passive Cross-Zone Links as Orifices

### Problem

All cross-zone links are exported as `fan_cvf` (forced prescribed flow),
including passive connections like ladder wells and stairwells. These should
respond to pressure differences from temperature gradients and wind.

### Fix

For links with `is_hvac_ducted: false`, emit a `plr_orfc` (orifice) element
sized to produce the design flow at a reference ΔP of 1 Pa:

```
A = Q / (Cd × sqrt(2 × ΔP / ρ))
```

With Cd=0.6, ρ=1.2 kg/m³, ΔP=1 Pa:

| Design flow | Orifice area |
|-------------|-------------|
| 20 m³/h | 0.0023 m² |
| 50 m³/h | 0.0058 m² |
| 80 m³/h | 0.0092 m² |

These are physically plausible for hatched vertical openings.

Assign the appropriate opening schedule (`ShaftOpenW` for shafts,
`HatchOccW` for hatches) based on the link path type.

Keep `fan_cvf` only for `is_hvac_ducted: true` links.

### Files to modify

- `tools/contamw34_prj.py` — cross-zone path emission logic
- `data/contam_hobbyist/orifice_catalog.json` — add `vertical_shaft` entry

---

## Execution Order

1. Zone name rename (§1) — biggest ripple, do first
2. Regenerate PRJs from renamed JSON (final bootstrap)
3. Per-AHU OA (§2) — in generator or direct PRJ edit
4. Zone temperatures (§3) — fix deck_temp_k lookup
5. Passive orifices (§4) — generator change
6. Regenerate all PRJs one last time
7. Run `--simplify` on each PRJ → verify JSON round-trips cleanly
8. The PRJs are now the source of truth; delete or deprecate the generator
9. Run full test suite (~655 tests)
10. Run contam_flow_compare and contam_engine_compare

## Tests

- All zone names in generated PRJs ≤ 15 chars, no collision suffixes needed
- Per-AHU OA schedules appear in PRJ for overridden AHUs
- Engine room temperatures match deck offset overrides
- Passive cross-zone links emit `plr_orfc` not `fan_cvf`
- `--simplify` round-trip preserves zone count, volumes, adjacency

## Non-goals

- Do not change Crusher native engine physics
- Do not add new zones or connections
- Do not attempt professional-grade CONTAM modeling — these remain
  documented fiction twins, but now with physically defensible parameters
