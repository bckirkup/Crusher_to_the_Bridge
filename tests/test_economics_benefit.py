"""Afloat and shore benefit stay separate, and shore comes from the shore model.

The invariants worth defending here are that shore benefit is *adopted* from
the shore counterfactual rather than re-derived, that a detection lead is
reported in physical hours, and that the shore:afloat ratio in cases is
independent of the valuation while the dollar ratio is not.
"""

from __future__ import annotations

import pytest

from picard_framework.analysis.economics import (
    COMMUNITIES,
    COMMUNITY_AFLOAT,
    COMMUNITY_SHORE,
    DEFAULT_COMMUNITY_WEIGHTS,
    PAYER_PORT_AUTHORITY,
    PAYER_PUBLIC_HEALTH_AGENCY,
    PAYER_SHIP_OPERATOR,
    UNIT_VALUATION,
    VALUATION_PROVENANCE,
    AfloatBenefit,
    BenefitValuation,
    ShoreBenefit,
    benefit_split,
    payer_benefit_usd,
)
from picard_framework.analysis.sentinel.port_health import PortSurveillanceCapability
from picard_framework.analysis.shore import (
    PortCallImportation,
    ShoreRenewalParameters,
    evaluate_counterfactual,
)

VALUATION = BenefitValuation(
    usd_per_case_afloat=1_000.0,
    usd_per_case_ashore=500.0,
    provenance=VALUATION_PROVENANCE,
)


class TestAfloatBenefit:
    """Paired differences, including the unwelcome ones."""

    def test_defaults_are_a_no_benefit_control(self) -> None:
        assert AfloatBenefit().cases_averted == pytest.approx(0.0)

    def test_a_harmful_arm_reports_a_negative_difference(self) -> None:
        assert AfloatBenefit(cases_averted=-4.0).cases_averted == pytest.approx(-4.0)

    @pytest.mark.parametrize(
        "field",
        [
            "cases_averted",
            "symptomatic_person_hours_averted",
            "operational_impact_averted",
            "intervention_usd_averted",
        ],
    )
    def test_non_finite_differences_are_refused(self, field: str) -> None:
        with pytest.raises(ValueError, match=field):
            AfloatBenefit(**{field: float("nan")})


class TestShoreBenefit:
    """The shore stream is the shore model's number, in hours."""

    def test_detection_lead_converts_epochs_to_physical_hours(self) -> None:
        benefit = ShoreBenefit(detection_lead_epochs=6, epoch_hours=1.0)
        assert benefit.detection_lead_hours == pytest.approx(6.0)

    def test_a_coarser_epoch_lengthens_the_same_lead(self) -> None:
        benefit = ShoreBenefit(detection_lead_epochs=6, epoch_hours=24.0)
        assert benefit.detection_lead_hours == pytest.approx(144.0)

    def test_no_detection_reports_no_lead_rather_than_zero(self) -> None:
        assert ShoreBenefit(detection_lead_epochs=None).detection_lead_hours is None

    @pytest.mark.parametrize("bad", [0.0, -1.0, float("inf")])
    def test_epoch_duration_must_be_positive_and_finite(self, bad: float) -> None:
        with pytest.raises(ValueError, match="epoch_hours"):
            ShoreBenefit(epoch_hours=bad)

    def test_non_finite_cases_are_refused(self) -> None:
        with pytest.raises(ValueError, match="cases_averted"):
            ShoreBenefit(cases_averted=float("nan"))

    def test_adopts_the_counterfactual_rather_than_re_deriving_it(self) -> None:
        result = evaluate_counterfactual(
            PortCallImportation(
                port_id="TESTPORT",
                pathogen_id="norwalk_gi",
                epoch_hours=24.0,
                strain_importations={"GII.4": tuple(2.0 for _ in range(200))},
                ship_detection_epoch=0,
            ),
            ShoreRenewalParameters(
                r_shore=0.5,
                generation_median_hours=48.0,
                generation_sigma=0.6,
                generation_max_hours=336.0,
                population=200_000,
            ),
            residual_importation_fraction=0.0,
            case_threshold=10.0,
            capability=PortSurveillanceCapability(
                port_id="TESTPORT",
                port_name="Test Port",
                region="TEST",
                population=200_000,
                syndromic_enabled=True,
                syndromic_coverage=0.5,
                syndromic_delay_days=3,
                syndromic_pathogens=(),
            ),
        )
        benefit = ShoreBenefit.from_counterfactual(result, epoch_hours=24.0)
        assert result.benefit > 0.0
        assert benefit.cases_averted == pytest.approx(result.benefit)
        assert benefit.detection_lead_epochs == result.detection_lead_epochs
        assert benefit.detection_lead_hours == pytest.approx(
            24.0 * result.detection_lead_epochs,
        )


