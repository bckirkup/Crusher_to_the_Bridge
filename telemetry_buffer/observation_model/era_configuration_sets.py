"""Pre-2020 and post-2020 configuration sets for the A7 arms (task #10).

``vsp_covid_discontinuity_design.md`` §7 fixes the order: the common dose is
fitted on the **pre** arm alone, the **post** arm then runs at that same dose
with an independently constructed operational configuration, and A7 is scored
as a prediction.  This module is that configuration, and it is the only place
the two arms are allowed to differ.

Three rules it enforces mechanically, because #11 must not be able to break
them by accident:

1. **No lever has a value.**  Every quantity that differs between the eras is
   a swept span --- a sourced interval where a measurement bounds it, a
   declared axis where nothing does --- and ``era_config_patch`` refuses to
   build a patch unless the caller states a coordinate in [0, 1] for every
   swept lever of that era.  There is no default coordinate and no midpoint,
   so no era ever silently acquires a point value.
2. **Coverage, compliance and route efficacy stay separate.**  The buffet-entry
   prompt is not one hygiene multiplier.  How many passengers are reminded
   (coverage), how many act on the reminder (compliance), what the action
   removes (``removal_log10``, the one sourced part) and how much of the
   host's hand-mediated dose passes through the washed state (``hand_share``)
   are four levers, and the arms of soap and alcohol rub are separate
   measures with separate removals.
3. **An NPI is not the ship's plant.**  Filtration is ``hvac.filter_efficiency``
   and immunity is ``ship_graph.immune_fraction``; neither is expressed as a
   dose-reduction measure, so a change to either cannot be double-counted
   through the NPI interface (#9).

What is *not* here is as much of the content as what is.  Every mechanism in
``post_covid_configuration_sources.md`` §3 that the sources describe
qualitatively appears below as an ``UNREPRESENTED`` lever carrying the reason,
so #11 cannot report "the post-2020 configuration was applied" while silently
meaning four of its nine documented components were dropped.

Two findings fell out of building it, and neither is a tuning knob:

* The shipped ``hvac.filter_efficiency`` of 0.50, whose comment labels it
  ``MERV-13``, lies inside **neither** era's sourced span.  The Healthy Sail
  Panel's own figures put MERV 8 at 30% and MERV 13 at 90%, so 0.50 is above
  any pre-2020 filter and below the post-2020 one it is named after --- a
  post-pandemic label on a value that matches no filter, carried by an arm
  whose anchors are overwhelmingly pre-2020.
* The soap-versus-rub gap that makes the post-2020 hand-hygiene push near-null
  for norovirus is a gap in **genomic copies**.  On infectious MNV1, Tuladhar's
  own intervals overlap (soap >3.0 ± 0.4 against rub 2.8 ± 1.5), so the two
  arms are only separated by the endpoint that is not what the model's dose
  axis counts.  Both arms are therefore carried at their infectious-titre
  spans, which is the *weaker* separation, and the wider genomic gap is
  recorded but not used.

Usage::

    PYTHONPATH=. python3 telemetry_buffer/observation_model/era_configuration_sets.py

Nothing here is fitted, and no span was chosen because it reproduces A7.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, NamedTuple

ERAS: tuple[str, ...] = ("pre", "post")

# Lever kinds.  The first two are swept and need a coordinate; the last three
# carry no number into a run and exist so the omission is on the record.
SOURCED_INTERVAL = "sourced_interval"
DECLARED_AXIS = "declared_axis"
INHERITED_POINT = "inherited_point"
IDENTITY = "identity"
UNREPRESENTED = "unrepresented"

SWEPT_KINDS: frozenset[str] = frozenset({SOURCED_INTERVAL, DECLARED_AXIS})

# The config key the NPI interface (#9) reads.
_NPI_KEY = "non_pharmaceutical_interventions"


class Span(NamedTuple):
    """A closed interval a lever is swept over.  Never collapsed to a point."""

    lo: float
    hi: float


@dataclass(frozen=True)
class Lever:
    """One quantity that may differ between the pre-2020 and post-2020 arms.

    ``path`` is the dotted config key the value lands on, or ``""`` for an
    input that is composed into a measure rather than written directly.
    ``grade`` and ``origin`` use the register's vocabulary
    (``docs/parameter_provenance_register.md`` §1), and they are separate on
    purpose: an industry report read in full is still ``Tr``.
    """

    name: str
    path: str
    kind: str
    span: Span | None
    value: float | None
    source: str
    grade: str
    origin: str
    note: str

    def __post_init__(self) -> None:
        if self.kind in SWEPT_KINDS:
            self._check_swept()
        elif self.kind == INHERITED_POINT and self.value is None:
            raise ValueError(f"{self.name}: an inherited point needs a value")
        elif self.kind not in {
            SOURCED_INTERVAL, DECLARED_AXIS, INHERITED_POINT,
            IDENTITY, UNREPRESENTED,
        }:
            raise ValueError(f"{self.name}: unknown lever kind {self.kind!r}")
        if not self.note:
            raise ValueError(f"{self.name}: a lever must carry its reasoning")

    def _check_swept(self) -> None:
        if self.span is None:
            raise ValueError(f"{self.name}: a swept lever needs a span")
        if not math.isfinite(self.span.lo) or not math.isfinite(self.span.hi):
            raise ValueError(f"{self.name}: span must be finite")
        if self.span.hi <= self.span.lo:
            raise ValueError(f"{self.name}: span must be non-degenerate")
        if self.value is not None:
            raise ValueError(f"{self.name}: a swept lever has no value")
        if not self.source:
            raise ValueError(f"{self.name}: a swept lever needs a source")


# --------------------------------------------------------------------------
# Sources.  Written once, referenced by every lever that rests on them.
# --------------------------------------------------------------------------

HSP = (
    "Healthy Sail Panel Recommendations 29-31 (Royal Caribbean Group / "
    "Norwegian Cruise Line Holdings expert panel, 2020-09-21): MERV 8 is 30% "
    "efficient over 3.0-10.0 um, MERV 13 is 90% efficient over 0.3-1 um, and "
    "all operators are asked to upgrade to MERV 13. Industry-reported, not "
    "peer-reviewed."
)
TULADHAR = (
    "Tuladhar et al. 2015, J Hosp Infect, finger-pad tests, 30 s: soap and "
    "water removed >3.0 +/- 0.4 log10 infectious MNV1 against 2.8 +/- 1.5 "
    "log10 for alcohol rub; on genomic copies soap removed 4 log10 GII.4 "
    "against >3.3 for propanol rub."
)
BANSAGHI = (
    "Bansaghi et al. 2025, Open Res Europe, four-arm trial aboard Celestyal "
    "Olympia: no intervention arm produced measurable behavioural change; "
    "observed use was 7.6 soap and 1.6 hand-rub doses per person per day, and "
    "compliance is attributed to dispenser placement and to whether "
    "passengers are actively reminded. Qualitative for the prompt; it "
    "measures no dose reduction and no per-entry coverage."
)
IMMUNITY_DEBT = (
    "O'Reilly et al. 2021, BMC Medicine (England) and Lappe et al. 2023, BMC "
    "Infect Dis (US, >2-fold projected community incidence at full contact "
    "resumption): fitted community models, so the direction of the change is "
    "supported and no shipboard immune fraction is measured."
)
KORKIN = (
    "Inherited from the upstream Korkin Java model (Ship.java IMMUNE_RATIO); "
    "no measurement behind the transfer."
)

# Soap and rub are carried at their *infectious*-titre spans, which is the
# narrower separation of the two Tuladhar reports.  Tuladhar's soap figure is
# a censored lower bound (">3.0"), so the span's upper end is the point the
# 0.4 s.d. reaches, not an extrapolation past the censoring.
_SOAP_REMOVAL = Span(2.6, 3.4)
_RUB_REMOVAL = Span(1.3, 4.3)


def _hygiene_arm_levers(
    arm: str, removal: Span, source: str, extra: str,
) -> tuple[Lever, ...]:
    """The four levers of one buffet-entry hand-hygiene arm.

    Split because collapsing them is the specific defect the interface was
    built to prevent: a single "hygiene multiplier" cannot say whether a null
    result came from nobody complying or from the action not working.
    """
    prefix = f"npi.{arm}"
    return (
        Lever(
            name=f"{prefix}.coverage_passenger",
            path=f"{_NPI_KEY}.{arm}.coverage_by_role.passenger",
            kind=DECLARED_AXIS, span=Span(0.0, 1.0), value=None,
            source=BANSAGHI, grade="C", origin="R",
            note=(
                "Share of passengers the attendant actually reminds. The "
                "mechanism is qualitatively supported and the number is not "
                "measured anywhere, so the axis spans its whole range and "
                "0.0 --- the prompt reaching nobody --- stays admissible."
            ),
        ),
        Lever(
            name=f"{prefix}.compliance",
            path=f"{_NPI_KEY}.{arm}.compliance",
            kind=DECLARED_AXIS, span=Span(0.0, 1.0), value=None,
            source=BANSAGHI, grade="C", origin="R",
            note=(
                "Share of reminded passengers who take the action. Bansaghi "
                "reports doses per person per day, not acts per buffet "
                "entry, so it bounds nothing here."
            ),
        ),
        Lever(
            name=f"{prefix}.removal_log10",
            path="",
            kind=SOURCED_INTERVAL, span=removal, value=None,
            source=source, grade="B", origin="R",
            note=(
                "log10 removal of infectious virus by one act, measured on "
                "finger pads with a surrogate. " + extra
            ),
        ),
        Lever(
            name=f"{prefix}.hand_share",
            path="",
            kind=DECLARED_AXIS, span=Span(0.0, 1.0), value=None,
            source="declared: no source bounds it",
            grade="C", origin="Tr",
            note=(
                "Share of the host's hand-mediated dose that passes through "
                "the washed state --- one act at one doorway cannot touch the "
                "rest of the voyage. Unmeasured, and it is what converts a "
                "per-act removal into a route multiplier, so it is declared "
                "rather than borrowed from the removal figure."
            ),
        ),
    )


_FILTER_PRE = Lever(
    name="hvac.filter_efficiency",
    path="hvac.filter_efficiency",
    kind=SOURCED_INTERVAL, span=Span(0.0, 0.30), value=None,
    source=HSP, grade="C", origin="Tr",
    note=(
        "The model's eta is one scalar with no particle size, and the source "
        "reports each filter at one band. 30% is MERV 8 at 3-10 um, its "
        "coarsest and therefore best band, so it is a ceiling across the "
        "aerosol rather than a central value; the floor is 0 because MERV 8 "
        "is not rated below 1 um at all. Declared monotonicity in particle "
        "size above 0.3 um is the assumption that makes the ceiling one."
    ),
)
_FILTER_POST = Lever(
    name="hvac.filter_efficiency",
    path="hvac.filter_efficiency",
    kind=SOURCED_INTERVAL, span=Span(0.90, 0.99), value=None,
    source=HSP, grade="C", origin="Tr",
    note=(
        "90% is MERV 13 at 0.3-1 um, its *worst* band, so under the same "
        "declared monotonicity it is a floor rather than a ceiling. The "
        "upper end stops short of 1.0 because no filter removes everything "
        "and HEPA was not fleet-wide."
    ),
)

_ACH = Lever(
    name="hvac.air_changes_per_hour",
    path="",
    kind=UNREPRESENTED, span=None, value=None,
    source=HSP, grade="C", origin="Tr",
    note=(
        "Recommendation 30's >=6 ACH in occupied spaces is quantified and "
        "has nowhere to land: the native transport carries "
        "hvac.natural_decay_rate, which lumps settling with inactivation, "
        "and ventilation itself only enters through a CONTAM airflow "
        "network. Configuring the post arm's ventilation would need an "
        "engine change, so the post arm does not have it."
    ),
)

_IMMUNE_PRE = Lever(
    name="ship_graph.immune_fraction",
    path="ship_graph.immune_fraction",
    kind=INHERITED_POINT, span=None, value=0.2,
    source=KORKIN, grade="C", origin="Tr",
    note=(
        "The pre-2020 level is not sourced and is not made so here: it is "
        "the inherited 0.2, and it is the level the common dose is fitted "
        "*at*, so it is a construction choice of the fit rather than a "
        "measurement. Only the post/pre contrast below is evidenced."
    ),
)
_IMMUNE_POST = Lever(
    name="ship_graph.immune_fraction",
    path="ship_graph.immune_fraction",
    kind=DECLARED_AXIS, span=Span(0.0, 0.2), value=None,
    source=IMMUNITY_DEBT, grade="C", origin="R",
    note=(
        "Susceptibility rose because exposure stopped, so the post-2020 "
        "immune fraction is bounded above by the pre-2020 level and below by "
        "zero. The sign is sourced and the magnitude is not, which is why "
        "this is an axis over the whole span and not a scaled version of "
        "either paper's incidence ratio --- a community incidence multiplier "
        "is not a shipboard immune fraction. It pushes A7 the opposite way "
        "to every NPI here, and folding it into an NPI multiplier would let "
        "the two cancel invisibly."
    ),
)


def _unrepresented(name: str, note: str, source: str) -> Lever:
    return Lever(
        name=name, path="", kind=UNREPRESENTED, span=None, value=None,
        source=source, grade="C", origin="Tr", note=note,
    )


_QUALITATIVE_POST: tuple[Lever, ...] = (
    _unrepresented(
        "buffet.staff_assisted_service",
        "Self-service replaced by staff-assisted serving lines. Directly "
        "norovirus-relevant on the shared-utensil route and no efficacy "
        "measurement exists, so it cannot enter as a multiplier. It is also "
        "partly takeoff-preventing, which A7 cannot see.",
        "post_covid_configuration_sources.md 3: trade-press and operator "
        "protocol documents; no measurement.",
    ),
    _unrepresented(
        "isolation.capacity_fraction",
        "Convertible-cabin blocks adjacent to the medical centre, with a "
        ">=5% of occupancy recommendation (Buildings 13:2350, 2023). The "
        "model has no isolation-capacity ceiling to raise: confinement is "
        "unbounded, so a capacity change has no field. Tail-capping, so its "
        "absence biases A7d specifically.",
        "Musio-Sale et al., NAV 2022; Buildings 13:2350, 2023.",
    ),
    _unrepresented(
        "surfaces.touchless_fittings",
        "Touchless fittings, crew/passenger zoning and cleanable materials: "
        "direction clear, magnitude unmeasured, trade-press sourcing only.",
        "post_covid_configuration_sources.md 3.",
    ),
    _unrepresented(
        "embarkation.preboarding_screening",
        "Pre-boarding screening and denial of boarding is takeoff-preventing "
        "by construction: it removes introductions, so it moves the posting "
        "count (A7e, never scored) and leaves the conditional statistics "
        "A7a-A7d untouched. Omitting it is the correct treatment for A7, not "
        "a gap --- but it makes A7c a lower bound on total NPI effect.",
        "post_covid_configuration_sources.md 1 and 3.",
    ),
    _unrepresented(
        "transmission.surface_cleaning",
        "Enhanced cleaning is the most-publicised post-2020 change and the "
        "least usable: the schedule is one coverage and one log10 reduction "
        "for the whole ship, no source gives a post-2020 coverage or "
        "frequency, and the routine figures already in config are measured "
        "pre-2020. Changing them would be inventing the discontinuity in the "
        "plant.",
        "post_covid_configuration_sources.md 3 and 5.",
    ),
)

_NPI_PRE = Lever(
    name=_NPI_KEY,
    path="",
    kind=IDENTITY, span=None, value=None,
    source="construction",
    grade="X", origin="Tr",
    note=(
        "The pre-2020 arm carries no measure, which is not a claim that "
        "pre-2020 ships had no hand hygiene. Whatever baseline hygiene "
        "existed is inside the dose the pre arm fits, so representing it "
        "again as a reduction would remove it twice."
    ),
)


PRE_LEVERS: tuple[Lever, ...] = (_FILTER_PRE, _IMMUNE_PRE, _ACH, _NPI_PRE)

POST_LEVERS: tuple[Lever, ...] = (
    (_FILTER_POST, _IMMUNE_POST, _ACH)
    + _hygiene_arm_levers(
        "buffet_entry_handwash_prompt", _SOAP_REMOVAL, TULADHAR,
        "Soap and water on infectious MNV1; the reported >3.0 is censored, "
        "so the span is the stated s.d. around it and not an extrapolation.",
    )
    + _hygiene_arm_levers(
        "buffet_entry_sanitizer_prompt", _RUB_REMOVAL, TULADHAR,
        "Alcohol rub on infectious MNV1, where the +/- 1.5 s.d. makes the "
        "arm overlap soap. The wide soap-versus-rub gap is on genomic "
        "copies, an endpoint the dose axis does not count, so it is not "
        "used to separate the arms here.",
    )
    + _QUALITATIVE_POST
)

_LEVERS_BY_ERA: dict[str, tuple[Lever, ...]] = {
    "pre": PRE_LEVERS,
    "post": POST_LEVERS,
}

_HYGIENE_ARMS: tuple[str, ...] = (
    "buffet_entry_handwash_prompt",
    "buffet_entry_sanitizer_prompt",
)

# The routes one act at the buffet doorway can touch: both are hand-mediated
# and neither is the plant.  Applying one hand_share to both is declared, and
# is why hand_share is per arm rather than per route.
_HYGIENE_ROUTES: tuple[str, ...] = ("fomite", "food_contamination")


def levers(era: str) -> tuple[Lever, ...]:
    """Every lever of one era, swept and unrepresented alike."""
    if era not in _LEVERS_BY_ERA:
        raise ValueError(f"unknown era {era!r}; expected one of {ERAS}")
    return _LEVERS_BY_ERA[era]


def swept_lever_names(era: str) -> tuple[str, ...]:
    """Names a caller must supply a coordinate for, in declaration order."""
    return tuple(
        lever.name for lever in levers(era) if lever.kind in SWEPT_KINDS
    )


def _coordinate(name: str, coordinates: Mapping[str, float]) -> float:
    raw = coordinates[name]
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(f"coordinate {name} must be a number, got {raw!r}")
    position = float(raw)
    if not math.isfinite(position) or not 0.0 <= position <= 1.0:
        raise ValueError(f"coordinate {name} must lie in [0, 1], got {raw!r}")
    return position


def resolve(era: str, coordinates: Mapping[str, float]) -> dict[str, float]:
    """Place every swept lever of ``era`` at the caller's coordinates.

    A coordinate is a position in [0, 1] along the lever's span, so a caller
    has to say where in the box it is standing.  Missing and unknown names are
    both errors: silently defaulting a coordinate is how a swept axis becomes
    a point value nobody chose.
    """
    required = set(swept_lever_names(era))
    supplied = set(coordinates)
    missing = sorted(required - supplied)
    if missing:
        raise ValueError(
            f"{era}: no coordinate for {', '.join(missing)}; every swept "
            "lever needs one and there is no default",
        )
    unknown = sorted(supplied - required)
    if unknown:
        raise ValueError(f"{era}: unknown lever(s) {', '.join(unknown)}")
    placed: dict[str, float] = {}
    for lever in levers(era):
        if lever.kind not in SWEPT_KINDS or lever.span is None:
            continue
        position = _coordinate(lever.name, coordinates)
        span = lever.span
        placed[lever.name] = span.lo + position * (span.hi - span.lo)
    return placed


def hygiene_multiplier(removal_log10: float, hand_share: float) -> float:
    """Surviving fraction of a hand-mediated route under one hygiene act.

    Removal is measured per act on a finger pad; the route multiplier is the
    share of the route's dose that never met the act plus the share that did
    and survived it.  With ``hand_share`` at 0 the act is applied to none of
    the route and the multiplier is exactly 1.0, so an unsupported efficacy
    cannot manufacture a reduction on its own.
    """
    if not 0.0 <= hand_share <= 1.0:
        raise ValueError(f"hand_share must lie in [0, 1], got {hand_share!r}")
    if removal_log10 < 0.0:
        raise ValueError(
            f"removal_log10 must be non-negative, got {removal_log10!r}",
        )
    surviving_when_acted = math.pow(10.0, -removal_log10)
    return (1.0 - hand_share) + hand_share * surviving_when_acted


def _hygiene_measure(
    arm: str, placed: Mapping[str, float], source: str,
) -> dict[str, Any]:
    multiplier = hygiene_multiplier(
        placed[f"npi.{arm}.removal_log10"],
        placed[f"npi.{arm}.hand_share"],
    )
    return {
        "source": source,
        "coverage_by_role": {
            "passenger": placed[f"npi.{arm}.coverage_passenger"],
            # The attendant is posted at the passenger buffet entrance; crew
            # messing is a different service with no documented prompt, so
            # crew coverage is 0 by construction rather than by sweep.
            "crew": 0.0,
        },
        "compliance": placed[f"npi.{arm}.compliance"],
        "reference_multipliers": dict.fromkeys(_HYGIENE_ROUTES, multiplier),
    }


def _assign(patch: dict[str, Any], path: str, value: float) -> None:
    keys = path.split(".")
    cursor = patch
    for key in keys[:-1]:
        cursor = cursor.setdefault(key, {})
    cursor[keys[-1]] = value


def era_config_patch(
    era: str, coordinates: Mapping[str, float],
) -> dict[str, Any]:
    """Config overlay for one arm at one point of the swept box.

    The result is a nested overlay to merge onto ``config.yaml``, carrying
    only the keys the era actually changes.  The pre arm returns no
    ``non_pharmaceutical_interventions`` key at all --- absence, not an empty
    block --- so the engine's identity path is the one that runs.
    """
    placed = resolve(era, coordinates)
    patch: dict[str, Any] = {}
    for lever in levers(era):
        # NPI paths are documentation of where a lever lands; the block itself
        # is composed below, because a route multiplier is a function of two
        # levers rather than one of them written through.
        if not lever.path or lever.path.startswith(_NPI_KEY):
            continue
        if lever.kind == INHERITED_POINT and lever.value is not None:
            _assign(patch, lever.path, lever.value)
        elif lever.name in placed:
            _assign(patch, lever.path, placed[lever.name])
    if era == "post":
        patch[_NPI_KEY] = {
            arm: _hygiene_measure(arm, placed, TULADHAR)
            for arm in _HYGIENE_ARMS
        }
    return patch


def _fmt_span(lever: Lever) -> str:
    if lever.span is not None:
        return f"[{lever.span.lo:g}, {lever.span.hi:g}]"
    if lever.value is not None:
        return f"{lever.value:g} (not swept)"
    return "--"


def markdown_table(era: str) -> list[str]:
    """One era's levers as a markdown table, for the findings document."""
    rows = [
        f"### {era}-2020 levers",
        "",
        "| lever | kind | swept over | grade | origin |",
        "|---|---|---|---|---|",
    ]
    rows.extend(
        f"| `{lever.name}` | {lever.kind} | {_fmt_span(lever)} "
        f"| {lever.grade} | {lever.origin} |"
        for lever in levers(era)
    )
    rows.append("")
    return rows


