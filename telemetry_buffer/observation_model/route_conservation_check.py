"""Direct-contact dose against the hand reservoir the same host carries.

Closed-form check on shipped constants only: no simulation, no RNG, no
calibration. It answers one question — how much virus does the
direct-contact pathway deliver to one contact, compared with how much the
donor's hands are carrying at that moment — and reports the composed
alternative for the same contact through the reservoir and the hand-to-mouth
step the fomite pathway already uses.

Read alongside `dose_concentration_findings.md` §3/§5, whose realised per-draw
medians are the independent cross-check on the gap printed here, and
`../../docs/proposals/direct_contact_hand_composition.md`, which is where the
interpretation lives. Nothing here adopts or proposes a constant.

Usage: python3 telemetry_buffer/observation_model/route_conservation_check.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.infection_dynamics_bridge import (  # noqa: E402
    ALPHA,
    BETA,
    HAND_LOAD_LOG10_GEC,
    HAND_LOAD_REFERENCE_PEAK_LOG10,
    SYMPTOMATIC_SHEDDING,
)
from engines.infection_dynamics_bridge import (  # noqa: E402
    ENVIRONMENTAL_FAECAL_RELEASE_LOG10_G_PER_EPOCH as RELEASE_LOG10,
)
from engines.transmission_core import (  # noqa: E402
    HAND_TO_MOUTH_NORMAL,
    MOUTH_CONTACT_FRACTION_RANGE,
)

# Norovirus `route_efficiency_multipliers["direct_contact"]`, the route's sole
# surviving owner after the C5 retirement of `contact_transfer_fraction`
# (tranche 12 §10). Read from the profile rather than hard-coded by the caller.
PROFILE_PATH = "data/pathogens/active_profiles.json"
HOURS_PER_DAY = 24.0

# Donor-hand -> recipient-hand transfer, for the composed arm only. These are
# the wet-deposit directional measurements of tranche 12 §1-§4 with skin as the
# recipient surface; person-to-person transfer is an explicit literature null
# (§6.3), so this is a declared analogy and is NOT adopted anywhere.
TRANSFER_ARMS = (
    (0.30, "Sharps wet genome-copy upper"),
    (0.13, "Tuladhar MNV-1 finger->steel, wet"),
    (0.01, "dried"),
)


def _direct_efficiency() -> float:
    """Norovirus direct-contact route efficiency, read from the profile."""
    data = json.loads((REPO_ROOT / PROFILE_PATH).read_text())
    entries = data.get("pathogens", data)
    values = entries.values() if isinstance(entries, dict) else entries
    for profile in values:
        if not isinstance(profile, dict):
            continue
        label = "{} {}".format(
            profile.get("pathogen_id", ""), profile.get("name", ""),
        ).lower()
        if "noro" not in label and "norwalk" not in label:
            continue
        return float(
            profile.get("route_efficiency_multipliers", {}).get(
                "direct_contact", 1.0,
            ),
        )
    raise SystemExit(f"no norovirus profile found in {PROFILE_PATH}")


def _hand_reservoir(curve_log10: float) -> float:
    """Genome copies on one hand of a host at this shedding-curve value."""
    return math.pow(10.0, HAND_LOAD_LOG10_GEC) * math.pow(
        10.0, curve_log10 - HAND_LOAD_REFERENCE_PEAK_LOG10,
    )


def _direct_dose(curve_log10: float, efficiency: float) -> float:
    """Genome copies the direct pathway delivers to one contact, per epoch."""
    emission_per_epoch = math.pow(
        10.0, curve_log10 - RELEASE_LOG10,
    ) / HOURS_PER_DAY
    return efficiency * emission_per_epoch


def _hand_to_mouth_midpoint() -> float:
    """Ingested fraction of a hand load per mouth contact, at midpoints."""
    used = sum(MOUTH_CONTACT_FRACTION_RANGE) / 2.0
    return used * HAND_TO_MOUTH_NORMAL[0]


def _p_infection(dose: float) -> float:
    """Shipped Teunis hypergeometric dose-response."""
    return 1.0 - math.pow(1.0 + dose / BETA, -ALPHA)


def _report_ratio(efficiency: float, curves: tuple[float, ...]) -> None:
    print(
        f"\nhand bridge offset: {HAND_LOAD_LOG10_GEC} - "
        f"{HAND_LOAD_REFERENCE_PEAK_LOG10} = "
        f"{HAND_LOAD_LOG10_GEC - HAND_LOAD_REFERENCE_PEAK_LOG10:+.2f} log10 g",
    )
    print(
        f"release normaliser: {RELEASE_LOG10}   "
        f"direct route efficiency: {efficiency}",
    )
    print("\ncurve   hand reservoir   direct dose/contact   dose/reservoir")
    for curve in curves:
        reservoir = _hand_reservoir(curve)
        dose = _direct_dose(curve, efficiency)
        print(
            f"{curve:5.1f}   {reservoir:14.4g}   {dose:19.4g}   "
            f"{dose / reservoir:14.4g}",
        )
    print(
        "\nThe ratio is independent of the curve value: it is "
        f"{efficiency} * 10^("
        f"{HAND_LOAD_LOG10_GEC - HAND_LOAD_REFERENCE_PEAK_LOG10:+.2f} "
        f"+ {RELEASE_LOG10}) / {HOURS_PER_DAY:.0f}.",
    )


def _report_composed(efficiency: float, peak: float) -> None:
    mouth = _hand_to_mouth_midpoint()
    shipped = _direct_dose(peak, efficiency)
    print(f"\nhand-to-mouth ingested fraction per contact: {mouth:.5f}")
    print("\ntransfer   composed/shipped   logs below   source")
    for transfer, label in TRANSFER_ARMS:
        composed = _hand_reservoir(peak) * transfer * mouth
        ratio = composed / shipped
        print(
            f"{transfer:8.2f}   {ratio:16.3g}   {-math.log10(ratio):10.2f}   "
            f"{label}",
        )


def _report_probability(efficiency: float, peak: float) -> None:
    mouth = _hand_to_mouth_midpoint()
    transfer = TRANSFER_ARMS[1][0]
    print("\nper-contact establishment probability, shipped Teunis")
    print("curve   shipped dose   P(inf)   composed dose   P(inf)")
    for curve in (peak, peak - 1.0, peak - 2.0):
        shipped = _direct_dose(curve, efficiency)
        composed = _hand_reservoir(curve) * transfer * mouth
        print(
            f"{curve:5.1f}   {shipped:12.4g}   {_p_infection(shipped):6.4f}   "
            f"{composed:13.4g}   {_p_infection(composed):6.4f}",
        )


def main() -> None:
    efficiency = _direct_efficiency()
    peak = max(SYMPTOMATIC_SHEDDING)
    curves = (peak, peak - 2.0, peak - 4.0)
    _report_ratio(efficiency, curves)
    _report_composed(efficiency, peak)
    _report_probability(efficiency, peak)


if __name__ == "__main__":
    main()
