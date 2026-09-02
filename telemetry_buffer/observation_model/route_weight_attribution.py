"""What the route weights do, measured on the realised exposure stream.

Usage: route_weight_attribution.py <exposure_events_*.json> [pathogen_id]
Findings: route_weight_measurement_findings.md

Reads the per-exposure-event records written by route_weight_attenuation.py and
reports, for one hull:

1. mass share by pathway, pre- and post-weight;
2. establishment-weighted route attribution -- each event's establishment
   probability credited across pathways in proportion to the dose each
   delivered, which is the statistic the older single-shedder probe in
   `a5_role_asymmetry_diagnosis.md` reported and is not the same object as
   mass share;
3. S(s) = sum_i P(establish | s * D_i) for multiplicative dose scales s, the
   exposure-side elasticity of the dose axis;
4. S under alternative route multiplier sets, including the clearance-derived
   efficiencies in `route_clearance_findings.md` Sec 2.

E_r[1 - exp(-rD)] = 1 - 1F1(alpha; alpha+beta; -D) exactly (beta-Poisson Kummer
form), so no quadrature is needed.

S sums over every exposure event, including exposures of agents already infected
or recovered, so its level is an upper bound on establishments. Its *ratios*
across multiplier sets are the quantity of interest.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.special import hyp1f1

# Per-pathogen beta-frailty parameters as shipped in active_profiles.json.
# Both are inherited/adapted values, not measurements: norwalk_gi's pair is the
# administered-oral Norwalk GI.1 inoculum fit, and sars_cov2_resp's is adapted
# from SARS-CoV-1. Every dose figure derived here is void pending a refit.
DOSE_RESPONSE = {
    "norwalk_gi": (0.111, 32.81),
    "sars_cov2_resp": (0.18, 58.0),
}

# Shipped norwalk_gi transmission_route_weights, keyed by engine pathway name.
SHIPPED = {
    "direct_contact": 0.35,
    "droplet": 0.10,
    "hvac_airborne": 0.05,
    "fomite": 0.30,
    "food": 0.20,
    "environmental": 0.0,
}
# Clearance-derived per-virion efficiency, oral reference, Edison v2 rates
# (route_clearance_findings.md Sec 2). Grade C, recorded not adopted.
CLEARANCE = {
    "direct_contact": 0.500,
    "droplet": 0.071,
    "hvac_airborne": 0.071,
    "fomite": 0.500,
    "food": 1.000,
    "environmental": 1.000,
}
UNIT = dict.fromkeys(SHIPPED, 1.0)
# Same clearance rates with droplet re-assigned to the oral portal, the
# alternative route_clearance_findings.md Sec 5 says has to be settled first.
CLEARANCE_ORAL_DROPLET = {**CLEARANCE, "droplet": 0.500, "hvac_airborne": 0.500}


def main(path: Path) -> int:
    pid = sys.argv[2] if len(sys.argv) > 2 else "norwalk_gi"
    alpha, beta = DOSE_RESPONSE[pid]

    def p_establish(dose: np.ndarray) -> np.ndarray:
        return 1.0 - hyp1f1(alpha, alpha + beta, -dose)

    all_events = json.loads(path.read_text(encoding="utf-8"))
    events = [e for e in all_events if e.get("pathogen_id") == pid]
    if not events:
        raise SystemExit(f"no events for {pid} in {path}")
    pathways = sorted({k for e in events for k in e["pre"]})
    pre = np.array([[e["pre"].get(k, 0.0) for k in pathways] for e in events])
    post = np.array([[e["post"].get(k, 0.0) for k in pathways] for e in events])

    print(f"{path.name}: {pid}, {len(events)} of {len(all_events)} exposure "
          f"events, Beta({alpha}, {beta}), pathways {pathways}")

    def attribute(doses: np.ndarray, label: str) -> None:
        total = doses.sum(axis=1)
        p = p_establish(total)
        with np.errstate(invalid="ignore", divide="ignore"):
            share = np.where(total[:, None] > 0, doses / total[:, None], 0.0)
        credited = (share * p[:, None]).sum(axis=0)
        mass = doses.sum(axis=0)
        print(f"\n{label}: S = {p.sum():.4f}")
        print(f"{'pathway':16} {'mass share':>12} {'establishment share':>21}")
        for i, name in enumerate(pathways):
            print(f"{name:16} {mass[i]/mass.sum():12.5f} "
                  f"{credited[i]/credited.sum():21.5f}")

    attribute(pre, "pre-weight (weights all 1.0)")
    attribute(post, "post-weight (shipped weights)")

    base = float(p_establish(post.sum(axis=1)).sum())
    print("\ndose-scale elasticity, shipped-weight exposures as the base")
    print(f"{'scale':>10} {'S':>12} {'S/S(1)':>10}")
    for s in (0.06, 0.125, 0.25, 0.5, 1.0, 2.0, 2.889, 4.0, 8.0):
        val = float(p_establish(s * post.sum(axis=1)).sum())
        print(f"{s:10.4f} {val:12.4f} {val/base:10.4f}")

    print("\nalternative route multiplier sets, applied to the pre-weight stream")
    print(f"{'set':28} {'S':>12} {'vs unit':>10} {'vs shipped':>12}")
    unit_s = float(p_establish(pre.sum(axis=1)).sum())
    for label, weights in (
        ("unit (no route weights)", UNIT),
        ("shipped route weights", SHIPPED),
        ("clearance-derived (v2)", CLEARANCE),
        ("clearance, oral droplet", CLEARANCE_ORAL_DROPLET),
    ):
        w = np.array([weights.get(k, 1.0) for k in pathways])
        val = float(p_establish((pre * w[None, :]).sum(axis=1)).sum())
        print(f"{label:28} {val:12.4f} {val/unit_s:10.4f} {val/base:12.4f}")

    print("\nwhere establishment comes from, by exposure percentile")
    total = post.sum(axis=1)
    p = p_establish(total)
    order = np.argsort(total)
    cum = np.cumsum(p[order]) / p.sum()
    for pct in (50, 75, 90, 95, 99):
        print(f"  exposures below p{pct}: {cum[int(len(cum) * pct / 100)]:.4%} of S")

    counts: dict[str, int] = defaultdict(int)
    top = order[int(len(order) * 0.99):]
    for i in top:
        counts[pathways[int(np.argmax(post[i]))]] += 1
    print(f"  dominant pathway among the top 1% of exposures: {dict(counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
