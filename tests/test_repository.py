"""Unit tests for downloading release data in depvis.repository."""

import gzip
import ssl
from http import HTTPStatus
from http.client import IncompleteRead
from urllib.error import HTTPError, URLError

import pytest

from depvis.errors import PackageNotFoundError, RepositoryError
from depvis.repository import (
    DOWNLOAD_ATTEMPTS,
    GZIP_ENCODING,
    REQUEST_TIMEOUT,
    USER_AGENT,
    Release,
    fetch_release,
    release_url,
)

PYPI = "https://pypi.org/pypi"
DEMO_URL = f"{PYPI}/demo/1.0/json"
DEMO_BODY = (
    b'{"info": {"name": "demo", "version": "1.0", "requires_dist": []}}'
)


def download_error(fake_repository, answer):
    """Serve ``answer`` for demo 1.0 and return the error it causes."""
    fake_repository.add_page("demo/1.0/json", answer)
    with pytest.raises(RepositoryError) as caught:
        fetch_release(fake_repository.url, "demo", "1.0")
    return str(caught.value)


@pytest.mark.parametrize(
    "repository, name, version, url",
    [
        (PYPI, "requests", "2.32.3", f"{PYPI}/requests/2.32.3/json"),
        (PYPI + "/", "requests", None, f"{PYPI}/requests/json"),
        (
            PYPI,
            "Zope.Interface",
            "1.0+local",
            f"{PYPI}/zope-interface/1.0%2Blocal/json",
        ),
    ],
)
def test_release_url(repository, name, version, url):
    """Release addresses follow the layout of the PyPI JSON API."""
    assert release_url(repository, name, version) == url


def test_release_is_read_from_the_versioned_page(fake_repository):
    """Name, version and Requires-Dist of the release are returned."""
    fake_repository.add_release("demo", "1.0", ["idna", "certifi>=2017"])
    assert fetch_release(fake_repository.url, "demo", "1.0") == Release(
        "demo", "1.0", ("idna", "certifi>=2017")
    )


def test_latest_release_is_read_without_version(fake_repository):
    """Without a version the latest release of the package is used."""
    fake_repository.add_release("demo", "1.0", ["idna"])
    fake_repository.add_release("demo", "2.0", ["zipp"])
    assert fetch_release(fake_repository.url, "demo") == Release(
        "demo", "2.0", ("zipp",)
    )
    assert fake_repository.requested_urls() == [f"{PYPI}/demo/json"]


def test_project_name_comes_from_the_repository(fake_repository):
    """The project name is spelled as the repository spells it."""
    fake_repository.add_release("Flask", "3.0.3", [])
    release = fetch_release(fake_repository.url, "flask", "3.0.3")
    assert release.name == "Flask"


def test_null_requires_dist_means_no_dependencies(fake_repository):
    """PyPI gives null for a release without dependencies."""
    release = fetch_release(fake_repository.url, "certifi", "2024.8.30")
    assert not release.requires_dist


def test_request_headers_and_timeout(fake_repository):
    """Requests name the client, accept gzip and have a timeout."""
    fetch_release(fake_repository.url, "requests", "2.32.3")
    (request,) = fake_repository.requests
    assert request.get_header("User-agent") == USER_AGENT
    assert request.get_header("Accept-encoding") == GZIP_ENCODING
    assert fake_repository.timeouts == [REQUEST_TIMEOUT]


def test_gzip_answer_is_unpacked(fake_repository):
    """An answer compressed with gzip is decompressed before parsing."""
    fake_repository.add_page(
        "demo/1.0/json",
        gzip.compress(DEMO_BODY),
        headers={"Content-Encoding": GZIP_ENCODING},
    )
    assert fetch_release(fake_repository.url, "demo", "1.0") == Release(
        "demo", "1.0", ()
    )


def test_damaged_gzip_answer_is_reported(fake_repository):
    """A broken gzip body is reported instead of crashing."""
    fake_repository.add_page(
        "demo/1.0/json",
        b"not gzip at all",
        headers={"Content-Encoding": GZIP_ENCODING},
    )
    with pytest.raises(RepositoryError, match="gzip answer is damaged"):
        fetch_release(fake_repository.url, "demo", "1.0")


def test_missing_version_names_the_latest_one(fake_repository):
    """For a missing version the latest version is suggested."""
    with pytest.raises(PackageNotFoundError) as caught:
        fetch_release(fake_repository.url, "requests", "9.9.9")
    assert str(caught.value) == (
        f"package 'requests' has no version '9.9.9' in {PYPI} "
        "(latest version: 2.32.3)"
    )


