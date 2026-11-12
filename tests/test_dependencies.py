"""Unit tests for direct dependencies in depvis.dependencies."""

from depvis.dependencies import PackageInfo, RepositorySource, classify
from depvis.requirements import Requirement

PYPI = "https://pypi.org/pypi"


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


def test_root_is_described_in_the_configured_version(fake_repository):
    """The analysed package is read in its version, extras are left out."""
    source = RepositorySource(fake_repository.url, "requests", "2.32.3")
    assert source.describe("requests") == PackageInfo(
        "requests",
        "2.32.3",
        ("charset-normalizer", "idna", "urllib3", "certifi"),
    )
    assert fake_repository.requested_urls() == [
        f"{PYPI}/requests/2.32.3/json"
    ]


def test_other_packages_are_described_in_latest_version(fake_repository):
    """Dependencies are read in the latest version of the repository."""
    fake_repository.add_release("demo", "1.0", ["idna"])
    fake_repository.add_release("demo", "2.0", ["zipp"])
    source = RepositorySource(fake_repository.url, "requests", "2.32.3")
    assert source.describe("demo") == PackageInfo("demo", "2.0", ("zipp",))
    assert fake_repository.requested_urls() == [f"{PYPI}/demo/json"]


def test_unparsable_dependencies_become_problems(fake_repository):
    """Broken dependency strings are reported with the package."""
    fake_repository.add_release("odd", "1.0", ["idna", "!!!"])
    source = RepositorySource(fake_repository.url, "odd", "1.0")
    assert source.describe("odd") == PackageInfo(
        "odd",
        "1.0",
        ("idna",),
        (
            "odd 1.0: skipped dependency '!!!': "
            "not a PEP 508 dependency string",
        ),
    )
