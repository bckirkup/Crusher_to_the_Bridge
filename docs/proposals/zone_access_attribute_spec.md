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
