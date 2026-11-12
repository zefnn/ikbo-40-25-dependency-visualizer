"""Downloading release metadata from a repository with the PyPI JSON API.

The dependencies of a release are read from the ``info.requires_dist``
field of ``{repository}/{name}/{version}/json``, and those of the
latest release from ``{repository}/{name}/json``; for PyPI the
repository URL is ``https://pypi.org/pypi``. Only the standard library
is used: ``urllib`` for HTTP and ``json`` for decoding.
"""

import gzip
import json
import ssl
import zlib
from dataclasses import dataclass
from http import HTTPStatus
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from depvis.errors import NetworkError, PackageNotFoundError, RepositoryError
from depvis.requirements import canonical_name

REQUEST_TIMEOUT = 10
DOWNLOAD_ATTEMPTS = 3
USER_AGENT = "depvis (educational dependency graph visualizer)"
GZIP_ENCODING = "gzip"
REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
    "Accept-Encoding": GZIP_ENCODING,
}
SSL_HINT = (
    " (Python cannot check HTTPS certificates; for Python from"
    " python.org on macOS run 'Install Certificates.command')"
)


@dataclass(frozen=True)
class Release:
    """Project name, version and Requires-Dist strings of a release."""

    name: str
    version: str
    requires_dist: tuple


def release_url(repository, name, version=None):
    """Return the JSON API address of a release, or of the latest one."""
    parts = [repository.rstrip("/"), quote(canonical_name(name), safe="")]
    if version is not None:
        parts.append(quote(version, safe=""))
    parts.append("json")
    return "/".join(parts)


def fetch_release(repository, name, version=None):
    """Download a release of a package; the latest one without version."""
    url = release_url(repository, name, version)
    try:
        data = fetch_json(url)
    except PackageNotFoundError:
        if version is None:
            raise PackageNotFoundError(
                missing_package_text(repository, name)
            ) from None
        raise explain_missing_release(repository, name, version) from None
    return Release(
        name=info_text(data, "name") or name,
        version=info_text(data, "version") or (version or ""),
        requires_dist=tuple(read_requires_dist(url, data)),
    )


def fetch_json(url):
    """Download ``url`` and decode the answer as JSON."""
    body, encoding = download(url)
    try:
        return json.loads(unpack(url, body, encoding))
    except ValueError:
        raise RepositoryError(f"{url}: the answer is not JSON") from None


def download(url):
    """Download ``url``; a network failure is retried a few times."""
    attempts_left = DOWNLOAD_ATTEMPTS
    while True:
        try:
            return download_once(url)
        except NetworkError:
            attempts_left -= 1
            if not attempts_left:
                raise


def download_once(url):
    """Return the body of the answer and its Content-Encoding header."""
    request = Request(url, headers=REQUEST_HEADERS)
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as answer:
            return answer.read(), answer.headers.get("Content-Encoding", "")
    except HTTPError as error:
        raise http_failure(url, error) from None
    except URLError as error:
        raise download_failure(url, error.reason) from None
    except (OSError, HTTPException) as error:
        raise download_failure(url, error) from None


def unpack(url, body, encoding):
    """Decompress a gzip answer; any other answer is returned as is."""
    if encoding.strip().lower() != GZIP_ENCODING:
        return body
    try:
        return gzip.decompress(body)
    except (OSError, EOFError, zlib.error):
        raise RepositoryError(f"{url}: the gzip answer is damaged") from None


def http_failure(url, error):
    """Turn an HTTP error status into a repository error."""
    if error.code == HTTPStatus.NOT_FOUND:
        return PackageNotFoundError(f"{url}: not found")
    return RepositoryError(f"{url}: HTTP error {error.code} {error.reason}")


def download_failure(url, reason):
    """Describe why nothing could be downloaded from ``url``.

    Certificate problems will not go away by themselves, so only the
    other failures are ``NetworkError`` that is worth retrying.
    """
    if isinstance(reason, TimeoutError):
        return NetworkError(
            f"{url}: no answer within {REQUEST_TIMEOUT} seconds"
        )
    message = f"cannot download {url}: {reason}"
    if isinstance(reason, ssl.SSLCertVerificationError):
        return RepositoryError(message + SSL_HINT)
    return NetworkError(message)


def missing_package_text(repository, name):
    """Return the message for a package unknown to the repository."""
    return f"package {name!r} not found in {repository}"


def explain_missing_release(repository, name, version):
    """Build the error for a 404: missing package or missing version."""
    try:
        data = fetch_json(release_url(repository, name))
    except PackageNotFoundError:
        return PackageNotFoundError(missing_package_text(repository, name))
    message = f"package {name!r} has no version {version!r} in {repository}"
    latest = info_text(data, "version")
    if latest:
        message += f" (latest version: {latest})"
    return PackageNotFoundError(message)


def info_object(data):
    """Return the ``info`` object of a JSON answer, or None."""
    info = data.get("info") if isinstance(data, dict) else None
    return info if isinstance(info, dict) else None


def info_text(data, field_name):
    """Return a text field of the ``info`` object, or an empty string."""
    value = (info_object(data) or {}).get(field_name)
    return value if isinstance(value, str) else ""


def read_requires_dist(url, data):
    """Take the ``info.requires_dist`` list; ``null`` means no entries."""
    info = info_object(data)
    if info is None or "requires_dist" not in info:
        raise RepositoryError(f"{url}: no 'info.requires_dist' in the answer")
    requires_dist = info["requires_dist"]
    if requires_dist is None:
        return []
    if not is_string_list(requires_dist):
        raise RepositoryError(
            f"{url}: 'info.requires_dist' is not a list of strings"
        )
    return requires_dist


def is_string_list(value):
    """Tell whether ``value`` is a list made only of strings."""
    if not isinstance(value, list):
        return False
    return all(isinstance(item, str) for item in value)
