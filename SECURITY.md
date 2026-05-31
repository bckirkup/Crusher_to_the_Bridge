# Security Policy

## Scope

Crusher-to-the-Bridge is a **simulation platform** — it does not handle
real patient data, personally identifiable information (PII), or live
biosurveillance feeds.  All pathogen profiles, agent populations, and
diagnostic telemetry are synthetic.

## Supported Versions

| Version | Supported |
|---------|-----------|
| `main` (HEAD) | Yes |
| Feature branches | Best-effort |

## Reporting a Vulnerability

If you discover a security issue (e.g., a dependency CVE, credential
exposure in committed files, or unsafe deserialization), please report
it **privately**:

1. **Email:** bckirkup@gmail.com
2. **Subject line:** `[SECURITY] Crusher-to-the-Bridge — <brief description>`

Do **not** open a public GitHub issue for security vulnerabilities.

You should receive an acknowledgment within 72 hours.  Confirmed issues
will be patched on `main` and disclosed in the next release notes.

## Security Considerations

### No Secrets in Repository

- Configuration files (`config.yaml`, JSON data) contain only simulation
  parameters — no API keys, tokens, or credentials.
- The `.gitignore` excludes runtime artifacts (`telemetry_buffer/*.json`,
  experience stores) that could contain large simulation outputs.
- No `.env` files are committed or expected.

### Dependency Hygiene

- All Python dependencies are listed in `requirements.txt` with minimum
  version pins.
- CI runs on Python 3.11 and 3.12 against `ubuntu-latest`.
- No native C extensions or binary blobs are bundled; all simulation
  logic is pure Python + NumPy.

### Data Integrity

- The `tools/sanity_checker.py` validator enforces structural and
  mathematical bounds on all configuration files before simulation.
- JSON Schemas in `schemas/` provide formal contracts for every data file.
- The Six Laws (`.cursorrules`) prohibit hardcoded zone names, epoch
  schedules, and out-of-bounds physics scalars.

### External Simulation Bridges

Sibling repositories (`infection-dynamics`, `py-contam`, `GRUMB`,
`EMOD-Generic`, `FRED`) are **read-only** dependencies.  This project
adapts their mathematical contracts but never modifies upstream code.
