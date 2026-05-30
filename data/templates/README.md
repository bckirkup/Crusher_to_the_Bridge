# Data Templates

Production-grade configuration templates extracted from the Korkin Lab
`infection-dynamics` repository.  These serve as reference examples for
creating new simulation scenarios.

## Template Files

### `multi_pathogen_cruise_ship.json`

**Multi-pathogen concurrent profile: Norwalk GII.4 + SARS-CoV-2 BA.5**

- Norwalk dose-response parameters from `Person.java` (α=0.111, β=32.81, η=0.508, γ=0.095)
- Shedding curves from Atmar et al. RT-PCR data (Figure 1C/1E)
- SARS-CoV-2 compartmental parameters from `SEIQR-SCM-diamond.Rmd` (Diamond Princess calibration)
- Mid-cruise pathogen introduction (SARS-CoV-2 at epoch 6)
- Dual microflora disruption signatures (GI + respiratory)

### `enterprise_constitution_tos.json`

**USS Enterprise (Constitution class, TOS) — crew demographics and pathogens**

- Platform: `data/platforms/enterprise_constitution_tos/` (13 zones including `Mess_Hall` for SOP compatibility)
- Pathogens: `data/pathogens/enterprise_tos_profiles.json` — Rigelian fever, Psi-2000 polywater analog
- Agent classes: command, helm/ops, security, engineering, sciences, medical, communications, services, general (all `crew`)
- Recommended `num_agents`: 200 (full complement ~430)

### `enterprise_galaxy_tng.json`

**USS Enterprise-D (Galaxy class, TNG) — crew + civilian families**

- Platform: `data/platforms/enterprise_galaxy_tng/` (17 zones)
- Pathogens: `data/pathogens/enterprise_tng_profiles.json` — Barclay protomorphosis, shipboard influenza analog
- Agent classes: Starfleet departments plus `passenger_family` / `passenger_civilian`
- Recommended `num_agents`: 400

### `cruise_ship_x_layout.json`

**22-zone cruise ship spatial/HVAC layout derived from GIS shapefiles**

- Zone centroids computed from polygon geometries in `NorwalkVirus/Dependencies/maps/`
- Volumes derived from GIS polygon areas × ceiling heights
- 3-deck HVAC zone configuration with inter-deck ducted connections
- CruiseNet corridor/elevator network (28,568 line segments) mapped to adjacency graph
- Population: 1,888 passengers + 814 crew = 2,702 total onboard

## Usage

Copy a template into the active configuration directory and modify as needed:

```bash
# Use the multi-pathogen profile
cp data/templates/multi_pathogen_cruise_ship.json data/pathogens/active_profiles.json

# Use the cruise ship layout (extract spatial_layout and air_flow_paths sections)
# Note: This template combines both files — extract the relevant sections
python -c "
import json
with open('data/templates/cruise_ship_x_layout.json') as f:
    tmpl = json.load(f)
with open('data/platforms/cruise_ship_x/spatial_layout.json', 'w') as f:
    json.dump(tmpl['spatial_layout'], f, indent=2)
with open('data/platforms/cruise_ship_x/air_flow_paths.json', 'w') as f:
    json.dump(tmpl['air_flow_paths'], f, indent=2)
"

# Validate before running
python tools/sanity_checker.py
```

## Sources

- **Srinivasan S, King J, Collins JM, Colubri A, Korkin D.** "Real-time
  spatiotemporal tracking of infectious outbreaks in confined environments
  with a host–pathogen agent-based system." *PNAS* 2026;123(4):e2422574123.
- **Teunis PFM et al.** "Norwalk virus: How infectious is it?" *J Med Virol*
  2008;80:1468–1476. (dose-response parameters)
- **Atmar RL et al.** "Norwalk Virus Shedding after Experimental Human
  Infection." *Emerg Infect Dis* 2008;14(10):1553–1557. (shedding curves)
