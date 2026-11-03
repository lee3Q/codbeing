"""Unreadable trace inputs return a concise CLI error without creating reports."""
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest
from codbeing.__main__ import main


def arguments(command, source, report, reports):
    args = [command, str(source)]
    if command == 'analyze':
        args.append(str(report))
    elif command in ('run', 'quick'):
        args += ['--reports-dir', str(reports)]
    return args


@pytest.mark.parametrize('command', ['validate', 'quick', 'run', 'analyze'])
def test_directory_input_exits_cleanly_without_report(tmp_path, command):
    source = tmp_path / 'directory-input'
    source.mkdir()
    sentinel = source / 'keep.txt'
    sentinel.write_text('untouched', encoding='utf-8')
    report = tmp_path / 'report.md'
    reports = tmp_path / 'reports'
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, '-m', 'codbeing', *arguments(command, source, report, reports)],
        cwd=tmp_path, env={**os.environ, 'PYTHONPATH': str(root)},
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert 'validation error: could not read trace input' in result.stdout
    assert not result.stderr
    assert sentinel.read_text(encoding='utf-8') == 'untouched'
    assert not report.exists()
    assert not reports.exists()


@pytest.mark.parametrize('command', ['validate', 'quick', 'run', 'analyze'])
@pytest.mark.parametrize('error_type', [PermissionError, OSError])
def test_read_failure_does_not_expose_error_details_or_create_report(tmp_path, capsys, command, error_type):
    source = tmp_path / 'trace.json'
    source.write_bytes(b'original bytes')
    report = tmp_path / 'report.md'
    reports = tmp_path / 'reports'
    with patch('codbeing.__main__._read_json', side_effect=error_type('private-marker')):
        assert main(arguments(command, source, report, reports)) == 2
    output = capsys.readouterr()
    assert 'validation error: could not read trace input' in output.out
    assert 'private-marker' not in output.out + output.err
    assert not output.err
    assert source.read_bytes() == b'original bytes'
    assert not report.exists()
    assert not reports.exists()