def test_missing_version_without_latest_information(fake_repository):
    """Without info.version in the answer no suggestion is made."""
    fake_repository.add_page("odd/json", b'{"releases": {}}')
    with pytest.raises(PackageNotFoundError) as caught:
        fetch_release(fake_repository.url, "odd", "1.0")
    assert str(caught.value) == (
        f"package 'odd' has no version '1.0' in {PYPI}"
    )


def test_missing_package_is_reported(fake_repository):
    """A package unknown to the repository is reported as such."""
    with pytest.raises(PackageNotFoundError) as caught:
        fetch_release(fake_repository.url, "nothing", "1.0")
    assert str(caught.value) == f"package 'nothing' not found in {PYPI}"


def test_missing_latest_release_needs_one_request(fake_repository):
    """Without a version a 404 already means the package is unknown."""
    with pytest.raises(PackageNotFoundError) as caught:
        fetch_release(fake_repository.url, "nothing")
    assert str(caught.value) == f"package 'nothing' not found in {PYPI}"
    assert fake_repository.requested_urls() == [f"{PYPI}/nothing/json"]


def test_http_error_is_reported(fake_repository):
    """HTTP errors other than 404 are reported with their status."""
    error = HTTPError(
        DEMO_URL,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        "Internal Server Error",
        None,
        None,
    )
    assert download_error(fake_repository, error) == (
        f"{DEMO_URL}: HTTP error 500 Internal Server Error"
    )


def test_unknown_host_is_reported_after_retries(fake_repository):
    """A host that cannot be resolved is tried again, then reported."""
    error = URLError("nodename nor servname provided")
    assert download_error(fake_repository, error) == (
        f"cannot download {DEMO_URL}: nodename nor servname provided"
    )
    assert fake_repository.timeouts == [REQUEST_TIMEOUT] * DOWNLOAD_ATTEMPTS


@pytest.mark.parametrize(
    "error", [URLError(TimeoutError("timed out")), TimeoutError("timed out")]
)
def test_timeout_is_reported(fake_repository, error):
    """Timeouts while connecting or reading are reported the same way."""
    assert download_error(fake_repository, error) == (
        f"{DEMO_URL}: no answer within {REQUEST_TIMEOUT} seconds"
    )


def test_network_failure_is_retried(fake_repository):
    """A temporary failure is followed by another attempt."""
    fake_repository.add_page(
        "demo/1.0/json", TimeoutError("timed out"), DEMO_BODY
    )
    assert fetch_release(fake_repository.url, "demo", "1.0") == Release(
        "demo", "1.0", ()
    )
    assert fake_repository.requested_urls() == [DEMO_URL, DEMO_URL]


def test_certificate_problem_gets_a_hint_and_no_retry(fake_repository):
    """An HTTPS certificate error explains how to fix Python on macOS."""
    reason = ssl.SSLCertVerificationError("certificate verify failed")
    message = download_error(fake_repository, URLError(reason))
    assert message.startswith(f"cannot download {DEMO_URL}: ")
    assert "Install Certificates.command" in message
    assert fake_repository.requested_urls() == [DEMO_URL]


def test_broken_transfer_is_reported(fake_repository):
    """A connection broken in the middle of the answer is reported."""
    message = download_error(fake_repository, IncompleteRead(b"{"))
    assert message.startswith(f"cannot download {DEMO_URL}: IncompleteRead")


def test_answer_that_is_not_json_is_reported(fake_repository):
    """An HTML page or other text instead of JSON is reported."""
    assert download_error(fake_repository, b"<html></html>") == (
        f"{DEMO_URL}: the answer is not JSON"
    )


@pytest.mark.parametrize(
    "body", [b"[]", b'{"releases": {}}', b'{"info": {"name": "demo"}}']
)
def test_answer_without_requires_dist_is_reported(fake_repository, body):
    """JSON without info.requires_dist is not a PyPI release answer."""
    assert download_error(fake_repository, body) == (
        f"{DEMO_URL}: no 'info.requires_dist' in the answer"
    )


@pytest.mark.parametrize("value", [b'"idna"', b'["idna", 5]'])
def test_requires_dist_must_be_a_list_of_strings(fake_repository, value):
    """Anything but a list of strings in requires_dist is reported."""
    body = b'{"info": {"requires_dist": ' + value + b"}}"
    assert download_error(fake_repository, body) == (
        f"{DEMO_URL}: 'info.requires_dist' is not a list of strings"
    )
