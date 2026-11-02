"""Synthetic boundary tests: invalid evidence must not become a saved decision."""
from copy import deepcopy
from unittest.mock import patch

import pytest

from codbeing.__main__ import main
from codbeing.schema import DecisionTraceValidationError, validate_decision_trace

TRACE = {
    'context': 'Choose a test plan', 'options': ['A', 'B'],
    'chosen_action': 'A', 'rejected_options': ['B'],
    'judgment_basis': 'Small reversible first step',
    'observed_behavior': '', 'outcome': 'pending', 'aftertaste': '',
    'memory_confidence': 'unknown', 'source': 'synthetic test',
}


@pytest.mark.parametrize('field', ['context', 'chosen_action', 'judgment_basis'])
@pytest.mark.parametrize('value', ['', '  \t\n'])
def test_rejects_blank_core_evidence(field, value):
    trace = {**TRACE, field: value}
    with pytest.raises(DecisionTraceValidationError, match=field):
        validate_decision_trace(trace, require_core=True)


@pytest.mark.parametrize('field', list(TRACE))
@pytest.mark.parametrize('value', [None, 7, False, {}])
def test_rejects_wrong_field_types(field, value):
    with pytest.raises(DecisionTraceValidationError, match=field):
        validate_decision_trace({**TRACE, field: value}, require_core=True)


@pytest.mark.parametrize('field', ['options', 'rejected_options'])
@pytest.mark.parametrize('value', ['A, B', [1], [' '], [None], [['A']]])
def test_rejects_invalid_option_lists(field, value):
    with pytest.raises(DecisionTraceValidationError, match=field):
        validate_decision_trace({**TRACE, field: value}, require_core=True)


def test_empty_options_rejected_but_no_rejected_options_is_valid():
    with pytest.raises(DecisionTraceValidationError, match='options'):
        validate_decision_trace({**TRACE, 'options': []}, require_core=True)
    validate_decision_trace({**TRACE, 'rejected_options': []})


def test_unknown_supporting_evidence_and_extra_fields_are_not_fabricated():
    trace = {**deepcopy(TRACE), 'private_extension': {'anything': True}}
    original = deepcopy(trace)
    validate_decision_trace(trace, require_core=True)
    assert trace == original


@pytest.mark.parametrize('existing', [False, True])
def test_invalid_capture_never_changes_store(tmp_path, existing, capsys):
    store = tmp_path / 'traces.json'
    if existing:
        store.write_text('[]\n')
    original = store.read_bytes() if existing else None
    with patch('codbeing.__main__._prompt_for_trace', return_value={**TRACE, 'context': ''}):
        assert main(['capture', '--store', str(store), '--no-analyze']) == 2
    assert (store.read_bytes() if store.exists() else None) == original
    assert 'appended' not in capsys.readouterr().out


@pytest.mark.parametrize('error,code', [(EOFError(), 0), (KeyboardInterrupt(), 130)])
def test_cancelled_capture_does_not_save(tmp_path, error, code):
    store = tmp_path / 'traces.json'
    with patch('builtins.input', side_effect=error):
        assert main(['capture', '--store', str(store), '--no-analyze']) == code
    assert not store.exists()


def test_legacy_blank_core_record_remains_readable_with_field_warnings():
    from codbeing.report import analyze_decision_traces
    trace = {**TRACE, 'context': '', 'judgment_basis': '', 'options': []}
    before = deepcopy(trace)
    report = analyze_decision_traces(trace)
    assert 'Incomplete legacy evidence in trace 1: context, judgment_basis, options' in report
    assert trace == before


def test_short_korean_core_is_valid():
    validate_decision_trace({**TRACE, 'context': '일', 'chosen_action': '가',
                             'judgment_basis': '쉼', 'options': ['가']}, require_core=True)


@pytest.mark.parametrize('existing', [False, True])
def test_failed_replace_preserves_old_store_and_removes_partial_file(tmp_path, existing, capsys):
    from pathlib import Path
    store = tmp_path / 'traces.json'
    if existing:
        store.write_text('[]\n')
    original = store.read_bytes() if existing else None
    with patch('codbeing.__main__._prompt_for_trace', return_value=deepcopy(TRACE)), \
         patch.object(Path, 'replace', side_effect=OSError('synthetic write failure')):
        assert main(['capture', '--store', str(store), '--no-analyze']) == 2
    assert (store.read_bytes() if store.exists() else None) == original
    assert not list(tmp_path.glob('*.tmp'))
    output = capsys.readouterr().out
    assert 'capture error' in output
    assert 'appended' not in output


def test_valid_capture_preserves_existing_unknown_values(tmp_path):
    import json
    store = tmp_path / 'traces.json'
    previous = {**TRACE, 'context': '', 'outcome': ''}
    store.write_text(json.dumps([previous]))
    with patch('codbeing.__main__._prompt_for_trace', return_value=deepcopy(TRACE)):
        assert main(['capture', '--store', str(store), '--no-analyze']) == 0
    assert json.loads(store.read_text()) == [previous, TRACE]


@pytest.mark.parametrize('patch_value', [{'options': 'A, B'}, {'outcome': None}, {'options': []}, {'context': ''}])
def test_key_only_legacy_shapes_stay_readable_with_warnings(patch_value):
    from codbeing.report import analyze_decision_traces
    trace = {**TRACE, **patch_value}
    before = deepcopy(trace)
    validate_decision_trace(trace)
    assert 'Incomplete legacy evidence in trace 1:' in analyze_decision_traces(trace)
    assert trace == before


@pytest.mark.parametrize('value', [None, 0, False, {'not': 'evidence'}])
def test_invalid_legacy_core_abstains_before_hypothesis_or_hard_mirror(value):
    from codbeing.report import analyze_decision_traces
    trace = {**TRACE, 'context': value, 'chosen_action': value, 'judgment_basis': value,
             'memory_confidence': 'high', 'activation_pattern': 'stress', 'impact': 'high',
             'reversibility_cost': 'high', 'action_pressure': 'immediate'}
    report = analyze_decision_traces([trace, trace])
    assert 'Analysis abstained' in report
    for prohibited in ['## User-Code Hypothesis', 'Hard Mirror', 'Overall confidence:', 'Current trace chose', 'bases:']:
        assert prohibited not in report


def test_interrupt_after_commit_does_not_claim_no_append(tmp_path, capsys):
    from codbeing.__main__ import _write_json
    store = tmp_path / 'traces.json'
    def write_then_interrupt(path, payload):
        _write_json(path, payload)
        raise KeyboardInterrupt
    with patch('codbeing.__main__._prompt_for_trace', return_value=deepcopy(TRACE)), \
         patch('codbeing.__main__._write_json', side_effect=write_then_interrupt):
        assert main(['capture', '--store', str(store), '--no-analyze']) == 130
    assert store.exists()
    output = capsys.readouterr().out
    assert 'may have been saved' in output
    assert 'no DecisionTrace was appended' not in output
