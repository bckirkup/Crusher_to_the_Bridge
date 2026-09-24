# Consensus tranche 47 — per-class touch shares for the declared table

**Status:** literature record; adopts nothing. Written for
`docs/ledger/NORO-TOUCH-SHARE-01.md`. Extends tranche 46 only for the
numbers that tranche did not capture: per-class touch counts or shares that
could populate `fomite_touch_share_table`.

**Retrieval.** Consensus MCP, full-text chunks on, 2026-09-24. Each number
records the section it was read in. A number absent from an indexed chunk is
recorded `?nr` (not retrieved), not as a literature null.

## 1. Numbers captured

**Jin et al. 2022**, *Int J Infect Dis*, DOI `10.1016/j.ijid.2022.05.047`.
*Results (full text):* "From 140 minutes of video analysis, we collected
41,042 surface touches by diners and staff members. … Diners touched their
mucous membranes (M), hands (H), body (B), table's object for public use (T),
and object for public use for all individuals in the restaurant (R), 39.9,
47.5, 97.3, **38.5, and 4.3** times per hour, respectively. Staff members
touched their M, H, B, T, and R, 7.0, 30.3, 85.0, **245.8, and 299.6** times
per hour." *Methods:* "81 visible diners and 18 staff members from 12:01:30
to 14:20:20"; 87 subsurfaces coded into seven groups (M, H, B, PP, PT, T, R).
Counted: touches. The per-subsurface composition of T and R (Appendix A /
Figure S1) is `?nr`.

**Ackerley et al. 2025**, *Perspect Public Health*, DOI
`10.1177/17579139251371964`; conference version Ackerley 2023, *Eur J Public
Health*, DOI `10.1093/eurpub/ckad160.995`. *Results:* "324 individuals
performed 627 touches over 13 different fomites … elevator button and front
desk counter were the most frequently touched (**32 and 22%** of all touches
respectively), with 55% of individuals touching the elevator button and 79%
touching either"; the elevator button connected to "9 other fomites
including doors, countertops, seating, a credit card reader and a hand
sanitizer pump"; other contaminated objects "luggage cart handle, sanitizer
pump, and computer equipment". Counted: touches (shares) and touchers
(fractions), reported separately. The per-fomite split of the remaining 46%
is `?nr` — the full-text table is not indexed.

**Cheng et al. 2015**, *J Hosp Infect*, DOI `10.1016/j.jhin.2014.12.024`.
*Findings (abstract):* 6,144 contact-episodes in 66 h; bedside rails 13.6,
bedside tables 12.3 contact-episodes/h. Counted: contact episodes, not
touches. Hospital cubicle; no cruise zone class maps to it under the `shared`
reading (cabin has no bed rail class enumerated) — not used.

## 2. Settings queried with no usable per-class share retrieved

| Setting (zone class) | Queries | Best hit | Why not usable |
|---|---|---|---|
| public restroom (`sanitary`) | touch frequency per surface flush/tap/door/latch | Abney et al. 2024 (*Food Environ Virol*, QMRA) | assumed contact sequences, not observation |
| hotel guest room (`cabin`) | per-surface touch counts light switch, remote, door | hotel cleanliness perception surveys (ATP) | self-report of "most touched", no counts |
| commercial kitchen (`galley`) | food-handler per-surface touch frequency | Kirchner et al. 2023 (*Am J Infect Control*) | home-kitchen first-7-touch coding, cross-contamination outcome, no shares |
| crew mess (`crew_mess`) | — | Jin 2022 staff rates | servers, not diners |

No source reporting per-class touch shares for a cruise or shipboard setting
was retrieved. No source reported a summed high-touch area for any room; the
tranche 45/46 null stands.

## 3. Queries run

1. Ackerley 2025 hotel lobby 13 fomites 627 touches elevator button front
   desk counter per fomite touch counts proportion
2. Jin 2022 restaurant norovirus touch frequency table public objects
   restaurant public objects diners staff seven surface groups
3. Cheng 2015 six-bed cubicle contact episodes per hour bedside rail table
   touches per hour hand touch surface frequency list
4. public restroom touch observation frequency per surface flush handle tap
   faucet door handle toilet seat proportion of touches video
5. public toilet washroom surface touch frequency observation number of
   touches flush button tap door handle cubicle lock per user
6. hotel guest room housekeeping high touch surface touch frequency per
   surface light switch remote control door handle observation counts
7. commercial kitchen food handler hand contact surface frequency observation
   touches per hour utensils taps handles work surface
8. Ackerley hotel lobby observation table number of touches per fomite entry
   door handle luggage cart handle hand sanitizer pump credit card reader
   seating percentage of touches
9. Jin 2022 restaurant appendix surface list restaurant public objects door
   handle soup ladle serving spoon public chopsticks tablecloth touch
   frequency per surface
