"""Malformed persisted journal shapes must be rejected without a traceback."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from codbeing.prospective import GENESIS, _hash

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('event', [None, [], 7, 'not-an-event',
                                   {'files': None}, {'files': []},
                                   {'files': 'records.json'}, {'files': 1}])
def test_cli_rejects_malformed_event_shapes_without_changing_evidence(tmp_path, event):
    journal = tmp_path / 'journal'
    journal.mkdir()
    source = journal / 'events.jsonl'
    if isinstance(event, dict):
        event = {"sequence": 1, "previous_hash": GENESIS, "kind": "prediction_issued",
                 "recorded_at": "2026-09-24T01:00:00+00:00", **event}
        event["event_hash"] = _hash(event)
    original = (json.dumps(event) + '\n').encode('utf-8')
    source.write_bytes(original)
    env = {**os.environ, 'PYTHONPATH': str(ROOT)}
    result = subprocess.run([sys.executable, '-m', 'codbeing.prospective', 'verify', str(journal)],
                            cwd=tmp_path, env=env, text=True, capture_output=True)
    assert result.returncode == 2, result.stderr
    assert 'prospective journal error:' in result.stderr
    assert 'Traceback' not in result.stderr
    assert not result.stdout
    assert source.read_bytes() == original
    assert list(journal.iterdir()) == [source]
