"""Damaged local data must not close the no-argument lab or be rewritten."""
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest
from codbeing.__main__ import _render_lab_surface
from codbeing.config import CodbeingConfig
from codbeing.lab_state import append_submitted_material, load_research_state

ROOT = Path(__file__).resolve().parents[1]


def run_lab(cwd, stdin):
    env = {**os.environ, 'PYTHONPATH': str(ROOT)}
    env.pop('CODBEING_LAB_STATE_FIXTURE', None)
    return subprocess.run([sys.executable, '-m', 'codbeing'], cwd=cwd,
                          env=env, input=stdin, text=True, capture_output=True)


@pytest.mark.parametrize('rel', ['private-traces/decision-traces.json',
                               'private-traces/submitted-material.json'])
def test_bad_utf8_store_keeps_entrance_and_other_actions_usable(tmp_path, rel):
    path = tmp_path / rel
    path.parent.mkdir(parents=True)
    raw = b'\xffPRIVATE_SYNTHETIC_MARKER'
    path.write_bytes(raw)
    before = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob('*'))
    result = run_lab(tmp_path, '4\nq\n')
    assert result.returncode == 0
    assert result.stderr == ''
    assert 'Local data warning:' in result.stdout
    assert '모델·개인정보 경계' in result.stdout
    assert 'PRIVATE_SYNTHETIC_MARKER' not in result.stdout
    assert path.read_bytes() == raw
    assert before == sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob('*'))


def test_bad_note_store_blocks_append_without_replacing_bytes(tmp_path):
    path = tmp_path / 'notes.json'
    path.write_bytes(b'\xfforiginal')
    with pytest.raises(ValueError, match='needs repair'):
        append_submitted_material(path, 'new synthetic note')
    assert path.read_bytes() == b'\xfforiginal'


def test_bad_utf8_report_returns_to_entrance_and_can_choose_another_action(tmp_path):
    path = tmp_path / 'private-reports/broken.md'
    path.parent.mkdir()
    path.write_bytes(b'\xffPRIVATE_SYNTHETIC_MARKER')
    result = run_lab(tmp_path, '3\n4\nq\n')
    assert result.returncode == 0
    assert result.stderr == ''
    assert 'Local report error: could not read the report.' in result.stdout
    assert '모델·개인정보 경계' in result.stdout
    assert 'PRIVATE_SYNTHETIC_MARKER' not in result.stdout
    assert path.read_bytes() == b'\xffPRIVATE_SYNTHETIC_MARKER'


@pytest.mark.parametrize('error', [PermissionError('PRIVATE_SYNTHETIC_MARKER'),
                                  FileNotFoundError('PRIVATE_SYNTHETIC_MARKER')])
def test_report_read_failure_is_concise_and_does_not_escape(tmp_path, monkeypatch, capsys, error):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / 'private-reports/report.md'
    path.parent.mkdir()
    path.write_text('valid report', encoding='utf-8')
    state = load_research_state(tmp_path / 'traces.json', path.parent)
    with patch('codbeing.__main__._lab_state', return_value=state), \
         patch('pathlib.Path.read_text', side_effect=error):
        assert _render_lab_surface('analysis', CodbeingConfig(), 'Solo inspect') == 'Solo inspect'
    result = capsys.readouterr()
    assert result.err == ''
    assert 'Local report error:' in result.out
    assert 'PRIVATE_SYNTHETIC_MARKER' not in result.out
    assert path.read_text(encoding='utf-8') == 'valid report'


def test_valid_report_still_displays(tmp_path):
    path = tmp_path / 'private-reports/report.md'
    path.parent.mkdir()
    path.write_text('# Valid synthetic report\n정상 한국어 내용', encoding='utf-8')
    result = run_lab(tmp_path, '3\nq\n')
    assert result.returncode == 0
    assert result.stderr == ''
    assert '정상 한국어 내용' in result.stdout
    assert 'Local report error:' not in result.stdout
