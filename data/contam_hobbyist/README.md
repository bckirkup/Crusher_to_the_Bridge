# Contam hobbyist-plus shared pack

JSON templates consumed by `tools/contam_hobbyist.py` and the ContamW 3.4
fiction exporter (`tools/contamw34_prj.py`) when `--hobbyist` is enabled.

| File | Role |
|------|------|
| `orifice_catalog.json` | Adjacency type → physically sized `plr_orfc` openings |
| `wind_profiles.json` | Hull / low-rise Cp vs azimuth |
| `schedule_templates.json` | OAFrac, HvacDuty, and door/hatch/shaft open–closed day/week schedules |
| `filter_presets.json` | MERV/HEPA → Contam `cef` filters |
| `duct_defaults.json` | Darcy trunk leakage spines |
| `species_pack.json` | Air + Virus tracer species |

Named openings use realistic open areas (doors ~1.8–2 m², stairs/elevators
larger; `cabin_relief` and EnvLeak stay small). Path week schedules modulate
open/closed state with a non-zero undercut residual for ContamX Jacobian
stability.

Per-platform overrides live at `data/platforms/<id>/contam/hobbyist_overrides.json`.
