"""Re-read the retained expedition arrays stratified by the dose scale.

Every design point in a bounded-gate array carries its own
``environmental_faecal_release_log10_g_per_epoch`` (``adj``). The scalar sits in
the exponent of the emission, so a uniform design over [4, 24] spans twenty
orders of magnitude of release, and the ledger records a switch near
``adj ~ 6-7``: below it a voyage transmits, above it a voyage's infections are
close to its boarding imports. A campaign marginalised over that box therefore
reports a mixture of two regimes, and a mechanism contrast read across it is
diluted by whatever fraction of the design happens to lie above the switch.

This readout does not re-run anything. It bins each arm's retained per-voyage
rows by the ``adj`` of the point that produced them, and re-reads the paired
mechanism contrasts within a stratum, so that each arm is compared with its
control on ships that transmit. The strata are cut at the switch measured in
the ledger, not at a quantile of the design, and they are stated here rather
than chosen per arm.

Two limits are structural and no amount of re-reading removes them. A stratum
holds roughly a seventh of the design, so a contrast that was bounded at
+-0.1 pp over the whole box is bounded at around +-0.7 pp inside one. And
``adj`` does not scale the hand, surface or food routes at all
(``docs/norovirus/fomite_pool_denominator_reconciliation.md``), so for a
fomite-side arm the strata differ only in the routes the arm does not touch.

That second limit is also why the top stratum is not an import-only regime, and
``floor_probe`` reads it directly: the hand route carries its own release
normaliser (``HAND_LOAD_LOG10_GEC`` read against ``HAND_LOAD_REFERENCE_PEAK``,
an implicit -7.14 log10 g of stool per hand), so a voyage keeps a transmitting
channel at a fixed scale however far ``adj`` shuts the profiled one down.

Finite-sample over the submitted designs. Nothing is selected or adopted by it.

    python3 -m telemetry_buffer.observation_model.adj_stratified_readout
"""
from __future__ import annotations

import argparse
import glob
import json
import statistics as st
from math import comb

BASE = "telemetry_buffer/observation_model"
POSTING_THRESHOLD = 0.03
ADJ = "environmental_faecal_release_log10_g_per_epoch"
BOARDING_PAX = "boarding_prevalence_passenger"

# Cut at the switch measured in the ledger, not at a quantile of the design.
STRATA = (("live", 0.0, 5.5), ("transition", 5.5, 6.5), ("import_only", 6.5, 99.0))

CAMPAIGNS = {
    "SURF-KO-01": (
        "threearm_expedition_base",
        ("threearm_expedition_surfko",),
    ),
    "CONTACT-SCALE-01": (
        "contactscale_expedition_phi0",
        tuple(f"contactscale_expedition_{t}"
              for t in ("phim1", "phi05", "phi1", "phi2")),
    ),
    "CONTACT-ARCH-01": (
        "contactarch_expedition_control",
        tuple(f"contactarch_expedition_{t}" for t in ("low", "mid", "high")),
    ),
    "CONTACT-ARCH-02": (
        "contactarch2_expedition_control",
        tuple(f"contactarch2_expedition_{t}"
              for t in ("low", "mid", "high", "mid_tau1", "mid_tau2",
                        "high_tau05", "high_tau1", "high_tau2")),
    ),
}


def load(stage: str, root: str = BASE):
    """Per-voyage rows keyed by point and seed, plus each point's factors."""
    rows: dict[str, dict] = {}
    factors: dict[int, dict] = {}
    for path in sorted(glob.glob(f"{root}/{stage}/*/*.jsonl")):
        with open(path) as handle:
            for line in handle:
                record = json.loads(line)
                if "runs" not in record:
                    continue
                point = record["point_index"]
                factors[point] = record["factors"]
                for run in record["runs"]:
                    rows[f"p{point:04d}_s{run['seed']}"] = dict(
                        run, point_index=point,
                    )
    return rows, factors


def posted(row: dict) -> bool:
    return (
        row["reported_case_attack_rate_passenger"] >= POSTING_THRESHOLD
        or row["reported_case_attack_rate_crew"] >= POSTING_THRESHOLD
    )


