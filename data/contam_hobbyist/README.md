# Contam hobbyist-plus shared pack

JSON templates consumed by `tools/contam_hobbyist.py` and the ContamW 3.4
fiction exporter (`tools/contamw34_prj.py`) when `--hobbyist` is enabled.

| File | Role |
|------|------|
| `orifice_catalog.json` | Adjacency type → `plr_orfc` sizes |
| `wind_profiles.json` | Hull / low-rise Cp vs azimuth |
| `schedule_templates.json` | OAFrac + HvacDuty day/week schedules |
| `filter_presets.json` | MERV/HEPA → Contam `cef` filters |
| `duct_defaults.json` | Darcy trunk leakage spines |
| `species_pack.json` | Air + Virus tracer species |

Per-platform overrides live at `data/platforms/<id>/contam/hobbyist_overrides.json`.