def main() -> None:
    """Print both arms, and the corners of the post-2020 box."""
    lines: list[str] = ["# Era configuration sets (#10)", ""]
    for era in ERAS:
        lines.extend(markdown_table(era))
        lines.append(
            f"Swept levers requiring a coordinate: "
            f"{len(swept_lever_names(era))}",
        )
        lines.append("")
    corners = {
        "no NPI effect, immunity unchanged": dict.fromkeys(
            swept_lever_names("post"), 0.0,
        ) | {"ship_graph.immune_fraction": 1.0},
        "maximum NPI effect, immunity lost": dict.fromkeys(
            swept_lever_names("post"), 1.0,
        ) | {"ship_graph.immune_fraction": 0.0},
    }
    for label, coordinates in corners.items():
        patch = era_config_patch("post", coordinates)
        npi = patch[_NPI_KEY]
        lines.append(f"- **{label}**: eta = "
                     f"{patch['hvac']['filter_efficiency']:.3f}, "
                     f"immune = {patch['ship_graph']['immune_fraction']:.3f}, "
                     f"soap fomite multiplier = "
                     f"{npi['buffet_entry_handwash_prompt']['reference_multipliers']['fomite']:.4f}"
                     )
    print("\n".join(lines))


if __name__ == "__main__":
    main()
