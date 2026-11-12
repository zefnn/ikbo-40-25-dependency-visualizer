"""Shared fixtures for the depvis test suite."""

import pytest

CONFIG_NAME = "config.ini"
VALID_VALUES = {
    "package_name": "requests",
    "repository": "https://pypi.org/pypi",
    "test_mode": "false",
    "version": "2.32.3",
    "output_image": "graph.png",
    "ascii_tree": "false",
    "filter_substring": "",
}


def render_config(values):
    """Build the text of a ``[settings]`` section with ``values``."""
    lines = ["[settings]"]
    lines.extend(f"{name} = {text}" for name, text in values.items())
    return "\n".join(lines) + "\n"


@pytest.fixture(autouse=True)
def work_in_tmp_path(tmp_path, monkeypatch):
    """Run every test inside its own temporary working directory."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def config_path(tmp_path):
    """Return the path where the tests write ``config.ini``."""
    return tmp_path / CONFIG_NAME


@pytest.fixture
def make_config(tmp_path):
    """Return a factory that writes a valid config with some changes.

    Keyword arguments replace parameter values; a value of ``None``
    removes the parameter from the file. The factory returns the path
    of the written file as a string.
    """

    def make(**changes):
        """Write the config with ``changes`` applied; return its path."""
        values = dict(VALID_VALUES, **changes)
        kept = {
            name: text for name, text in values.items() if text is not None
        }
        path = tmp_path / CONFIG_NAME
        path.write_text(render_config(kept), encoding="utf-8")
        return str(path)

    return make


@pytest.fixture
def repo_file(tmp_path):
    """Create a small test repository file and return its path."""
    path = tmp_path / "repo.txt"
    path.write_text("A: B\nB:\n", encoding="utf-8")
    return str(path)
