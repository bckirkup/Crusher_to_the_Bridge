# Durable zone-access attribute

> **Status:** Proposed. No value is adopted and no platform JSON is changed.

Item 1 currently uses a token filter over each zone's `name`, `deck`, and
`description` to keep machinery, service, stores, galley, bridge, navigation,
and technical spaces out of passenger leisure draws. That gets the current
platform records right without inventing a physical or epidemiological
parameter, and preserves the full zone list for crew work assignments.

A durable schema should declare access explicitly, for example
`passenger_accessible: true|false`, or `access: passenger|crew|restricted|shared`.
The declared field would be authoritative, validated by the platform contract,
and independently reviewable.

The interim token list is evidence from names and descriptions, not a declared
field. It can fail in both directions: a future crew-only zone may be named
without an exclusion token, while a passenger venue whose description mentions
a galley or service hatch could be falsely excluded. This proposal adopts no
field value and does not add the field to platform files.

## Audit of current token decisions

Every platform's token-filter decisions was audited against the zone's own
description:

| Platform | Free-typed zones excluded from passenger leisure |
| --- | --- |
| `mega_cruise_5000` | Bridge, Central_Stores, Laundry_Main, WasteTreat, Engine_Room_Aft, EngControl |
| `messy_cruise_500` | Bridge, Central_Stores, Laundry_Main, Waste_Treatment_Plant, Engine_Room_Aft, Engine_Control_Room |
| `spirit_cruise_3000` | Laundry, Engine_Room |
| `classic_cruise_1900` | Laundry, Engine_Room |
| `expedition_cruise_300` | Bridge, Laundry, Stores, Engine_Room |
| `expedition_cruise_450` | Laundry, Stores, Engine_Room |
| `destroyer_baseline` | Bridge |
| `fletcher_class_destroyer` | Bridge, CIC, Engine_Room_Fwd, Engine_Room_Aft |
| `legend_class_nsc` | Bridge, Engine_Room |
| `san_antonio_class_lpd` | Bridge, Hangar, Engine_Room_Fwd, Engine_Room_Aft |
| `enterprise_constitution_tos` | Bridge, BriefRoom, StoresDry, StoresCold |
| `enterprise_galaxy_tng` | Bridge, StoresDry, StoresCold |

All excluded records are controlled work or service spaces on inspection of
their own descriptions: `BriefRoom` is “Bridge briefing / ready room”,
`Hangar` is “Aircraft hangar ... Maintenance shops, aviation stores”, and
`CIC` is “Combat Information Center ... below bridge”. The interim filter
therefore produced no false exclusion in this audit, while remaining
string-based; that limitation is why the durable access attribute is proposed.

## Seeded timing consequence

The weighted leisure draw changes the seeded random-number stream, so the
default-seed escalation timing moved from 16 h to 124 h. A 24-seed audit found
baseline first-escalation epochs of 2–126 h (median 30 h; two never
escalated), versus weighted epochs ranging 1–85 h (median 24.5 h; two never
escalated). The distributions are indistinguishable; the old 8–72 h assertion
was not a model property and was replaced by a voyage-scale bound.
