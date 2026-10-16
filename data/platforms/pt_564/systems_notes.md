# Systems inference notes — pt_564

Era: **USN WW2 fleet practice** (`usn_ww2`)

Cowled natural supply to accommodation; mechanical exhaust for galley, heads, machinery; magazines exhaust + flooding.

## Ventilation markers

| marker | kind | facing | direction | serves zone | evidence |
|---|---|---|---|---|---|
| VENT_BOX_ENG | air_port | unknown | supply | Engine_Room | sheet_read |
| FUEL_VENT_AFT | vent_trunk | unknown | exhaust | Fuel_Comp_Aft | sheet_read |
| FUEL_VENT_MID | vent_trunk | unknown | exhaust | Fuel_Comp_Mid | sheet_read |
| SKYLIGHT_WR | skylight | unknown | supply | Ward_Room | era_plausible |

## Zone ventilation modes

| zone | mode | evidence |
|---|---|---|
| Cockpit | nat_supply | era_rule |
| Crews_Quarters | nat_supply | era_rule |
| Engine_Room | nat_supply | sheet_read |
| Fore_Peak | nat_supply | era_rule |
| Foredeck | nat_supply | era_rule |
| Fuel_Comp_Aft | mech_exhaust | sheet_read |
| Fuel_Comp_Mid | mech_exhaust | sheet_read |
| Gun_Tub_Aft | nat_supply | era_rule |
| HD_Crew | exhaust_only | era_rule |
| Lazaret | mech_supply_exhaust | era_rule |
| Pilothouse | nat_supply | era_rule |
| Torpedo_Deck | nat_supply | era_rule |
| Ward_Room | nat_supply | era_plausible |

## Tanks read from the sheet

| label | kind | nearest zone |
|---|---|---|
| FUEL TANK 100 GAL P | fuel | Fuel_Comp_Aft |
| FUEL TANK 100 GAL S | fuel | Fuel_Comp_Aft |
| FUEL TANK 400 GAL P | fuel | Fuel_Comp_Mid |
| FUEL TANK 400 GAL S | fuel | Fuel_Comp_Mid |
| OIL SUMP TANK | fuel | Engine_Room |
| F.W. EXPANSION TANK | freshwater | Fuel_Comp_Mid |

## Plumbing drains

- HD_Crew (Sanitary) drains soil/gray water to the collection/sea-discharge system; nearest marked tank: HD_Crew

Evidence grades: `sheet_read` = marker drawn/labeled on the sheet; `era_rule` = era/zone-type prior; zones with neither are engineer handwork.
