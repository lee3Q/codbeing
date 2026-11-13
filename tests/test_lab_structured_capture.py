"""The advertised no-argument decision action reaches real local capture."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest
from codbeing.__main__ import main

ROOT = Path(__file__).resolve().parents[1]
ANSWERS = ['Synthetic study decision', 'Study, Rest', 'Study', 'Rest',
           'Protect focus', '', '', '', '', '', '', '']


def run_lab(cwd, answers):
    env = {**os.environ, 'PYTHONPATH': str(ROOT)}
    env.pop('CODBEING_LAB_STATE_FIXTURE', None)
    return subprocess.run([sys.executable, '-m', 'codbeing'], cwd=cwd, env=env,
                          input='\n'.join(answers) + '\n', text=True, capture_output=True)


def test_real_menu_capture_then_analysis_and_reentry(tmp_path):
    result = run_lab(tmp_path, ['2', *ANSWERS, '3', 'q'])
    assert result.returncode == 0
    assert result.stderr == ''
    store = tmp_path / 'private-traces/decision-traces.json'
    traces = json.loads(store.read_text(encoding='utf-8'))
    assert len(traces) == 1
    assert traces[0]['context'] == ANSWERS[0]
    assert traces[0]['options'] == ['Study', 'Rest']
    assert traces[0]['chosen_action'] == 'Study'
    reports = list((tmp_path / 'private-reports').glob('*.md'))
    assert len(reports) == 1
    report = reports[0].read_text(encoding='utf-8')
    assert 'external model calls are disabled' in report
    assert report in result.stdout
    assert '1 stored DecisionTrace' in result.stdout
    assert not (tmp_path / 'private-traces/submitted-material.json').exists()


def test_menu_capture_forces_local_even_with_saved_glm_and_preserves_notes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = tmp_path / 'private/codbeing-config.json'
    config.parent.mkdir()
    config.write_text('{"model_provider":"glm"}', encoding='utf-8')
    notes = tmp_path / 'private-traces/submitted-material.json'
    notes.parent.mkdir()
    notes.write_text('["old synthetic note"]', encoding='utf-8')
    original = {config: config.read_bytes(), notes: notes.read_bytes()}
    with patch('builtins.input', side_effect=['2', *ANSWERS, 'q']), \
         patch('codbeing.__main__.external_assist_ready') as ready, \
         patch('codbeing.__main__._confirm_external_context_sharing') as consent, \
         patch('codbeing.models._call_glm') as provider, \
         patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')) as network:
        assert main([]) == 0
    for mocked in [ready, consent, provider, network]:
        mocked.assert_not_called()
    for path, raw in original.items():
        assert path.read_bytes() == raw
    assert len(json.loads(Path('private-traces/decision-traces.json').read_text())) == 1


@pytest.mark.parametrize('raw', [b'\xfforiginal', b'{broken', b'[{"context":"partial"}]'])
def test_bad_existing_store_blocks_append_and_report(tmp_path, raw):
    store = tmp_path / 'private-traces/decision-traces.json'
    store.parent.mkdir()
    store.write_bytes(raw)
    result = run_lab(tmp_path, ['2', *ANSWERS, '4', 'q'])
    assert result.returncode == 0
    assert 'capture error:' in result.stdout
    assert '모델·개인정보 경계' in result.stdout
    assert store.read_bytes() == raw
    assert not (tmp_path / 'private-reports').exists()


def test_eof_during_capture_writes_nothing(tmp_path):
    result = run_lab(tmp_path, ['2', 'unfinished context'])
    assert result.returncode == 0
    assert result.stderr == ''
    assert 'Capture needs interactive input' in result.stdout
    assert not (tmp_path / 'private-traces').exists()
    assert not (tmp_path / 'private-reports').exists()


def test_keyboard_cancel_returns_to_entrance_without_save(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    with patch('builtins.input', side_effect=['2', 'unfinished', KeyboardInterrupt, '4', 'q']):
        assert main([]) == 0
    output = capsys.readouterr().out
    assert 'Capture cancelled; no DecisionTrace was appended.' in output
    assert '모델·개인정보 경계' in output
    assert not (tmp_path / 'private-traces').exists()


def test_invalid_new_decision_does_not_write_and_menu_remains_usable(tmp_path):
    answers = ANSWERS.copy()
    answers[0] = ''
    result = run_lab(tmp_path, ['2', *answers, '4', 'q'])
    assert result.returncode == 0
    assert 'capture error:' in result.stdout
    assert '모델·개인정보 경계' in result.stdout
    assert not (tmp_path / 'private-traces').exists()


def test_second_menu_capture_appends_and_keeps_first_report(tmp_path):
    first = run_lab(tmp_path, ['2', *ANSWERS, 'q'])
    assert first.returncode == 0
    report = next((tmp_path / 'private-reports').glob('*.md'))
    before = report.read_bytes()
    second_answers = ANSWERS.copy()
    second_answers[0] = 'Second synthetic decision'
    second = run_lab(tmp_path, ['2', *second_answers, '3', 'q'])
    assert second.returncode == 0
    traces = json.loads((tmp_path / 'private-traces/decision-traces.json').read_text())
    assert [t['context'] for t in traces] == [ANSWERS[0], second_answers[0]]
    assert report.read_bytes() == before
    assert len(list((tmp_path / 'private-reports').glob('*.md'))) == 2