def _stratum_keys(rows, factors, low, high):
    return {
        key for key, row in rows.items()
        if low <= float(factors[row["point_index"]][ADJ]) < high
    }


def _mean_pp(values):
    return 100.0 * st.mean(values)


def _se_pp(values):
    if len(values) < 2:
        return float("nan")
    return 100.0 * st.stdev(values) / len(values) ** 0.5


def describe(rows, keys, label: str) -> None:
    """Level readout for one stratum of one arm."""
    if not keys:
        print(f"{label:>26} | empty")
        return
    sub = [rows[key] for key in keys]
    pax = st.mean(row["infection_attack_rate_passenger"] for row in sub)
    crew = st.mean(row["infection_attack_rate_crew"] for row in sub)
    postings = sum(posted(row) for row in sub)
    points = len({row["point_index"] for row in sub})
    ratio = f"{pax / crew:5.2f}" if crew else "  n/a"
    print(
        f"{label:>26} | n={len(sub):5d} pts={points:3d} "
        f"pax={100 * pax:6.2f}% crew={100 * crew:6.2f}% A5={ratio} "
        f"post={100 * postings / len(sub):5.2f}%"
    )


def contrast(control, arm, keys, label: str) -> None:
    """Paired contrast between two arms, restricted to one stratum."""
    common = sorted(keys & set(control) & set(arm))
    if not common:
        print(f"{label:>26} | empty")
        return
    off = sum(1 for key in common if posted(control[key]) and not posted(arm[key]))
    on = sum(1 for key in common if not posted(control[key]) and posted(arm[key]))
    total, smaller = off + on, min(off, on)
    sign_p = (
        min(1.0, 2 * sum(comb(total, i) for i in range(smaller + 1)) / 2 ** total)
        if total else 1.0
    )
    d_pax = [arm[key]["infection_attack_rate_passenger"]
             - control[key]["infection_attack_rate_passenger"] for key in common]
    d_crew = [arm[key]["infection_attack_rate_crew"]
              - control[key]["infection_attack_rate_crew"] for key in common]
    print(
        f"{label:>26} | n={len(common):5d} "
        f"dpax={_mean_pp(d_pax):+7.3f}+-{_se_pp(d_pax):5.3f} pp "
        f"dcrew={_mean_pp(d_crew):+7.3f}+-{_se_pp(d_crew):5.3f} pp "
        f"flips {off}/{on} p={sign_p:.3f}"
    )


def boarding_split(rows, factors, root: str = BASE) -> None:
    """Within the import-only stratum, posting rate by boarding-prevalence quartile."""
    del root
    keys = _stratum_keys(rows, factors, 6.5, 99.0)
    sub = [rows[key] for key in sorted(keys)]
    points = sorted({row["point_index"] for row in sub})
    values = sorted(float(factors[p][BOARDING_PAX]) for p in points)
    cuts = [values[int(len(values) * q)] for q in (0.25, 0.5, 0.75)]
    print("\nimport-only stratum by passenger boarding prevalence "
          f"({len(sub)} voyages, {len(points)} points)")
    buckets: dict[int, list] = {i: [] for i in range(4)}
    for row in sub:
        prevalence = float(factors[row["point_index"]][BOARDING_PAX])
        buckets[sum(1 for cut in cuts if prevalence >= cut)].append(row)
    for index in range(4):
        rowset = buckets[index]
        if not rowset:
            continue
        prevalence = st.mean(
            float(factors[row["point_index"]][BOARDING_PAX]) for row in rowset
        )
        pax = st.mean(row["infection_attack_rate_passenger"] for row in rowset)
        postings = sum(posted(row) for row in rowset)
        print(
            f"{'Q' + str(index + 1):>26} | boarding={100 * prevalence:5.2f}% "
            f"n={len(rowset):5d} pax_infAR={100 * pax:5.2f}% "
            f"post={100 * postings / len(rowset):5.2f}%"
        )


FLOOR_BANDS = ((6.5, 7.5), (7.5, 8.5), (8.5, 10.0), (10.0, 99.0))
FLOOR_DEAD = 10.0
BIG_VOYAGE_PAX_AR = 0.08


