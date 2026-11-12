"""Checks that turn raw INI strings into valid parameter values.

Each check receives the text written in the configuration file,
returns the cleaned value and raises ``ValidationError`` with a short
explanation when the value cannot be used.
"""

import re
from pathlib import Path
from urllib.parse import urlsplit

from depvis.errors import ValidationError

TRUE_WORDS = ("true", "yes", "on", "1")
FALSE_WORDS = ("false", "no", "off", "0")
URL_SCHEMES = ("http", "https")
IMAGE_SUFFIX = ".png"
PACKAGE_NAME_PATTERN = re.compile(
    r"[A-Z0-9](?:[A-Z0-9._-]*[A-Z0-9])?", re.IGNORECASE
)
TEST_PACKAGE_NAME_PATTERN = re.compile(r"[A-Z]+")
FILTER_PATTERN = re.compile(r"[A-Za-z0-9._-]*")
VERSION_PATTERN = re.compile(
    r"v?(?:[0-9]+!)?[0-9]+(?:\.[0-9]+)*"
    r"(?:[-_.]?(?:alpha|a|beta|b|preview|pre|c|rc)[-_.]?[0-9]*)?"
    r"(?:-[0-9]+|[-_.]?(?:post|rev|r)[-_.]?[0-9]*)?"
    r"(?:[-_.]?dev[-_.]?[0-9]*)?"
    r"(?:\+[a-z0-9]+(?:[-_.][a-z0-9]+)*)?",
    re.IGNORECASE,
)


def require_text(value):
    """Return ``value`` without surrounding spaces; fail if it is empty."""
    text = value.strip()
    if not text:
        raise ValidationError("must not be empty")
    return text


def parse_flag(value):
    """Convert a true/false style word into a ``bool``."""
    word = require_text(value)
    if word.lower() in TRUE_WORDS:
        return True
    if word.lower() in FALSE_WORDS:
        return False
    raise ValidationError(
        f"{word!r} is not a boolean (use true/false, yes/no, on/off, 1/0)"
    )


def check_package_name(value, test_mode):
    """Check a pip package name, or a test name of capital letters."""
    name = require_text(value)
    if test_mode and not TEST_PACKAGE_NAME_PATTERN.fullmatch(name):
        raise ValidationError(
            f"{name!r} is not a test package name (capital letters A-Z)"
        )
    if not PACKAGE_NAME_PATTERN.fullmatch(name):
        raise ValidationError(f"{name!r} is not a valid pip package name")
    return name


def check_repository(value, test_mode):
    """Check the repository: an http(s) URL or a test repository file."""
    location = require_text(value)
    if test_mode:
        check_test_repository(location)
    else:
        check_repository_url(location)
    return location


def check_repository_url(url):
    """Fail unless ``url`` is an absolute http or https URL."""
    if any(char.isspace() for char in url):
        raise ValidationError(f"URL {url!r} must not contain spaces")
    try:
        parts = urlsplit(url)
    except ValueError:
        raise ValidationError(f"{url!r} is not a valid URL") from None
    if parts.scheme not in URL_SCHEMES or not parts.hostname:
        raise ValidationError(
            f"{url!r} is not an http(s) URL "
            "(test files need test_mode = true)"
        )


def check_test_repository(location):
    """Fail unless ``location`` is the path of an existing file."""
    path = Path(location)
    if not path.exists():
        raise ValidationError(f"file {location!r} does not exist")
    if not path.is_file():
        raise ValidationError(f"{location!r} is not a file")


def check_version(value):
    """Check a package version written in the PEP 440 format."""
    version = require_text(value)
    if not VERSION_PATTERN.fullmatch(version):
        raise ValidationError(
            f"{version!r} is not a PEP 440 version (e.g. 2.32.3)"
        )
    return version


def check_output_image(value):
    """Check the name of the PNG file the graph image is saved to."""
    name = require_text(value)
    path = Path(name)
    if path.suffix.lower() != IMAGE_SUFFIX:
        raise ValidationError(f"{name!r} does not end with {IMAGE_SUFFIX}")
    if path.is_dir():
        raise ValidationError(f"{name!r} is a directory, not a file name")
    if not path.parent.is_dir():
        raise ValidationError(
            f"directory {str(path.parent)!r} does not exist"
        )
    return name


def check_filter(value):
    """Check the optional substring used to skip packages by name."""
    text = value.strip()
    if not FILTER_PATTERN.fullmatch(text):
        raise ValidationError(
            f"{text!r} may contain only Latin letters, digits and . _ -"
        )
    return text
