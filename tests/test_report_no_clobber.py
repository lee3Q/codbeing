"""Existing report paths remain untouched, including races and dangling links."""
from pathlib import Path
from unittest.mock import patch

from codbeing.__main__ import _next_report_path, _write_report


def test_report_created_after_precheck_is_not_overwritten(tmp_path, capsys):
    destination = tmp_path / "report.md"
    original_open = Path.open
    def competing_open(path, mode="r", *args, **kwargs):
        if path == destination and mode in {"w", "x"}:
            with original_open(destination, "w", encoding="utf-8") as handle:
                handle.write("other writer's report")
        return original_open(path, mode, *args, **kwargs)
    with patch.object(Path, "open", competing_open):
        assert _write_report(destination, "new report") == 2
    assert destination.read_text(encoding="utf-8") == "other writer's report"
    assert "report file already exists" in capsys.readouterr().out


def test_report_refuses_dangling_symlink_without_creating_target(tmp_path, capsys):
    target = tmp_path / "unrelated.md"
    destination = tmp_path / "report.md"
    destination.symlink_to(target)
    assert _write_report(destination, "new report") == 2
    assert destination.is_symlink()
    assert not target.exists()
    assert "report file already exists" in capsys.readouterr().out


def test_numbered_report_skips_dangling_symlinks(tmp_path):
    target = tmp_path / "unrelated.md"
    first = tmp_path / "trace-runtime-analysis-1.md"
    first.symlink_to(target)
    chosen = _next_report_path(tmp_path, "trace")
    assert chosen == tmp_path / "trace-runtime-analysis-2.md"
    assert _write_report(chosen, "new report") == 0
    assert first.is_symlink()
    assert not target.exists()
    assert chosen.read_text(encoding="utf-8") == "new report"


def test_new_report_and_existing_regular_report_keep_public_messages(tmp_path, capsys):
    destination = tmp_path / "nested" / "report.md"
    assert _write_report(destination, "first report") == 0
    assert _write_report(destination, "second report") == 2
    assert destination.read_text(encoding="utf-8") == "first report"
    output = capsys.readouterr().out
    assert "Runtime Analysis report written:" in output
    assert "output error: report file already exists:" in output


def test_two_report_writers_have_one_winner(tmp_path):
    import os
    import subprocess
    import sys
    from concurrent.futures import ThreadPoolExecutor
    destination = tmp_path / "shared.md"
    command = [sys.executable, "-c", "import sys; from pathlib import Path; "
               "from codbeing.__main__ import _write_report; "
               "raise SystemExit(_write_report(Path(sys.argv[1]),sys.argv[2]))", str(destination)]
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(root)}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda content: subprocess.run(
            command + [content], cwd=tmp_path, env=env, text=True, capture_output=True),
            ["writer A", "writer B"]))
    assert sorted(result.returncode for result in results) == [0, 2]
    assert destination.read_text(encoding="utf-8") in {"writer A", "writer B"}
    assert sum("report written:" in result.stdout for result in results) == 1
    assert all(not result.stderr for result in results)
