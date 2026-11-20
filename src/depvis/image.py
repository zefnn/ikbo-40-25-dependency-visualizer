"""PNG image of the graph, drawn from its Mermaid text by mermaid.ink.

mermaid.ink is the rendering service used by the Mermaid Live Editor:
``https://mermaid.ink/img/pako:<code>?type=png`` returns the picture of
a diagram. ``<code>`` is the zlib-compressed JSON {"code": <text>}
encoded with URL-safe base64, the format of the Mermaid Live Editor.
Only the standard library is used: zlib, base64, json and urllib.
"""

import base64
import json
import zlib
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from depvis.errors import ImageError
from depvis.repository import USER_AGENT

RENDER_URL = "https://mermaid.ink/img/pako:{code}?type=png"
RENDER_TIMEOUT = 30
RENDER_ATTEMPTS = 3
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
COMPRESSION_LEVEL = 9
THEME = "default"


def render_url(mermaid_text):
    """Return the mermaid.ink address that draws ``mermaid_text``."""
    state = json.dumps({"code": mermaid_text, "mermaid": {"theme": THEME}})
    packed = zlib.compress(state.encode("utf-8"), COMPRESSION_LEVEL)
    code = base64.urlsafe_b64encode(packed).decode("ascii")
    return RENDER_URL.format(code=code)


def render_png(mermaid_text):
    """Download the PNG picture of a Mermaid diagram from mermaid.ink."""
    request = Request(
        render_url(mermaid_text),
        headers={"User-Agent": USER_AGENT, "Accept": "image/png"},
    )
    data = fetch_image(request)
    if not data.startswith(PNG_SIGNATURE):
        raise ImageError("mermaid.ink did not return a PNG image")
    return data


def fetch_image(request):
    """Download the picture; a network failure is retried a few times."""
    attempts_left = RENDER_ATTEMPTS
    while True:
        try:
            with urlopen(request, timeout=RENDER_TIMEOUT) as answer:
                return answer.read()
        except HTTPError as error:
            raise ImageError(
                f"mermaid.ink answered HTTP {error.code} {error.reason}"
            ) from None
        except (URLError, OSError, HTTPException) as error:
            attempts_left -= 1
            if not attempts_left:
                reason = getattr(error, "reason", error)
                message = f"cannot reach mermaid.ink: {reason}"
                raise ImageError(message) from None


def save_png(path, data):
    """Write the PNG bytes to the file ``path``."""
    try:
        with open(path, "wb") as stream:
            stream.write(data)
    except OSError as error:
        raise ImageError(
            f"cannot write {path!r}: {error.strerror}"
        ) from None
