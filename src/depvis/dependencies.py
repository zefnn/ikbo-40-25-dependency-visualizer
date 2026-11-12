"""Direct dependencies of packages taken from a package repository."""

from dataclasses import dataclass

from depvis.errors import RequirementError
from depvis.repository import fetch_release
from depvis.requirements import canonical_name, parse_requirement


@dataclass(frozen=True)
class DirectDependencies:
    """Direct dependencies of one release, sorted into three groups.

    ``required`` are installed together with the package, some of them
    only on platforms named by their marker. ``optional`` are needed
    only for an extra such as ``requests[socks]``. ``invalid`` describes
    the dependency strings that could not be parsed.
    """

    required: tuple
    optional: tuple
    invalid: tuple


@dataclass(frozen=True)
class PackageInfo:
    """What a source of packages tells about one package.

    ``dependencies`` are the names of the required direct dependencies;
    ``problems`` are warnings found while reading the package.
    """

    name: str
    version: str
    dependencies: tuple
    problems: tuple = ()


class RepositorySource:
    """Describes packages with data from a PyPI-compatible repository.

    The analysed package is taken in the configured version, every
    other package in its latest version in the repository.
    """

    def __init__(self, repository, root_name, root_version):
        """Remember the repository URL and the analysed release."""
        self.repository = repository
        self.root_key = canonical_name(root_name)
        self.root_version = root_version

    def describe(self, name):
        """Download a package and return its required dependencies."""
        is_root = canonical_name(name) == self.root_key
        version = self.root_version if is_root else None
        release = fetch_release(self.repository, name, version)
        groups = classify(release.requires_dist)
        problems = tuple(
            f"{release.name} {release.version}: skipped dependency {text}"
            for text in groups.invalid
        )
        return PackageInfo(
            name=release.name,
            version=release.version,
            dependencies=tuple(item.name for item in groups.required),
            problems=problems,
        )


def classify(lines):
    """Parse dependency strings and sort them into the three groups."""
    required, optional, invalid = [], [], []
    for line in lines:
        try:
            requirement = parse_requirement(line)
        except RequirementError as error:
            invalid.append(f"{line!r}: {error}")
        else:
            group = optional if requirement.is_optional else required
            group.append(requirement)
    return DirectDependencies(tuple(required), tuple(optional), tuple(invalid))
