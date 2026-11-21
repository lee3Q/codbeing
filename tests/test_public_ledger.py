"""The committed public evidence ledger must be semantically verified."""

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "evidence/public-cycle/ledger.jsonl"
EXPECTED_HEAD = "96a83068d6ee42fe2f65b323830de46e4fde29008217bfeb5501f92707ed5d3b"


def test_committed_public_ledger_reports_verified_status():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "codbeing.evidence_ledger",
            str(LEDGER.relative_to(ROOT)),
            "verify",
            "--expected-head",
            EXPECTED_HEAD,
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    state = json.loads(result.stdout)
    assert state["head"] == EXPECTED_HEAD
    assert state["current_status"]["public_cycle"] == "PASS"
