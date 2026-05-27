"""Read-depth and metagenomic parameters are sourced from config.yaml."""

from __future__ import annotations

from crusher_labs import (
    build_modalities,
    load_config,
    metagenomic_sequencing_params,
    wastewater_sequencing_params,
)
from orchestrator_init import init_observation_engine


def test_wastewater_sequencing_params_match_config() -> None:
    cfg = load_config()
    params = wastewater_sequencing_params(cfg)
    ww_cfg = cfg["wastewater_sequencing"]
    assert params["read_depth"] == ww_cfg["read_depth"]
    assert params["dirichlet_concentration"] == ww_cfg["dirichlet_concentration"]
    assert params["pseudocount"] == ww_cfg["pseudocount"]


def test_metagenomic_sequencing_params_match_config() -> None:
    cfg = load_config()
    params = metagenomic_sequencing_params(cfg)
    seq_cfg = cfg["sequencing"]
    assert params["read_depth"] == seq_cfg["read_depth"]
    assert params["pseudocount"] == seq_cfg["pseudocount"]
    assert params["clr_shift_scale"] == seq_cfg["clr_shift_scale"]


def test_build_modalities_uses_config_read_depth() -> None:
    cfg = load_config()
    modalities = build_modalities(cfg)
    seq = modalities["sequencing"]
    assert seq.read_depth == cfg["sequencing"]["read_depth"]
    assert seq.clr_shift_scale == cfg["sequencing"]["clr_shift_scale"]


def test_init_observation_engine_wastewater_read_depth() -> None:
    cfg = load_config()
    engine = init_observation_engine(cfg, seed=42)
    expected = wastewater_sequencing_params(cfg)["read_depth"]
    assert engine.wastewater_seq.read_depth == expected
