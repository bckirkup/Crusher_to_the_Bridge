# ContamW handoff — `antietam_cvs36`

This ContamW **3.4** project is a **Target B starter** from naval general
arrangements via `tools.ship_blueprint_import.author_contam`.

It is meant to **run ContamX Path A** in Crusher-to-the-Bridge and to be
**opened in ContamW** so HVAC engineers can finish work that is **not on the
GA drawings**.

## Already drafted (from GA import)

- Contam **levels / zones** with volume, floor area, ceiling height, elevation
- SketchPad-ish display coordinates from zone overlays
- **61** typed `plr_orfc` openings (doors / hatches / ladders) —
  see `openings_draft.json`
- **10** starter **AHS** branches from HVAC hints (ACH → Fahs)
- Cross-zone ladder/fan links from the synthesized airflow graph
- `path_map.json` for ContamX ↔ Crusher alignment

## Engineer handwork (Target C — not on GAs)

1. Confirm / edit opening areas and schedules (`openings_draft.json` checklist)
2. Fiction Darcy duct spines were **omitted** (naval GA default). Author real ducts / terminals in ContamW from HVAC drawings.
3. Fan curves, damper schedules, measured leakage, NBC filtration as Contam elements
4. Weather / wind as required for the analysis window
5. Re-export or keep editing this `.prj`; Path B simplify refreshes Crusher JSON if needed

## CtB Path A

Place / keep files under `data/platforms/antietam_cvs36/contam/`:

- `platform.prj`
- `path_map.json`
- `hobbyist_overrides.json` (starter only; ContamW edits are authoritative)

Set `hvac.transport_engine: contamx` (or `auto`) with `prj_path` pointing here.

## Commands

```bash
python3 -m tools.ship_blueprint_import author_contam \
  --platform-dir data/platforms/antietam_cvs36

# Optional offline PRJ parse gate (no ContamX binary required):
python3 -m tools.ship_blueprint_import validate \
  --platform-dir data/platforms/antietam_cvs36 --contam-gate
```

## Source

U.S. Navy CVS-36 USS Antietam (Essex class), Booklet of General Plans, 1955 — courtesy of the [San Francisco Maritime National Park Association](https://maritime.org/about/), Booklets of General Plans Online: [cvs36.pdf](https://maritime.org/doc/plans/cvs36.pdf).
