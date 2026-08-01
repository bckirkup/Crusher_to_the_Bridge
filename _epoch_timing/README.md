# Epoch timing harness

Ad-hoc wall-clock characterisation for Picard ship runs. Ported from the
orphaned `cursor/epoch-timing-harness` branch and extended for the
cabin-corridor cruise fleet.

## Compare cruise classes

```bash
python3 _epoch_timing/time_epochs.py --compare-cruise --epochs 12 --budget 180
```

Writes per-platform `*.timing.json` plus `compare_cruise.summary.json` with
mean s/epoch and a rough 240-epoch hour projection.

## Single platform

```bash
python3 _epoch_timing/time_epochs.py --platform classic_cruise_1900 \
  --num-agents 1910 --epochs 24 --label classic_n1910
```

## Mega campaign tier (original)

```bash
python3 _epoch_timing/time_epochs.py --tier t1 --epochs 21 --num-agents 2000 \
  --label n2000
```

`*.spec.json` files are gitignored; commit `*.timing.json` / summary JSON when
you want the numbers in-repo.
