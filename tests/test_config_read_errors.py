"""Bad local settings stop the CLI without leaking contents or rewriting them."""

from unittest.mock import patch

import pytest

from codbeing.__main__ import main


@pytest.mark.parametrize('raw', [b'{', b'\xff', b'{"model_provider": "private-value", broken}'])
@pytest.mark.parametrize('command', [[], ['model', 'status'], ['capture', '--no-analyze']])
def test_invalid_config_is_reported_without_traceback_or_writes(tmp_path, capsys, raw, command):
    path = tmp_path / 'config.json'
    path.write_bytes(raw)
    with patch('builtins.input') as prompt, patch('codbeing.__main__.save_config') as save:
        assert main(['--config', str(path), *command]) == 2
    prompt.assert_not_called()
    save.assert_not_called()
    assert path.read_bytes() == raw
    result = capsys.readouterr()
    assert result.out == ''
    assert result.err.startswith('config error: could not read local settings.')
    assert 'private-value' not in result.err
    assert 'Traceback' not in result.err


def test_unreadable_config_stops_before_command(tmp_path, capsys):
    with patch('codbeing.__main__.load_config', side_effect=PermissionError('private-value')), \
         patch('codbeing.__main__._model') as command:
        assert main(['--config', str(tmp_path / 'config.json'), 'model', 'status']) == 2
    command.assert_not_called()
    assert 'private-value' not in capsys.readouterr().err


def test_missing_config_keeps_default_behavior(tmp_path, capsys):
    path = tmp_path / 'missing.json'
    assert main(['--config', str(path), 'model', 'status']) == 0
    assert not path.exists()
    result = capsys.readouterr()
    assert 'Model status' in result.out
    assert result.err == ''
