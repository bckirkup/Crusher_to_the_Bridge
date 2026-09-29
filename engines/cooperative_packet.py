"""COVID-COOP-02: cooperative-packet dose-response arm.

Under the declared cooperative law a virion converts a cell only when it
arrives inside a carrier that delivers at least ``n_star`` copies
concurrently. Carrier occupancy per aerosol class is Poisson(mu_class)
per COVID-COOP-01 / COVID-PACKET-01, so the share of a class's delivered
copies that ride inside qualifying packets is
``P(K >= n_star | K ~ Poisson(mu_class)) / mu_class`` — the packet share
that weights the host's baseline independent-action hazard rate:

    lambda = sum_class  w_class * D_class
    w_dry/wet = tail(mu_class, n_star) / mu_class
    w_bolus   = 1.0
    P(inf)    = -expm1(-susceptibility_draw * lambda)

The susceptibility draw is unchanged (beta frailty + declared scale), so
an A/B against ``model: beta_poisson`` isolates the dose law alone.

Classes
-------
dry
    Far-field aerosol carriers: non-compartment zone pool, HVAC drift,
    emesis and flush aerosols. Declared occupancy envelope
    mu in [0.004, 0.1] (COVID-COOP-01).
wet
    Near carriers: compartment pool, cabin-mate addback, near-field
    plume. Declared occupancy envelope mu in [0.04, 500].
bolus
    Contact-family routes: direct contact, fomite, food, environmental.
    One carrier carries the whole transfer, so every copy is trivially
    inside a qualifying packet and the independent-action rate is
    retained (weight 1.0).
"""

from __future__ import annotations

import math

COOP_MODEL = "cooperative_packet"

COOP_CLASSES = ("dry", "wet", "bolus")

# Pathway dose keys → carrier class. The ``droplet`` lump is absent: it is
# split per engine sub-term (corridor pool → dry; compartment pool +
# cabin addback + near field → wet) into the agent's cooperative dose
# ledger. Pathways missing from the map classify ``dry`` — consistent
# with the packet instrument's "other" channel class.
PATHWAY_COOP_CLASS: dict[str, str] = {
    "direct_contact": "bolus",
    "fomite": "bolus",
    "food": "bolus",
    "environmental": "bolus",
    "hvac_airborne": "dry",
    "emesis_aerosol": "dry",
    "flush_aerosol": "dry",
}

_DROPLET_FALLBACK_CLASS = "wet"


def poisson_tail(mu: float, n: int) -> float:
    """P(K >= n) for K ~ Poisson(mu), summed stably from the low terms."""
    if n <= 0:
        return 1.0
    if mu <= 0.0:
        return 0.0
    term = math.exp(-mu)
    cumulative = term
    for k in range(1, n):
        term *= mu / k
        cumulative += term
    return max(0.0, min(1.0, 1.0 - cumulative))


def packet_share(mu: float, n_star: int) -> float:
    """Share of delivered copies riding inside >= n_star carriers.

    ``tail(mu, n_star) / mu`` is E[qualifying carriers] per copy: for the
    small far-field occupancies it collapses to ``mu**(n_star-1)/n!``,
    and it vanishes as ``1/mu`` for large loads because dose fuses into
    fewer, bigger infectious units.
    """
    return poisson_tail(mu, n_star) / mu


def coop_class_weights(dose_response: dict) -> dict[str, float]:
    """Per-class hazard weights for one pathogen's cooperative arm.

    Required dose_response fields beyond the shared beta draw
    (``alpha``, ``beta``, ``susceptibility_scale``): ``n_star`` (int >= 1)
    and ``carrier_loading`` = ``{"dry": mu_dry, "wet": mu_wet}``, point
    occupancies declared from the COVID-COOP-01 envelopes.
    """
    n_star = dose_response.get("n_star")
    if not isinstance(n_star, int) or isinstance(n_star, bool) or n_star < 1:
        raise ValueError(
            "cooperative_packet dose_response requires integer n_star >= 1",
        )
    loading = dose_response.get("carrier_loading")
    if not isinstance(loading, dict):
        raise ValueError(
            "cooperative_packet dose_response requires carrier_loading "
            "{'dry': mu, 'wet': mu}",
        )
    weights: dict[str, float] = {}
    for cls in ("dry", "wet"):
        mu = loading.get(cls)
        if (
            not isinstance(mu, (int, float))
            or isinstance(mu, bool)
            or not math.isfinite(mu)
            or mu <= 0.0
        ):
            raise ValueError(
                f"cooperative_packet carrier_loading['{cls}'] must be a "
                "finite number > 0",
            )
        weights[cls] = packet_share(float(mu), n_star)
    weights["bolus"] = 1.0
    return weights


def classify_pathway_doses(
    pathway_doses: dict[str, float],
    pathogen_id: str,
    coop_doses: dict[str, float] | None,
    p_dose: float,
) -> dict[str, float]:
    """Split one host's epoch dose into cooperative carrier classes.

    ``pathway_doses`` are the merged ``agent_pathway_doses[aid]`` entries
    keyed ``<pathway>:<pid>`` (bare names for ``_default``); they carry
    route-efficiency and NPI factors but not the host susceptibility
    multiplier, so non-droplet entries are rescaled by
    ``p_dose / sum(matched pathway doses)`` — the same
    post-factor convention the takeoff instrument uses. ``coop_doses``
    supplies the droplet class split already on the ``p_dose`` scale
    (keys ``dry:<pid>`` / ``wet:<pid>``).

    A droplet lump without a recorded split classifies ``wet``: measured
    droplet dose is dominated by the compartment/near-field terms, and
    the fallback leans toward the mechanism surviving rather than the
    arm suppressing.
    """
    suffix = f":{pathogen_id}"
    matched: dict[str, float] = {}
    for key, dose in pathway_doses.items():
        if key.endswith(suffix):
            matched[key[: -len(suffix)]] = matched.get(
                key[: -len(suffix)], 0.0,
            ) + dose
        elif ":" not in key:
            matched[key] = matched.get(key, 0.0) + dose
    pw_total = sum(matched.values())
    ratio = p_dose / pw_total if pw_total > 0.0 else 0.0

    classes = dict.fromkeys(COOP_CLASSES, 0.0)
    coop = coop_doses or {}
    coop_total = 0.0
    for cls in ("dry", "wet"):
        for key in (f"{cls}{suffix}", cls):
            value = coop.get(key)
            if value is not None:
                classes[cls] += value
                coop_total += value
                break
    droplet_lump = matched.pop("droplet", 0.0)
    if droplet_lump > 0.0 and coop_total <= 0.0:
        classes[_DROPLET_FALLBACK_CLASS] += droplet_lump * ratio
    for name, dose in matched.items():
        cls = PATHWAY_COOP_CLASS.get(name, "dry")
        classes[cls] += dose * ratio
    return classes
