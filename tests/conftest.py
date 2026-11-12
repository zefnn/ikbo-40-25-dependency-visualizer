"""Shared fixtures for the depvis test suite."""

import io
import json
from http import HTTPStatus
from urllib.error import HTTPError

import pytest

from depvis.requirements import canonical_name

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
REQUESTS_REQUIRES_DIST = [
    "charset-normalizer<4,>=2",
    "idna<4,>=2.5",
    "urllib3<3,>=1.21.1",
    "certifi>=2017.4.17",
    'PySocks!=1.5.7,>=1.5.6; extra == "socks"',
    'chardet<6,>=3.0.2; extra == "use-chardet-on-py3"',
]


class FakeRepository:
    """Answers ``urlopen`` calls from prepared pages, not the network.

    An address without a page answers HTTP 404, as PyPI does for unknown
    packages and versions. A page holds either the bytes of the answer
    or an exception that ``urlopen`` should raise.
    """

    url = VALID_VALUES["repository"]

    def __init__(self):
        """Start with requests 2.32.3, the package of the default config."""
        self.pages = {}
        self.requests = []
        self.timeouts = []
        self.add_release("requests", "2.32.3", REQUESTS_REQUIRES_DIST)

    def add_page(self, path, answer):
        """Serve ``answer`` at the address ``{url}/{path}``."""
        self.pages[f"{self.url}/{path}"] = answer

    def add_release(self, name, version, requires_dist):
        """Serve a release that is also the latest one of the package."""
        info = {
            "name": name,
            "version": version,
            "requires_dist": requires_dist,
        }
        body = json.dumps({"info": info}).encode()
        self.add_page(f"{canonical_name(name)}/{version}/json", body)
        self.add_page(f"{canonical_name(name)}/json", body)

    def open(self, request, timeout):
        """Imitate ``urlopen``: return the page or raise like urllib."""
        self.requests.append(request)
        self.timeouts.append(timeout)
        answer = self.pages.get(request.full_url)
        if answer is None:
            raise HTTPError(
                request.full_url, HTTPStatus.NOT_FOUND, "Not Found", None, None
            )
        if isinstance(answer, Exception):
            raise answer
        return io.BytesIO(answer)


def refuse_network(request, timeout):
    """Stand in for ``urlopen`` and refuse to open anything."""
    raise AssertionError(
        f"network access in tests: {request.full_url} (timeout {timeout})"
    )


def render_config(values):
    """Build the text of a ``[settings]`` section with ``values``."""
    lines = ["[settings]"]
    lines.extend(f"{name} = {text}" for name, text in values.items())
    return "\n".join(lines) + "\n"


@pytest.fixture(autouse=True)
def work_in_tmp_path(tmp_path, monkeypatch):
    """Run every test inside its own temporary working directory."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """Make any real network access from the tests fail loudly."""
    monkeypatch.setattr("depvis.repository.urlopen", refuse_network)


@pytest.fixture
def fake_repository(monkeypatch):
    """Serve repository answers from a FakeRepository and return it."""
    repository = FakeRepository()
    monkeypatch.setattr("depvis.repository.urlopen", repository.open)
    return repository


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
