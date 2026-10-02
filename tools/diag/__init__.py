"""Shared machinery for the diagnostic readout/probe tools.

The noro_diag tools grew up as copies of one another; this package
carries the pieces that were genuinely duplicated so the tools consume
one implementation instead of drifting apart. ``readout_common`` holds
the run-zip readers/writers and the rate statistics, ``json_io`` the
validated JSON readers, ``manifest_args`` the campaign-manifest CLI
vocabulary, and ``instrument_common`` the TransmissionCore
witness-wrapper scaffolding.
"""
