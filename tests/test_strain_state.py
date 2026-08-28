"""Strain identity, per-pathogen strain config, and lineage census.

New seam, so these are bounds + graded-sensitivity tests rather than goldens
(skill ci-test-design). The behaviour lock for the rest of the simulator is
that nothing here is wired in yet: ``variant_surveillance.enabled`` is false.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

from engines.strain_state import (  # noqa: E402
    PHENOTYPE_AXES,
    Phenotype,
    PhenotypeEffectRanges,
    StrainConfigError,
    StrainEvolutionConfig,
    StrainRegistry,
    StrainState,
)
from tools.sanity_checker import (  # noqa: E402
    PathogensFile,
    Report,
    _check_strain_evolution,
    _check_variant_surveillance,
)

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore[assignment]

requires_jsonschema = pytest.mark.skipif(
    jsonschema is None, reason="jsonschema not installed",
)

NOROVIRUS_PROFILE = {
    "pathogen_id": "norwalk_gi",
    "strain_evolution": {
        "mutation_rate": 0.02,
        "phenotype_mutation_fraction": 0.05,
        "genotypes": ["GII.4", "GII.17"],
        "cross_immunity": {
            "GII.4": {"GII.4": 0.85, "GII.17": 0.18},
            "GII.17": {"GII.4": 0.18, "GII.17": 0.85},
        },
    },
}


# ── StrainState bounds ──────────────────────────────────────────────────

def test_founder_strain_has_no_parent_and_reference_phenotype():
    strain = StrainState(strain_id="norwalk_gi:1", pathogen_id="norwalk_gi")
    assert strain.is_founder
    assert strain.parent_strain_id is None
    assert not strain.recombinant
    assert strain.transmissibility_multiplier == pytest.approx(1.0)
    assert strain.generation == 0


def test_two_parents_marks_recombinant():
    strain = StrainState(
        strain_id="p:3",
        pathogen_id="p",
        parent_strain_ids=("p:1", "p:2"),
        origin="recombination",
    )
    assert strain.recombinant
    assert strain.parent_strain_id == "p:1"


def test_recombinant_origin_requires_exactly_two_parents():
    with pytest.raises(StrainConfigError, match="two parents"):
        StrainState(
            strain_id="p:3",
            pathogen_id="p",
            parent_strain_ids=("p:1",),
            origin="recombination",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("transmissibility_multiplier", 0.0),
        ("transmissibility_multiplier", -1.0),
        ("shedding_multiplier", 0.0),
        ("immune_escape", 1.5),
        ("immune_escape", -0.1),
        ("generation", -1),
        ("n_mutations", -1),
    ],
)
def test_out_of_range_phenotype_is_rejected(field, value):
    with pytest.raises(StrainConfigError):
        StrainState(strain_id="p:1", pathogen_id="p", **{field: value})


def test_unknown_origin_is_rejected():
    with pytest.raises(StrainConfigError, match="origin"):
        StrainState(strain_id="p:1", pathogen_id="p", origin="teleportation")


def test_shore_origin_is_a_first_class_strain_source():
    """The shore/port model reuses this identity rather than a parallel one."""
    strain = StrainState(
        strain_id="p:1",
        pathogen_id="p",
        origin="shore_import",
        source_location="risa",
    )
    assert strain.origin == "shore_import"
    assert strain.source_location == "risa"
    assert strain.to_telemetry()["source_location"] == "risa"


def test_telemetry_round_trips_through_json():
    strain = StrainState(
        strain_id="p:2",
        pathogen_id="p",
        genotype="GII.4",
        parent_strain_ids=("p:1",),
        origin="transmission",
    )
    blob = json.loads(json.dumps(strain.to_telemetry()))
    assert blob["parent_strain_ids"] == ["p:1"]
    assert blob["genotype"] == "GII.4"
    assert blob["recombinant"] is False


# ── registry ────────────────────────────────────────────────────────────

def test_ids_are_unique_monotone_and_pathogen_scoped():
    reg = StrainRegistry()
    first = reg.mint("norwalk_gi", genotype="GII.4")
    second = reg.mint("norwalk_gi", genotype="GII.17")
    other = reg.mint("sars_cov2_resp", genotype="omicron")
    assert (first.strain_id, second.strain_id) == ("norwalk_gi:1", "norwalk_gi:2")
    assert other.strain_id == "sars_cov2_resp:1"
    assert len(reg) == 3


def test_founders_are_tracked_per_pathogen():
    reg = StrainRegistry()
    reg.mint("norwalk_gi", genotype="GII.4")
    reg.mint("norwalk_gi", genotype="GII.17")
    reg.mint("sars_cov2_resp", genotype="delta")
    assert len(reg.founders("norwalk_gi")) == 2
    assert len(reg.founders("sars_cov2_resp")) == 1
    assert reg.founders("influenza_a") == ()


def test_duplicate_registration_is_rejected():
    reg = StrainRegistry()
    strain = reg.mint("p")
    with pytest.raises(StrainConfigError, match="duplicate"):
        reg.register(strain)


def test_unknown_parent_is_rejected():
    reg = StrainRegistry()
    with pytest.raises(StrainConfigError, match="unknown parent"):
        reg.mint("p", origin="transmission", parent_strain_ids=("p:99",))


def test_transmission_advances_generation_but_within_host_does_not():
    reg = StrainRegistry()
    founder = reg.mint("p", genotype="GII.4")
    child = reg.derive(founder, mutations_added=1)
    grandchild = reg.derive(child)
    within = reg.derive(grandchild, origin="within_host", mutations_added=1)

    assert (child.generation, grandchild.generation) == (1, 2)
    assert within.generation == grandchild.generation
    assert within.n_mutations == grandchild.n_mutations + 1


def test_derived_strain_inherits_phenotype_and_genotype():
    reg = StrainRegistry()
    founder = reg.mint(
        "p", genotype="GII.4", phenotype=Phenotype(immune_escape=0.2),
    )
    child = reg.derive(founder)
    assert child.genotype == "GII.4"
    assert child.immune_escape == pytest.approx(0.2)
    assert child.parent_strain_id == founder.strain_id

    mutant = reg.derive(
        founder,
        mutations_added=1,
        phenotype=Phenotype(transmissibility_multiplier=1.2, immune_escape=0.2),
    )
    assert mutant.transmissibility_multiplier == pytest.approx(1.2)
    assert mutant.immune_escape == pytest.approx(0.2)
    assert founder.transmissibility_multiplier == pytest.approx(1.0)


def test_lineage_root_walks_back_to_the_founder():
    reg = StrainRegistry()
    founder = reg.mint("p")
    tip = founder
    for _ in range(5):
        tip = reg.derive(tip)
    assert reg.lineage_root(tip.strain_id) == founder.strain_id
    assert reg.lineage_root(founder.strain_id) == founder.strain_id


def test_get_rejects_unknown_strain():
    reg = StrainRegistry()
    with pytest.raises(StrainConfigError, match="unknown strain"):
        reg.get("p:1")


# ── census ──────────────────────────────────────────────────────────────

def test_census_reports_diversity_and_dominance():
    reg = StrainRegistry()
    a = reg.mint("p")
    b = reg.derive(a)
    c = reg.derive(a)
    census = reg.census(4, "p", {a.strain_id: 6, b.strain_id: 3, c.strain_id: 1})
    assert census.total_carriers == 10
    assert census.num_lineages == 3
    assert census.dominant_strain_id == a.strain_id
    assert census.dominant_fraction == pytest.approx(0.6)


def test_census_drops_extinct_strains_and_other_pathogens():
    reg = StrainRegistry()
    a = reg.mint("p")
    extinct = reg.derive(a)
    other = reg.mint("q")
    census = reg.census(
        1, "p", {a.strain_id: 2, extinct.strain_id: 0, other.strain_id: 5},
    )
    assert set(census.lineage_counts) == {a.strain_id}
    assert census.total_carriers == 2


def test_empty_census_is_well_defined():
    reg = StrainRegistry()
    census = reg.census(0, "p", {})
    assert census.num_lineages == 0
    assert census.total_carriers == 0
    assert census.dominant_strain_id == ""
    assert census.dominant_fraction == pytest.approx(0.0)


def test_dominance_rises_as_one_lineage_sweeps():
    """Graded sensitivity: a sweeping lineage must show increasing dominance."""
    reg = StrainRegistry()
    a = reg.mint("p")
    b = reg.derive(a)
    fractions = []
    for epoch, (n_a, n_b) in enumerate([(5, 5), (7, 3), (9, 1)]):
        snap = reg.take_snapshot(epoch, "p", {a.strain_id: n_a, b.strain_id: n_b})
        fractions.append(snap.dominant_fraction)
    assert fractions == sorted(fractions)
    assert len(reg.snapshots("p")) == 3
    assert reg.snapshots("q") == ()


def test_registry_telemetry_is_json_serializable():
    reg = StrainRegistry()
    founder = reg.mint("p", genotype="GII.4")
    reg.derive(founder)
    reg.take_snapshot(0, "p", {founder.strain_id: 1})
    blob = json.loads(json.dumps(reg.to_telemetry()))
    assert len(blob["strains"]) == 2
    assert blob["founders"] == {"p": [founder.strain_id]}
    assert len(blob["snapshots"]) == 1


# ── StrainEvolutionConfig ───────────────────────────────────────────────

def test_absent_block_means_no_strain_structure():
    assert StrainEvolutionConfig.from_profile({"pathogen_id": "p"}) is None


def test_profile_block_parses_with_spec_values():
    cfg = StrainEvolutionConfig.from_profile(NOROVIRUS_PROFILE)
    assert cfg is not None
    assert cfg.mutation_rate == pytest.approx(0.02)
    assert cfg.phenotype_mutation_fraction == pytest.approx(0.05)
    assert cfg.within_host_mutation_rate == pytest.approx(0.0)
    assert cfg.genotypes == ("GII.4", "GII.17")


def test_prior_genotype_distribution_defaults_to_uniform_and_renormalizes():
    cfg = StrainEvolutionConfig.from_profile(NOROVIRUS_PROFILE)
    assert cfg.prior_genotype_distribution == {"GII.4": 0.5, "GII.17": 0.5}

    weighted = {
        "pathogen_id": "p",
        "strain_evolution": {
            "genotypes": ["a", "b"],
            "prior_genotype_distribution": {"a": 3.0, "b": 1.0},
        },
    }
    cfg2 = StrainEvolutionConfig.from_profile(weighted)
    assert cfg2.prior_genotype_distribution == pytest.approx({"a": 0.75, "b": 0.25})


def test_cross_immunity_lookup_and_escape_discount():
    cfg = StrainEvolutionConfig.from_profile(NOROVIRUS_PROFILE)
    same = StrainState(strain_id="p:1", pathogen_id="p", genotype="GII.4")
    escape = StrainState(
        strain_id="p:2", pathogen_id="p", genotype="GII.4", immune_escape=0.5,
    )
    assert cfg.protection("GII.4", "GII.4") == pytest.approx(0.85)
    assert cfg.protection("GII.4", "GII.17") == pytest.approx(0.18)
    assert cfg.protection("GII.4", "never_seen") == pytest.approx(0.0)
    assert cfg.effective_protection("GII.4", same) == pytest.approx(0.85)
    assert cfg.effective_protection("GII.4", escape) == pytest.approx(0.425)


def test_escape_monotonically_erodes_protection():
    cfg = StrainEvolutionConfig.from_profile(NOROVIRUS_PROFILE)
    protections = [
        cfg.effective_protection(
            "GII.4",
            StrainState(
                strain_id=f"p:{i}",
                pathogen_id="p",
                genotype="GII.4",
                immune_escape=escape,
            ),
        )
        for i, escape in enumerate((0.0, 0.25, 0.5, 1.0))
    ]
    assert protections == sorted(protections, reverse=True)
    assert protections[-1] == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("mutation_rate", 1.5),
        ("mutation_rate", -0.1),
        ("phenotype_mutation_fraction", 2.0),
        ("within_host_mutation_rate", -1.0),
        ("recombination_rate", 1.1),
        ("superinfection_susceptibility", -0.5),
        ("min_strain_fraction", 1.2),
    ],
)
def test_out_of_range_rates_are_rejected(key, value):
    profile = {
        "pathogen_id": "p",
        "strain_evolution": {"genotypes": ["a"], key: value},
    }
    with pytest.raises(StrainConfigError, match=key):
        StrainEvolutionConfig.from_profile(profile)


def test_empty_genotype_list_is_rejected():
    with pytest.raises(StrainConfigError, match="genotypes"):
        StrainEvolutionConfig.from_profile(
            {"pathogen_id": "p", "strain_evolution": {"genotypes": []}},
        )


def test_cross_immunity_must_reference_declared_genotypes():
    with pytest.raises(StrainConfigError, match="unknown prior genotype"):
        StrainEvolutionConfig.from_profile({
            "pathogen_id": "p",
            "strain_evolution": {
                "genotypes": ["a"],
                "cross_immunity": {"zzz": {"a": 0.5}},
            },
        })
    with pytest.raises(StrainConfigError, match="unknown challenge genotype"):
        StrainEvolutionConfig.from_profile({
            "pathogen_id": "p",
            "strain_evolution": {
                "genotypes": ["a"],
                "cross_immunity": {"a": {"zzz": 0.5}},
            },
        })


def test_cross_immunity_entries_must_be_probabilities():
    with pytest.raises(StrainConfigError, match=r"cross_immunity\[a\]\[a\]"):
        StrainEvolutionConfig.from_profile({
            "pathogen_id": "p",
            "strain_evolution": {
                "genotypes": ["a"],
                "cross_immunity": {"a": {"a": 1.4}},
            },
        })


def test_prior_distribution_must_reference_declared_genotypes_and_be_positive():
    with pytest.raises(StrainConfigError, match="unknown genotype"):
        StrainEvolutionConfig.from_profile({
            "pathogen_id": "p",
            "strain_evolution": {
                "genotypes": ["a"],
                "prior_genotype_distribution": {"zzz": 1.0},
            },
        })
    with pytest.raises(StrainConfigError, match="sums to zero"):
        StrainEvolutionConfig.from_profile({
            "pathogen_id": "p",
            "strain_evolution": {
                "genotypes": ["a"],
                "prior_genotype_distribution": {"a": 0.0},
            },
        })


def test_effect_ranges_default_and_validate():
    default = PhenotypeEffectRanges()
    assert default.transmissibility[0] < 1.0 < default.transmissibility[1]
    with pytest.raises(StrainConfigError, match="inverted"):
        PhenotypeEffectRanges.from_config({"shedding": [1.5, 0.5]})
    with pytest.raises(StrainConfigError, match="pair"):
        PhenotypeEffectRanges.from_config({"shedding": [1.0]})
    with pytest.raises(StrainConfigError, match="immune_escape"):
        PhenotypeEffectRanges.from_config({"immune_escape": [0.0, 1.4]})


def test_phenotype_axes_match_the_spec():
    assert set(PHENOTYPE_AXES) == {
        "transmissibility", "shedding", "incubation", "immune_escape",
    }


# ── shipped configuration ───────────────────────────────────────────────

PROFILE_FILES = sorted((REPO_ROOT / "data" / "pathogens").glob("*.json"))


@pytest.mark.parametrize("path", PROFILE_FILES, ids=lambda p: p.name)
def test_shipped_profiles_have_loadable_strain_blocks(path):
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    for profile in doc.get("pathogens", []):
        cfg = StrainEvolutionConfig.from_profile(profile)
        if cfg is None:
            continue
        assert cfg.genotypes, profile["pathogen_id"]
        for prior in cfg.cross_immunity:
            assert prior in cfg.genotypes
        assert set(cfg.prior_genotype_distribution) <= set(cfg.genotypes)


def test_trek_pathogens_are_more_mutationally_dynamic_than_real_ones():
    """Spec §1.3 makes this an explicit modelling claim; lock it."""
    rates = {}
    for path in PROFILE_FILES:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        for profile in doc.get("pathogens", []):
            cfg = StrainEvolutionConfig.from_profile(profile)
            if cfg is not None:
                rates[cfg.pathogen_id] = cfg.mutation_rate
    assert rates["psi_2000_polywater"] > rates["norwalk_gi"]
    assert rates["rigelian_fever"] > rates["measles_virus"]


def test_variant_surveillance_is_off_by_default():
    with open(REPO_ROOT / "crusher_labs" / "config.yaml", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    block = cfg["variant_surveillance"]
    assert block["enabled"] is False
    assert block["founder_strains_per_pathogen"] >= 1
    assert block["census_interval_hours"] >= 1


# ── schema ──────────────────────────────────────────────────────────────

def _profiles_schema():
    path = REPO_ROOT / "schemas" / "pathogen_profiles.schema.json"
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _validate_block(block):
    """Validate a bare strain_evolution block against the shipped schema."""
    full = _profiles_schema()
    schema = {
        "$schema": full["$schema"],
        "$defs": full["$defs"],
        "$ref": "#/$defs/StrainEvolution",
    }
    jsonschema.validate(instance=block, schema=schema)


@requires_jsonschema
def test_schema_accepts_a_full_strain_block():
    _validate_block({
        "mutation_rate": 0.02,
        "phenotype_mutation_fraction": 0.05,
        "within_host_mutation_rate": 0.001,
        "recombination_rate": 0.01,
        "superinfection_susceptibility": 0.1,
        "genotypes": ["GII.4"],
        "prior_genotype_distribution": {"GII.4": 1.0},
        "cross_immunity": {"GII.4": {"GII.4": 0.85}},
        "effect_ranges": {"transmissibility": [0.8, 1.25]},
        "min_strain_fraction": 0.001,
        "notes": "placeholder",
    })


@pytest.mark.parametrize("block", [
    {"genotypes": ["a"], "mutation_rate": 1.5},
    {"genotypes": ["a"], "superinfection_susceptibility": -0.1},
    {"genotypes": []},
    {"mutation_rate": 0.02},
    {"genotypes": ["a"], "effect_ranges": {"transmissibility": [0.8]}},
    {"genotypes": ["a"], "effect_ranges": {"nonsense": [0.8, 1.2]}},
    {"genotypes": ["a"], "unexpected_key": 1},
])
@requires_jsonschema
def test_schema_rejects_malformed_strain_blocks(block):
    with pytest.raises(jsonschema.ValidationError):
        _validate_block(block)


# ── sanity checker ──────────────────────────────────────────────────────

def test_sanity_checker_rejects_invalid_strain_block():
    good = PathogensFile.model_validate(
        {"pathogens": [{**NOROVIRUS_PROFILE, "name": "Norwalk"}]},
    )
    report = Report()
    _check_strain_evolution(good, report)
    assert report.passed

    bad_profile = {
        "pathogen_id": "p",
        "name": "P",
        "strain_evolution": {"genotypes": ["a"], "mutation_rate": 4.0},
    }
    bad = PathogensFile.model_validate({"pathogens": [bad_profile]})
    report = Report()
    _check_strain_evolution(bad, report)
    assert [f.rule for f in report.errors] == ["STRAIN_CONFIG"]


def test_sanity_checker_warns_when_recombination_is_unreachable():
    profile = {
        "pathogen_id": "p",
        "name": "P",
        "strain_evolution": {
            "genotypes": ["a"],
            "mutation_rate": 0.02,
            "phenotype_mutation_fraction": 0.05,
            "recombination_rate": 0.01,
            "superinfection_susceptibility": 0.0,
        },
    }
    report = Report()
    _check_strain_evolution(PathogensFile.model_validate({"pathogens": [profile]}), report)
    assert report.passed
    assert any("no recombination is reachable" in f.message for f in report.warnings)


def test_sanity_checker_warns_on_inert_mutation_rates():
    inert = {
        "pathogen_id": "p", "name": "P",
        "strain_evolution": {"genotypes": ["a"]},
    }
    report = Report()
    _check_strain_evolution(PathogensFile.model_validate({"pathogens": [inert]}), report)
    assert any("never diversify" in f.message for f in report.warnings)

    label_only = {
        "pathogen_id": "p", "name": "P",
        "strain_evolution": {"genotypes": ["a"], "mutation_rate": 0.02},
    }
    report = Report()
    _check_strain_evolution(
        PathogensFile.model_validate({"pathogens": [label_only]}), report,
    )
    assert any("phenotype cannot" in f.message for f in report.warnings)


@pytest.mark.parametrize("block", [
    {"founder_strains_per_pathogen": 0},
    {"census_interval_epochs": 0},
])
def test_sanity_checker_rejects_invalid_variant_surveillance_config(block):
    report = Report()
    _check_variant_surveillance({"variant_surveillance": block}, report)
    assert [f.rule for f in report.errors] == ["MATH_BOUND"]


def test_sanity_checker_accepts_absent_variant_surveillance_block():
    report = Report()
    _check_variant_surveillance({}, report)
    assert report.passed
