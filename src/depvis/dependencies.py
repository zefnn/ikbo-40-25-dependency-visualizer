"""Collecting the direct dependencies of the analysed package."""

from dataclasses import dataclass

from depvis.errors import RequirementError
from depvis.repository import fetch_requires_dist
from depvis.requirements import parse_requirement


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


def get_direct_dependencies(repository, name, version):
    """Download and classify the direct dependencies of a release."""
    return classify(fetch_requires_dist(repository, name, version))


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
