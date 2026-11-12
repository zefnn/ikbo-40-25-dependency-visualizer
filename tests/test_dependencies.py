"""Unit tests for collecting direct dependencies in depvis.dependencies."""

from depvis.dependencies import (
    DirectDependencies,
    classify,
    get_direct_dependencies,
)
from depvis.requirements import Requirement


def names(requirements):
    """Return the names of the given requirements as a list."""
    return [item.name for item in requirements]


def test_requests_dependencies_are_classified(fake_repository):
    """Dependencies of an extra are optional, the others are required."""
    result = get_direct_dependencies(fake_repository.url, "requests", "2.32.3")
    assert names(result.required) == [
        "charset-normalizer",
        "idna",
        "urllib3",
        "certifi",
    ]
    assert names(result.optional) == ["PySocks", "chardet"]
    assert not result.invalid


def test_platform_dependencies_stay_required():
    """A marker without an extra keeps the dependency required."""
    result = classify(
        ['colorama; sys_platform == "win32"', 'argcomplete; extra == "dev"']
    )
    assert result.required == (
        Requirement("colorama", marker='sys_platform == "win32"'),
    )
    assert result.optional == (
        Requirement("argcomplete", marker='extra == "dev"'),
    )


def test_unparsable_strings_are_collected():
    """Strings that cannot be parsed are kept with the reason."""
    result = classify(["idna", "!!!", "pkg >>1"])
    assert result.required == (Requirement("idna"),)
    assert result.invalid == (
        "'!!!': not a PEP 508 dependency string",
        "'pkg >>1': invalid version specifier '>>1'",
    )


def test_release_without_dependencies(fake_repository):
    """A release without Requires-Dist gives three empty groups."""
    fake_repository.add_release("certifi", "2024.8.30", None)
    result = get_direct_dependencies(
        fake_repository.url, "certifi", "2024.8.30"
    )
    assert result == DirectDependencies((), (), ())
