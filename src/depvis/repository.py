"""Downloading release metadata from a repository with the PyPI JSON API.

The dependencies of a release are read from the ``info.requires_dist``
field of ``{repository}/{name}/{version}/json``; for PyPI the
repository URL is ``https://pypi.org/pypi``. Only the standard library
is used: ``urllib`` for HTTP and ``json`` for decoding.
"""

import json
import ssl
from http import HTTPStatus
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from depvis.errors import PackageNotFoundError, RepositoryError
from depvis.requirements import canonical_name

REQUEST_TIMEOUT = 10
USER_AGENT = "depvis (educational dependency graph visualizer)"
SSL_HINT = (
    " (Python cannot check HTTPS certificates; for Python from"
    " python.org on macOS run 'Install Certificates.command')"
)


def release_url(repository, name, version=None):
    """Return the JSON API address of a release, or of the latest one."""
    parts = [repository.rstrip("/"), quote(canonical_name(name), safe="")]
    if version is not None:
        parts.append(quote(version, safe=""))
    parts.append("json")
    return "/".join(parts)


def fetch_requires_dist(repository, name, version):
    """Return the Requires-Dist strings of one release of a package."""
    url = release_url(repository, name, version)
    try:
        data = fetch_json(url)
    except PackageNotFoundError:
        raise explain_missing_release(repository, name, version) from None
    return read_requires_dist(url, data)


def fetch_json(url):
    """Download ``url`` and decode the answer as JSON."""
    request = Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as answer:
            body = answer.read()
    except HTTPError as error:
        raise http_failure(url, error) from None
    except URLError as error:
        raise download_failure(url, error.reason) from None
    except (OSError, HTTPException) as error:
        raise download_failure(url, error) from None
    try:
        return json.loads(body)
    except ValueError:
        raise RepositoryError(f"{url}: the answer is not JSON") from None


def http_failure(url, error):
    """Turn an HTTP error status into a repository error."""
    if error.code == HTTPStatus.NOT_FOUND:
        return PackageNotFoundError(f"{url}: not found")
    return RepositoryError(f"{url}: HTTP error {error.code} {error.reason}")


def download_failure(url, reason):
    """Describe why nothing could be downloaded from ``url``."""
    if isinstance(reason, TimeoutError):
        return RepositoryError(
            f"{url}: no answer within {REQUEST_TIMEOUT} seconds"
        )
    message = f"cannot download {url}: {reason}"
    if isinstance(reason, ssl.SSLCertVerificationError):
        message += SSL_HINT
    return RepositoryError(message)


def explain_missing_release(repository, name, version):
    """Build the error for a 404: missing package or missing version."""
    try:
        data = fetch_json(release_url(repository, name))
    except PackageNotFoundError:
        return PackageNotFoundError(
            f"package {name!r} not found in {repository}"
        )
    message = f"package {name!r} has no version {version!r} in {repository}"
    latest = latest_version(data)
    if latest:
        message += f" (latest version: {latest})"
    return PackageNotFoundError(message)


def info_object(data):
    """Return the ``info`` object of a JSON answer, or None."""
    info = data.get("info") if isinstance(data, dict) else None
    return info if isinstance(info, dict) else None


def latest_version(data):
    """Return ``info.version`` of a package answer, or an empty string."""
    info = info_object(data) or {}
    version = info.get("version")
    return version if isinstance(version, str) else ""


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
