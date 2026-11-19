# Cross-hull source attribution handoff

**Status:** Handoff record. All estimates are in the [retrospective readout](cross_hull_outbreak_evidence.md) or its cited sources. This record reports no new measurements.

## 1. Question

Which explanations for historical outbreaks are compatible with reported-case AR, posting, timing, and passenger/crew differences across hull sizes, especially mega?

## 2. Current hypothesis

Investigated outbreaks include both shared upstream food introductions and person-to-person transmission. Their contributions can coexist within an outbreak. Their proportions across the historical fleet remain unidentified.

## 3. Evidence for

The [readout and reproduction query](cross_hull_outbreak_evidence.md) and the [historical aggregates](cross_hull_outbreak_evidence.csv) use the CDC public series at input snapshot `7cd051da472fd88821176ed5212a12cc51ecfcec`. The readout cites the direct investigations and the MIDRS Tables 1–3 transcription. The comparator solver screens were measured at `6742f1a4`, `455f9ff7`, and `c6c3c25f` on the seed sets committed with each screen.

## 4. Evidence against and unresolved questions

The investigated events weigh against one universal route. The historical aggregate lacks the onset and traceback linkage needed to distinguish supply structure on mega. The simulation strata condition on seed selection and have no inclusion weights for estimating population posting rates.

## 5. PRs landed

None at authoring. This change records the retrospective analysis.

## 6. Running jobs

No simulation or AWS campaign job was submitted for this analysis.

## 7. Withdrawals

No previously recorded measurement is invalidated.

## 8. Open decision

Determine whether sufficiently detailed historical records can be linked by voyage for the mega group. That linkage would permit a comparison of onset order by role, traceback, and recurrence on affected and unaffected sailings.

## 9. Do not reopen

Preserve the endpoints and denominators in the readout. Keep final reported AR, date of symptom onset, date of notification, and day of simulated threshold crossing distinct. Source attribution requires evidence independent of the endpoints used to assess compatibility.
