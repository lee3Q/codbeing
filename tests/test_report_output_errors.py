"""Report I/O failures return an error instead of an unhandled traceback."""
import errno
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from codbeing.__main__ import ACADEMIC_NOMUSA_TRACES, _write_report, main


def test_analyze_blocked_parent_returns_output_error(tmp_path, capsys):
    source = tmp_path / 'trace.json'
    source.write_text(json.dumps(ACADEMIC_NOMUSA_TRACES), encoding='utf-8')
    blocker = tmp_path / 'not-a-directory'
    blocker.write_text('keep', encoding='utf-8')
    assert main(['--config', str(tmp_path / 'config.json'), 'analyze', str(source), str(blocker / 'report.md')]) == 2
    output = capsys.readouterr().out
    assert 'output error: could not write report' in output
    assert 'report written:' not in output
    assert blocker.read_text(encoding='utf-8') == 'keep'
    assert json.loads(source.read_text(encoding='utf-8')) == ACADEMIC_NOMUSA_TRACES


@pytest.mark.parametrize('operation', ['mkdir', 'open', 'write'])
def test_report_io_error_is_not_success(tmp_path, capsys, operation):
    destination = tmp_path / 'report.md'
    failure = OSError(errno.ENOSPC, 'synthetic disk error')
    if operation == 'write':
        class FailedWriter:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def write(self, _): raise failure
        target = patch.object(Path, 'open', return_value=FailedWriter())
    else:
        target = patch.object(Path, operation, side_effect=failure)
    with target:
        assert _write_report(destination, 'report') == 2
    output = capsys.readouterr().out
    assert 'output error: could not write report' in output
    assert 'Runtime Analysis report written:' not in output
