"""Unit tests for parsing dependency strings in depvis.requirements."""

import pytest

from depvis.errors import RequirementError
from depvis.requirements import (
    Requirement,
    canonical_name,
    parse_requirement,
)

PARSED_EXAMPLES = [
    ("idna", Requirement("idna")),
    ("  six  ", Requirement("six")),
    (
        "urllib3<3,>=1.21.1",
        Requirement("urllib3", specifier="<3,>=1.21.1"),
    ),
    (
        "pluggy (>=1.5, <2)",
        Requirement("pluggy", specifier=">=1.5,<2"),
    ),
    (
        "requests[socks, security] >= 2.0",
        Requirement(
            "requests", extras=("socks", "security"), specifier=">=2.0"
        ),
    ),
    (
        'colorama; sys_platform == "win32"',
        Requirement("colorama", marker='sys_platform == "win32"'),
    ),
    (
        'tomli>=1 ; python_version < "3.11"',
        Requirement(
            "tomli", specifier=">=1", marker='python_version < "3.11"'
        ),
    ),
    (
        "zope.interface==5.*",
        Requirement("zope.interface", specifier="==5.*"),
    ),
    (
        "pkg @ https://example.com/pkg-1.0.whl",
        Requirement("pkg", specifier="@ https://example.com/pkg-1.0.whl"),
    ),
]


@pytest.mark.parametrize("text, expected", PARSED_EXAMPLES)
def test_parse_requirement(text, expected):
    """Valid PEP 508 strings are split into their parts."""
    assert parse_requirement(text) == expected


@pytest.mark.parametrize("text", ["", "!!!", "-dash", "(idna)"])
def test_parse_requirement_rejects_strings_without_name(text):
    """A string must start with a package name."""
    with pytest.raises(RequirementError, match="not a PEP 508 dependency"):
        parse_requirement(text)


@pytest.mark.parametrize("text", ["pkg >>1", "pkg >=1.0, foo", "pkg 1.0"])
def test_parse_requirement_rejects_bad_specifiers(text):
    """Every part of the version specifier must be 'operator version'."""
    with pytest.raises(RequirementError, match="invalid version specifier"):
        parse_requirement(text)


def test_parse_requirement_rejects_bad_extras():
    """Extras must be valid names."""
    with pytest.raises(RequirementError, match="invalid extra name"):
        parse_requirement("pkg[bad extra]")


@pytest.mark.parametrize(
    "marker, optional",
    [
        ('extra == "socks"', True),
        ('"dev" == extra', True),
        ('python_version < "3.11" and extra == "test"', True),
        ('python_version < "3.11"', False),
        ('platform_machine == "extra"', False),
        ("", False),
    ],
)
def test_is_optional_detects_extra_markers(marker, optional):
    """Only a marker that uses the extra variable makes it optional."""
    assert Requirement("pkg", marker=marker).is_optional is optional


@pytest.mark.parametrize(
    "name, key",
    [
        ("requests", "requests"),
        ("PySocks", "pysocks"),
        ("zope.interface", "zope-interface"),
        ("typing__extensions", "typing-extensions"),
        ("A-_.B", "a-b"),
    ],
)
def test_canonical_name(name, key):
    """Names are lower-cased and separator runs become one '-'."""
    assert canonical_name(name) == key


def test_requirement_key_is_the_canonical_name():
    """The key of a requirement is its normalized name."""
    assert Requirement("Typing_Extensions").key == "typing-extensions"
