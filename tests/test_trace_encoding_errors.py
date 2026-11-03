"""Unreadable UTF-8 trace input is rejected without overwriting evidence."""

from unittest.mock import patch
import pytest
from codbeing.__main__ import main


@pytest.mark.parametrize('command', ['validate', 'run', 'analyze'])
def test_non_utf8_trace_returns_error_without_report(tmp_path, capsys, command):
    source = tmp_path / 'trace.json'
    source.write_bytes(b'\xff')
    report = tmp_path / 'report.md'
    reports = tmp_path / 'reports'
    args = [command, str(source)]
    if command == 'analyze':
        args.append(str(report))
    elif command == 'run':
        args += ['--reports-dir', str(reports)]
    assert main(args) == 2
    assert source.read_bytes() == b'\xff'
    assert not report.exists()
    assert not reports.exists()
    assert 'invalid UTF-8' in capsys.readouterr().out


def test_non_utf8_capture_store_is_not_replaced(tmp_path, capsys):
    store = tmp_path / 'trace.json'
    store.write_bytes(b'\xff')
    trace = dict(context='test', options=['A'], chosen_action='A', rejected_options=[],
                 judgment_basis='test', observed_behavior='', outcome='', aftertaste='',
                 memory_confidence='', source='synthetic')
    with patch('codbeing.__main__._prompt_for_trace', return_value=trace):
        assert main(['capture', '--store', str(store), '--no-analyze']) == 2
    assert store.read_bytes() == b'\xff'
    assert 'invalid UTF-8' in capsys.readouterr().out
