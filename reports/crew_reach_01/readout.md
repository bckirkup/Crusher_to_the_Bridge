# CREW-REACH-01 canary readout

Record: lab_confirmed 712/voyage; crew share 0.29; asymptomatic-at-specimen ~0.49 (honest bound ~0.4).

Parent boxed (labelled pre-change baseline): pooled lab_confirmed 819.0.

| arm | cells | pooled lab_conf | Δ vs declared | Δ vs parent | DP-scale seeds | crew share pooled | crew share DP-scale | asym share | dated share | retest spec/conf | wave spec/conf | deliv med | conf-pax takeoff med | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| boxed_declared | 20 | 1354 | +0 | 535 | [20200210, 20200218, 20200222, 20200223] | 0.399 | 0.308 | 0.184 | 0.733 | 3296/569 | 0/0 | 192772 | 98 | BASELINE |
| boxed_s1 | 20 | 1333 | -21 | 514 | [20200210, 20200218, 20200222, 20200223] | 0.398 | 0.315 | 0.156 | 0.761 | 40860/597 | 0/0 | 192772 | 98 | NO-MOVE |
| boxed_s1s2 | 20 | 1451 | +97 | 632 | [20200210, 20200218, 20200222, 20200223] | 0.447 | 0.358 | 0.231 | 0.696 | 42230/637 | 16620/161 | 192772 | 98 | MOVES-TOWARD-RECORD |
| boxed_s2 | 20 | 1453 | +99 | 634 | [20200210, 20200218, 20200222, 20200223] | 0.440 | 0.350 | 0.246 | 0.689 | 3296/569 | 11062/121 | 192772 | 98 | MOVES-TOWARD-RECORD |

## Audit


## Bit-identity (day<=31 slice)

- seed 20200205: DIFF ['infections_total', 'infections_during_window', 'confined_passenger_infections_during_quarantine']
- seed 20200206: DIFF ['infections_total', 'infections_during_window']
- seed 20200207: DIFF ['infections_total', 'infections_during_window', 'confined_passenger_infections_during_quarantine']
- seed 20200208: DIFF ['infections_total', 'infections_during_window', 'confined_passenger_infections_during_quarantine']
- seed 20200209: MATCH
- seed 20200210: DIFF ['infections_total', 'infections_during_window', 'confined_passenger_infections_during_quarantine']
- seed 20200211: DIFF ['infections_total', 'infections_during_window', 'confined_passenger_infections_during_quarantine']
- seed 20200212: DIFF ['infections_total', 'infections_during_window', 'confined_passenger_infections_during_quarantine']
- seed 20200213: MATCH
- seed 20200214: MATCH
- seed 20200215: DIFF ['infections_total', 'infections_during_window']
- seed 20200216: MATCH
- seed 20200217: MATCH
- seed 20200218: DIFF ['infections_total', 'infections_during_window', 'confined_passenger_infections_during_quarantine']
- seed 20200219: DIFF ['infections_total', 'infections_during_window', 'confined_passenger_infections_during_quarantine']
- seed 20200220: DIFF ['infections_total', 'infections_during_window', 'confined_passenger_infections_during_quarantine']
- seed 20200221: DIFF ['infections_total', 'infections_during_window', 'confined_passenger_infections_during_quarantine']
- seed 20200222: DIFF ['infections_total', 'infections_during_window', 'confined_passenger_infections_during_quarantine']
- seed 20200223: DIFF ['infections_total', 'infections_during_window', 'confined_passenger_infections_during_quarantine']
- seed 20200224: MATCH
