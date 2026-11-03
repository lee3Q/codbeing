"""Onboarding must decline non-interactive stdin without a traceback or partial config."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_onboard_without_interactive_input_writes_no_config(tmp_path):
    env = {**os.environ, 'PYTHONPATH': str(ROOT)}
    result = subprocess.run([sys.executable, '-m', 'codbeing', '--config', str(tmp_path / 'config.json'), 'onboard'],
                            cwd=tmp_path, env=env, text=True, capture_output=True, stdin=subprocess.DEVNULL)
    assert result.returncode == 0, result.stderr
    assert 'Onboarding needs interactive input' in result.stdout
    assert 'Traceback' not in result.stderr
    assert list(tmp_path.iterdir()) == []
