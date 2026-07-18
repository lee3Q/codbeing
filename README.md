# codbeing

Private dogfooding-first User Runtime Simulator.

codbeing is a local-first CLI lab for capturing structured `DecisionTrace`
records and generating evidence-grounded Runtime Analysis reports. The default
runtime stays on the local machine. External model assist is opt-in and only
runs when the user explicitly selects it and a key is available.

## Quick Start

```bash
python3 -m codbeing
python3 -m codbeing example nomusa
python3 -m codbeing capture
python3 -m codbeing run private-traces/decision-traces.json
python3 -m codbeing model status
```

Power-user entrypoints are also available through the local `cb` wrapper when
installed on the machine.

## Privacy Boundary

The repository intentionally excludes local private data:

- `private/`
- `private-traces/`
- `private-reports/`
- `.env` and other secret files

Generated reports and personal trace inputs should remain local unless they are
manually sanitized first.

## Verification

```bash
python3 -m unittest discover -s tests -v
python3 -m pytest -q
```