def _band_line(rows, factors, low, high) -> str:
    sub = [row for row in rows.values()
           if low <= float(factors[row["point_index"]][ADJ]) < high]
    if not sub:
        return f"adj {low:4.1f}-{high:4.1f} | empty"
    pax_posted = sum(
        row["reported_case_attack_rate_passenger"] >= POSTING_THRESHOLD
        for row in sub
    )
    return (
        f"adj {low:4.1f}-{high:4.1f} | n={len(sub):5d} "
        f"pax_infAR={100 * st.mean(r['infection_attack_rate_passenger'] for r in sub):5.2f}% "
        f"boarding={100 * st.mean(float(factors[r['point_index']][BOARDING_PAX]) for r in sub):5.2f}% "
        f"post_pax={100 * pax_posted / len(sub):5.2f}% "
        f"post_any={100 * sum(posted(r) for r in sub) / len(sub):5.2f}%"
    )


def floor_probe(rows, factors) -> None:
    """What still transmits where the profiled release is arithmetically dead.

    Above ``adj ~ 8.5`` a host's profiled emission is below one copy per epoch,
    so any voyage whose passenger infection attack rate exceeds its boarding
    prevalence transmitted through a route the scalar never entered. The factor
    contrast is descriptive: the design is a space-filling box, the subsets are
    small, and no association here is causal or adopted.
    """
    print("\nposting floor by dose band (passenger channel is A9's numerator)")
    for low, high in FLOOR_BANDS:
        print(f"{'':>13}{_band_line(rows, factors, low, high)}")
    dead = [row for row in rows.values()
            if float(factors[row["point_index"]][ADJ]) >= FLOOR_DEAD]
    if not dead:
        return
    big = [row for row in dead
           if row["infection_attack_rate_passenger"] > BIG_VOYAGE_PAX_AR]
    print(f"\nadj >= {FLOOR_DEAD:.0f}: {sum(r['took_off'] for r in dead)} of "
          f"{len(dead)} voyages took off, {len(big)} exceeded "
          f"{100 * BIG_VOYAGE_PAX_AR:.0f}% passenger infection AR")
    if not big:
        return
    for key in sorted(next(iter(factors.values()))):
        whole = st.mean(float(factors[r["point_index"]][key]) for r in dead)
        if not whole:
            continue
        part = st.mean(float(factors[r["point_index"]][key]) for r in big)
        print(f"{key:>52} | {part / whole:5.2f}x the band mean")


def read_campaign(name, control_stage, arm_stages, root: str = BASE) -> dict:
    control, factors = load(control_stage, root)
    if not control:
        print(f"\n=== {name}: control array absent under {root} ===")
        return {}
    print(f"\n=== {name} ({control_stage}) ===")
    adj_values = sorted(float(f[ADJ]) for f in factors.values())
    census = ", ".join(
        f"{tag} {sum(1 for v in adj_values if low <= v < high)}"
        for tag, low, high in STRATA
    )
    print(f"adj {adj_values[0]:.2f}-{adj_values[-1]:.2f} over "
          f"{len(adj_values)} points; {census}")
    keys = {tag: _stratum_keys(control, factors, low, high)
            for tag, low, high in STRATA}
    for tag in keys:
        describe(control, keys[tag], f"control/{tag}")
    for stage in arm_stages:
        arm, _ = load(stage, root)
        if not arm:
            print(f"{stage:>26} | array absent")
            continue
        short = stage.split("expedition_")[-1]
        for tag, _, _ in STRATA:
            if tag == "import_only":
                continue
            contrast(control, arm, keys[tag], f"{short}/{tag}")
    return {"control": control, "factors": factors}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=BASE,
                        help="directory holding the retained campaign arrays")
    args = parser.parse_args()
    last = {}
    for name, (control_stage, arm_stages) in CAMPAIGNS.items():
        read = read_campaign(name, control_stage, arm_stages, args.root)
        last = read or last
    if last:
        boarding_split(last["control"], last["factors"], args.root)
        floor_probe(last["control"], last["factors"])


if __name__ == "__main__":
    main()
