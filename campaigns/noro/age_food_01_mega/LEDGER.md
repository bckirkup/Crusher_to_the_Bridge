# NORO-AGE-FOOD-01 mega cells — campaign ledger

Wave-3 companion spec of `campaigns/noro/age_food_01/` — same manifest
(`noro_age_food_01_manifest.json`), only the six `fl_meg_12d_scr_*`
blocks, on the MEGA-IMPACT-01-proven container class (6144 MB / 1 vcpu).
Split from the parent spec because `campaign.json` `resources` applies
per spec, not per block.

Design of record: `docs/norovirus/noro_age_food_01_sweep_design.md`.

## Status

| date | event |
|------|-------|
| 2026-10-05 | Spec built by `age_food_01/design/build.py`; awaiting wave-3 submission decision. |
| 2026-10-06 | WAVE 3 (meg, 6 blocks × 288 seeds = 1,728 voyages) submitted at 2df542ff34d0. Image `picard-campaign:noro-age-food01-mega`, digest `sha256:112247d3d7586b923a40e89cbf90f9e64c79301e98c24fc2d34f085d6a76fad5` (built at 9ab260d92229). Jobdef `picard-noro-age-food-01-mega` revs :1–:6 @ 6144 MB / 1 vcpu, carrying `retryStrategy` (attempts 10, `Host EC2*`). Arrays: gen_l1 014ab26c, gen_ship afba0319, snr_l1 966ebfe3, snr_ship 84d6ec16, fam_l1 d4c726ce, fam_ship f6c5d657. All 1,728 children RUNNABLE (FIFO behind wave-2 spr). **OOM finding:** a local smoke of `fl_meg_12d_scr_gen_l1` index 0 in the pushed image under a 6144 MB cgroup (matching the jobdef) was OOM-killed ~55 min into the voyage — RSS climbed ~0.4→4.6+ GiB before SIGKILL, no application error. The 6144 MB jobdef is too small for meg cells; queued children will OOM when they reach the queue head unless the jobdef memory is raised and blocks resubmitted (reported, not retry-tuned). |

## Findings

- 2026-10-06 — **meg cells exceed the 6144 MB jobdef**: local `--local` smoke of `fl_meg_12d_scr_gen_l1` index 0 in `picard-campaign:noro-age-food01-mega` (sha256:112247d3) under `docker run --memory=6144m` was OOM-killed (`oom=true`, SIGKILL) ~55 min in; RSS grew steadily the whole voyage (~0.4→4.6+ GiB, still climbing). Worker `tools/noro_diag/growth_chain_census.py`, tier `fl_meg_12d_scr_gen_l1`, seed 8000. Wave-3 arrays are submitted but still RUNNABLE — needs a larger meg jobdef + resubmit before cells reach the queue head.
