"""
Tests for deploy/kiosk-launch.sh using a fake poetry and a fake app, in a temp folder.
They check that the launcher restarts the app, honours the stop file, and refuses to
run twice.
"""

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

LAUNCHER = Path(__file__).resolve().parents[2] / "deploy" / "kiosk-launch.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("flock") is None,
    reason="needs bash and flock",
)


def _make_fakes(tmp_path: Path, app_body: str) -> dict[str, str]:
    """Creates a fake poetry that points at a fake python running `app_body`."""
    fake_python = tmp_path / "fake-python"
    fake_python.write_text(f"#!/usr/bin/env bash\n{app_body}\n")
    fake_python.chmod(0o755)

    fake_poetry = tmp_path / "fake-poetry"
    fake_poetry.write_text(f'#!/usr/bin/env bash\necho "{fake_python}"\n')
    fake_poetry.chmod(0o755)

    env = dict(os.environ)
    env.update(
        {
            "XDG_STATE_HOME": str(tmp_path / "state"),
            "POETRY": str(fake_poetry),
            "RESTART_DELAY": "0",
        }
    )
    return env


def test_restarts_app_until_stop_file(tmp_path: Path) -> None:
    """The app is started again after it exits, until the stop file appears."""
    runs = tmp_path / "runs"
    stop = tmp_path / "state" / "barcode-kiosk" / "stop"
    # Each run appends a line; the third run asks the launcher to stop.
    app = (
        f'echo run >> "{runs}"\n'
        f'[ "$(wc -l < "{runs}")" -ge 3 ] && touch "{stop}"\n'
        "exit 1"
    )
    env = _make_fakes(tmp_path, app)

    result = subprocess.run(["bash", str(LAUNCHER)], env=env, timeout=30)

    assert result.returncode == 0
    assert runs.read_text().count("run") == 3
    log = (tmp_path / "state" / "barcode-kiosk" / "kiosk.log").read_text()
    assert "kiosk app exited with code 1" in log
    assert "stop file present" in log


def test_second_launcher_exits_immediately(tmp_path: Path) -> None:
    """Only one launcher runs at a time."""
    stop = tmp_path / "state" / "barcode-kiosk" / "stop"
    env = _make_fakes(tmp_path, "sleep 5")

    first = subprocess.Popen(["bash", str(LAUNCHER)], env=env)
    try:
        time.sleep(1.0)
        second = subprocess.run(["bash", str(LAUNCHER)], env=env, timeout=10)
        assert second.returncode == 0
        log = (tmp_path / "state" / "barcode-kiosk" / "kiosk.log").read_text()
        assert "another launcher is already running" in log
    finally:
        stop.parent.mkdir(parents=True, exist_ok=True)
        stop.touch()
        first.wait(timeout=20)


def test_missing_poetry_env_exits_with_error(tmp_path: Path) -> None:
    """If the poetry environment can't be found, the launcher logs it and stops."""
    env = _make_fakes(tmp_path, "exit 0")
    env["POETRY"] = str(tmp_path / "does-not-exist")

    result = subprocess.run(["bash", str(LAUNCHER)], env=env, timeout=10)

    assert result.returncode == 1
    log = (tmp_path / "state" / "barcode-kiosk" / "kiosk.log").read_text()
    assert "poetry environment not found" in log
