"""Unit tests for the PNG picture of the graph in depvis.image."""

import base64
import json
import zlib
from http import HTTPStatus
from urllib.error import HTTPError, URLError

import pytest

from depvis.errors import ImageError
from depvis.image import (
    PNG_SIGNATURE,
    RENDER_ATTEMPTS,
    RENDER_TIMEOUT,
    render_png,
    render_url,
    save_png,
)
from depvis.repository import USER_AGENT

DIAGRAM = 'flowchart TD\n    n0["A"] --> n1["B"]'
URL_PREFIX = "https://mermaid.ink/img/pako:"
URL_SUFFIX = "?type=png"


def test_render_url_packs_the_diagram():
    """The address holds the zlib-packed, base64-encoded diagram."""
    url = render_url(DIAGRAM)
    assert url.startswith(URL_PREFIX)
    assert url.endswith(URL_SUFFIX)
    code = url.removeprefix(URL_PREFIX).removesuffix(URL_SUFFIX)
    state = json.loads(zlib.decompress(base64.urlsafe_b64decode(code)))
    assert state["code"] == DIAGRAM


def test_png_is_downloaded(fake_renderer):
    """The picture is requested from mermaid.ink with a timeout."""
    assert render_png(DIAGRAM) == fake_renderer.picture
    (request,) = fake_renderer.requests
    assert request.full_url == render_url(DIAGRAM)
    assert request.get_header("User-agent") == USER_AGENT
    assert fake_renderer.timeouts == [RENDER_TIMEOUT]


def test_answer_that_is_not_png_is_rejected(fake_renderer):
    """Only an answer with the PNG signature is accepted."""
    fake_renderer.picture = b"<html>Error</html>"
    with pytest.raises(ImageError, match="did not return a PNG image"):
        render_png(DIAGRAM)


def test_http_error_is_reported(fake_renderer):
    """An HTTP error of the service is reported with its status."""
    fake_renderer.failures = [
        HTTPError("url", HTTPStatus.BAD_REQUEST, "Bad Request", None, None)
    ]
    with pytest.raises(ImageError) as caught:
        render_png(DIAGRAM)
    assert str(caught.value) == "mermaid.ink answered HTTP 400 Bad Request"


def test_network_failure_is_retried(fake_renderer):
    """A temporary network failure is followed by another attempt."""
    fake_renderer.failures = [URLError("timed out")]
    assert render_png(DIAGRAM) == fake_renderer.picture
    assert fake_renderer.timeouts == [RENDER_TIMEOUT, RENDER_TIMEOUT]


def test_network_failure_is_reported_after_all_attempts(fake_renderer):
    """Without network the error names the reason."""
    fake_renderer.failures = [URLError("offline")] * RENDER_ATTEMPTS
    with pytest.raises(ImageError) as caught:
        render_png(DIAGRAM)
    assert str(caught.value) == "cannot reach mermaid.ink: offline"
    assert fake_renderer.timeouts == [RENDER_TIMEOUT] * RENDER_ATTEMPTS


def test_png_is_saved(tmp_path):
    """The picture is written to the configured file."""
    path = tmp_path / "graph.png"
    save_png(str(path), PNG_SIGNATURE)
    assert path.read_bytes() == PNG_SIGNATURE


def test_unwritable_path_is_reported(tmp_path):
    """A path that cannot be written is reported."""
    with pytest.raises(ImageError, match="cannot write"):
        save_png(str(tmp_path), PNG_SIGNATURE)
