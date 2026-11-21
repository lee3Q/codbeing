import os

from codbeing.config import CodbeingConfig, load_config, save_config


def test_new_config_is_owner_only_under_group_umask(tmp_path):
    path = tmp_path / "private" / "config.json"
    previous_umask = os.umask(0o022)
    try:
        save_config(CodbeingConfig(model_provider="glm"), path)
    finally:
        os.umask(previous_umask)

    assert path.stat().st_mode & 0o777 == 0o600
    assert load_config(path).model_provider == "glm"


def test_config_overwrite_preserves_latest_value_and_mode(tmp_path):
    path = tmp_path / "config.json"
    save_config(CodbeingConfig(model_provider="codex"), path)
    save_config(CodbeingConfig(model_provider="glm"), path)

    assert load_config(path).model_provider == "glm"
    assert path.stat().st_mode & 0o777 == 0o600
