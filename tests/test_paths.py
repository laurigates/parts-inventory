"""Data-directory resolution: inventory data lives outside the code repo."""

from pathlib import Path

from parts_inventory.paths import data_dir


def test_env_override_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("PARTS_INVENTORY_DATA", str(tmp_path / "custom"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    assert data_dir() == tmp_path / "custom"


def test_xdg_data_home_used_when_set(monkeypatch, tmp_path):
    monkeypatch.delenv("PARTS_INVENTORY_DATA", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    assert data_dir() == tmp_path / "xdg" / "parts-inventory"


def test_defaults_to_local_share(monkeypatch):
    monkeypatch.delenv("PARTS_INVENTORY_DATA", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    assert data_dir() == Path.home() / ".local" / "share" / "parts-inventory"


def test_empty_env_values_are_ignored(monkeypatch):
    monkeypatch.setenv("PARTS_INVENTORY_DATA", "")
    monkeypatch.setenv("XDG_DATA_HOME", "")
    assert data_dir() == Path.home() / ".local" / "share" / "parts-inventory"


def test_tilde_is_expanded(monkeypatch):
    monkeypatch.setenv("PARTS_INVENTORY_DATA", "~/inv")
    assert data_dir() == Path.home() / "inv"
