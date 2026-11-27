from __future__ import annotations

import sys

import pytest

gi = pytest.importorskip("gi")
gi.require_version("Gtk", "3.0")

from gi.repository import Gtk

from nix_shell_gui import app as app_module
from nix_shell_gui import classify, store, terminal
from nix_shell_gui.search import Package


@pytest.fixture(scope="session", autouse=True)
def init_gtk():
    Gtk.init([])


class FakeProcess:
    def __init__(self, returncode: int) -> None:
        self.returncode: int | None = None
        self._returncode = returncode

    def wait(self) -> int:
        self.returncode = self._returncode
        return self._returncode


class FakeGLib:
    def __init__(self) -> None:
        self.idle_callbacks: list[tuple[object, tuple[object, ...]]] = []

    def idle_add(self, function, *args):
        self.idle_callbacks.append((function, args))
        return 1

    def timeout_add(self, _interval, _function, *_args):
        return 1

    def drain(self) -> None:
        while self.idle_callbacks:
            function, args = self.idle_callbacks.pop(0)
            function(*args)


@pytest.fixture
def nix_app(monkeypatch):
    monkeypatch.setattr(app_module, "find_nix", lambda: "/bin/true")
    monkeypatch.setattr(app_module.NixAppStore, "_load_catalog", lambda self: None)
    monkeypatch.setattr(store, "load_favourites", lambda: set())
    monkeypatch.setattr(store, "load_catalog_cache", lambda: [])
    monkeypatch.setattr(store, "store_entry_count", lambda: 0)
    instance = app_module.NixAppStore()
    instance.selected = Package("hello", "hello", "1.0", "a package")
    instance.launch_button.set_sensitive(True)
    yield instance
    instance.window.hide()


def install_fake_glib(monkeypatch) -> FakeGLib:
    fake = FakeGLib()
    monkeypatch.setattr(app_module, "GLib", fake)
    return fake


def test_gui_launch_shows_progress_and_writes_log(nix_app, monkeypatch, tmp_path):
    log_path = tmp_path / "launch-hello.log"
    monkeypatch.setattr(store, "launch_log_path", lambda _attr_path: log_path)
    monkeypatch.setattr(classify, "classify", lambda _nix_bin, _attr_path: "gui")
    calls = []

    def fake_launch_direct(nix_bin, attr_path, log=None):
        calls.append((nix_bin, attr_path, log))
        return FakeProcess(0)

    monkeypatch.setattr(terminal, "launch_direct", fake_launch_direct)
    fake_glib = install_fake_glib(monkeypatch)

    nix_app._on_launch(None)

    assert "Launching hello" in nix_app.status_label.get_text()
    assert nix_app.spinner.get_property("active")
    assert not nix_app.launch_button.get_sensitive()

    nix_app._launch_thread.join(timeout=5)
    assert not nix_app._launch_thread.is_alive()
    assert calls == [("/bin/true", "hello", str(log_path))]

    fake_glib.drain()

    assert "Started hello" in nix_app.status_label.get_text()
    assert not nix_app.spinner.get_property("active")
    assert nix_app.launch_button.get_sensitive()


def test_tui_launch_uses_terminal_and_reports_log(nix_app, monkeypatch, tmp_path):
    log_path = tmp_path / "launch-hello.log"
    monkeypatch.setattr(store, "launch_log_path", lambda _attr_path: log_path)
    monkeypatch.setattr(classify, "classify", lambda _nix_bin, _attr_path: "tui")
    calls = []

    def fake_launch_in_terminal(nix_bin, attr_path, mode, log=None):
        calls.append((nix_bin, attr_path, mode, log))
        return FakeProcess(0)

    monkeypatch.setattr(terminal, "launch_in_terminal", fake_launch_in_terminal)
    fake_glib = install_fake_glib(monkeypatch)

    nix_app._on_launch(None)
    nix_app._launch_thread.join(timeout=5)
    fake_glib.drain()

    assert calls == [("/bin/true", "hello", "tui", str(log_path))]
    assert "Started hello" in nix_app.status_label.get_text()
    assert str(log_path) in nix_app.status_label.get_text()


def test_launch_failure_reports_exit_and_log(nix_app, monkeypatch, tmp_path):
    log_path = tmp_path / "launch-hello.log"
    monkeypatch.setattr(store, "launch_log_path", lambda _attr_path: log_path)
    monkeypatch.setattr(classify, "classify", lambda _nix_bin, _attr_path: "cli")
    monkeypatch.setattr(
        terminal,
        "launch_in_terminal",
        lambda _nix_bin, _attr_path, _mode, log=None: FakeProcess(2),
    )
    fake_glib = install_fake_glib(monkeypatch)

    nix_app._on_launch(None)
    nix_app._launch_thread.join(timeout=5)
    fake_glib.drain()

    status = nix_app.status_label.get_text()
    assert "Launch failed (exit 2)" in status
    assert str(log_path) in status
    assert not nix_app.spinner.get_property("active")
    assert nix_app.launch_button.get_sensitive()


def test_launch_log_path_is_in_config_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "CONFIG_DIR", tmp_path)
    path = store.launch_log_path("python3Packages.some-tool")
    assert path == tmp_path / "launch-python3Packages.some-tool.log"
    assert path.parent.is_dir()


def test_spawn_captures_stdout_and_stderr_in_log(tmp_path):
    log_path = tmp_path / "launch-hello.log"
    process = terminal._spawn(
        [
            sys.executable,
            "-c",
            "import sys; print('out'); print('err', file=sys.stderr)",
        ],
        str(log_path),
    )
    assert process.wait() == 0
    text = log_path.read_text()
    assert "out" in text
    assert "err" in text
