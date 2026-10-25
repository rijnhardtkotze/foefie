from pathlib import Path

import pytest

from foefie.workspace import find_root


def make_workspace(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "dev.code-workspace").write_text("{}")
    return path


def test_find_root_from_cwd(tmp_path, monkeypatch):
    root = make_workspace(tmp_path / "ws")
    nested = root / "a" / "b"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    assert find_root() == root.resolve()


def test_find_root_falls_back_to_package(tmp_path, monkeypatch):
    root = make_workspace(tmp_path / "ws")
    module = root / "mantlepin-labs" / "foefie" / "src" / "foefie" / "workspace.py"
    module.parent.mkdir(parents=True)
    module.write_text("")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert find_root(module=module) == root.resolve()


def test_find_root_missing_exits(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    module = tmp_path / "pkg" / "workspace.py"
    with pytest.raises(SystemExit) as exc:
        find_root(module=module)
    assert exc.value.code not in (0, None)
    assert "dev.code-workspace not found" in str(exc.value.code)