class TestBenefitValuation:
    """Valuation is external, so every rate carries a source."""

    def test_provenance_must_cover_every_rate(self) -> None:
        with pytest.raises(ValueError, match="provenance"):
            BenefitValuation(
                usd_per_case_afloat=1.0,
                usd_per_case_ashore=1.0,
                provenance={"usd_per_case_afloat": "somewhere"},
            )

    def test_provenance_entries_must_say_something(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            BenefitValuation(
                usd_per_case_afloat=1.0,
                usd_per_case_ashore=1.0,
                provenance=dict.fromkeys(VALUATION_PROVENANCE, "  "),
            )

    def test_negative_rates_are_refused(self) -> None:
        with pytest.raises(ValueError, match="usd_per_case_ashore"):
            BenefitValuation(
                usd_per_case_afloat=1.0,
                usd_per_case_ashore=-1.0,
                provenance=VALUATION_PROVENANCE,
            )

    def test_shipped_unit_valuation_documents_its_provenance(self) -> None:
        assert set(UNIT_VALUATION.provenance) == set(VALUATION_PROVENANCE)

    def test_intervention_savings_pass_through_at_face_value(self) -> None:
        afloat = AfloatBenefit(intervention_usd_averted=250.0)
        assert VALUATION.afloat_usd(afloat) == pytest.approx(250.0)

    def test_operational_impact_is_unpriced_unless_a_rate_is_supplied(self) -> None:
        afloat = AfloatBenefit(operational_impact_averted=40.0)
        assert VALUATION.afloat_usd(afloat) == pytest.approx(0.0)
        priced = BenefitValuation(
            usd_per_case_afloat=0.0,
            usd_per_case_ashore=0.0,
            usd_per_operational_impact_point=3.0,
            provenance=VALUATION_PROVENANCE,
        )
        assert priced.afloat_usd(afloat) == pytest.approx(120.0)

    def test_symptomatic_hours_are_unpriced_by_default(self) -> None:
        afloat = AfloatBenefit(symptomatic_person_hours_averted=100.0)
        assert VALUATION.afloat_usd(afloat) == pytest.approx(0.0)


class TestBenefitSplit:
    """Two communities, two streams, and the ratio between them."""

    @staticmethod
    def _split(afloat_cases: float = 10.0, shore_cases: float = 30.0):
        return benefit_split(
            AfloatBenefit(cases_averted=afloat_cases),
            ShoreBenefit(cases_averted=shore_cases),
            VALUATION,
        )

    def test_streams_are_reported_separately_in_cases(self) -> None:
        split = self._split()
        assert split.afloat_cases_averted == pytest.approx(10.0)
        assert split.shore_cases_averted == pytest.approx(30.0)

    def test_total_is_the_sum_of_the_two_monetised_streams(self) -> None:
        split = self._split()
        assert split.total_usd == pytest.approx(10_000.0 + 15_000.0)

    def test_case_ratio_is_free_of_the_valuation(self) -> None:
        cases = benefit_split(
            AfloatBenefit(cases_averted=10.0),
            ShoreBenefit(cases_averted=30.0),
            UNIT_VALUATION,
        )
        assert self._split().shore_to_afloat_case_ratio == pytest.approx(
            cases.shore_to_afloat_case_ratio,
        )

    def test_dollar_ratio_equals_the_case_ratio_under_equal_valuation(self) -> None:
        split = benefit_split(
            AfloatBenefit(cases_averted=10.0),
            ShoreBenefit(cases_averted=30.0),
            UNIT_VALUATION,
        )
        assert split.shore_to_afloat_usd_ratio == pytest.approx(
            split.shore_to_afloat_case_ratio,
        )

    def test_dollar_ratio_moves_with_the_valuation_and_the_case_ratio_does_not(
        self,
    ) -> None:
        split = self._split()
        assert split.shore_to_afloat_case_ratio == pytest.approx(3.0)
        assert split.shore_to_afloat_usd_ratio == pytest.approx(1.5)

    def test_no_afloat_benefit_leaves_the_ratio_undefined(self) -> None:
        assert self._split(afloat_cases=0.0).shore_to_afloat_case_ratio is None
        assert self._split(afloat_cases=0.0).shore_to_afloat_usd_ratio is None

    def test_community_shares_sum_to_one(self) -> None:
        shares = self._split().benefit_shares()
        assert set(shares) == set(COMMUNITIES)
        assert sum(shares.values()) == pytest.approx(1.0)

    def test_shares_are_zero_when_nothing_was_averted(self) -> None:
        shares = self._split(afloat_cases=0.0, shore_cases=0.0).benefit_shares()
        assert sum(shares.values()) == pytest.approx(0.0)

    def test_community_usd_keys_on_the_two_communities(self) -> None:
        assert set(self._split().community_usd()) == {
            COMMUNITY_AFLOAT,
            COMMUNITY_SHORE,
        }


class TestPayerBenefit:
    """Community benefit reaches payers through declared weights only."""

    @staticmethod
    def _split():
        return benefit_split(
            AfloatBenefit(cases_averted=10.0),
            ShoreBenefit(cases_averted=30.0),
            UNIT_VALUATION,
        )

    def test_default_weights_split_the_shore_evenly(self) -> None:
        benefits = payer_benefit_usd(self._split())
        assert benefits[PAYER_SHIP_OPERATOR] == pytest.approx(10.0)
        assert benefits[PAYER_PORT_AUTHORITY] == pytest.approx(15.0)
        assert benefits[PAYER_PUBLIC_HEALTH_AGENCY] == pytest.approx(15.0)

    def test_attributed_benefit_conserves_the_total(self) -> None:
        split = self._split()
        assert sum(payer_benefit_usd(split).values()) == pytest.approx(split.total_usd)

    def test_shifting_the_shore_weights_shifts_only_shore_payers(self) -> None:
        benefits = payer_benefit_usd(
            self._split(),
            weights={
                PAYER_SHIP_OPERATOR: 1.0,
                PAYER_PORT_AUTHORITY: 0.25,
                PAYER_PUBLIC_HEALTH_AGENCY: 0.75,
            },
        )
        assert benefits[PAYER_SHIP_OPERATOR] == pytest.approx(10.0)
        assert benefits[PAYER_PORT_AUTHORITY] == pytest.approx(7.5)
        assert benefits[PAYER_PUBLIC_HEALTH_AGENCY] == pytest.approx(22.5)

    def test_weights_must_cover_every_payer(self) -> None:
        with pytest.raises(ValueError, match="every payer"):
            payer_benefit_usd(self._split(), weights={PAYER_SHIP_OPERATOR: 1.0})

    def test_unknown_payers_are_refused(self) -> None:
        with pytest.raises(ValueError, match="unknown payer"):
            payer_benefit_usd(
                self._split(), weights={**DEFAULT_COMMUNITY_WEIGHTS, "harbourmaster": 1.0},
            )

    def test_weights_within_a_community_must_sum_to_one(self) -> None:
        with pytest.raises(ValueError, match="must sum to 1"):
            payer_benefit_usd(
                self._split(),
                weights={
                    PAYER_SHIP_OPERATOR: 1.0,
                    PAYER_PORT_AUTHORITY: 0.5,
                    PAYER_PUBLIC_HEALTH_AGENCY: 0.9,
                },
            )

    def test_negative_weights_are_refused(self) -> None:
        with pytest.raises(ValueError, match="weights"):
            payer_benefit_usd(
                self._split(),
                weights={
                    PAYER_SHIP_OPERATOR: 1.0,
                    PAYER_PORT_AUTHORITY: -0.5,
                    PAYER_PUBLIC_HEALTH_AGENCY: 1.5,
                },
            )
