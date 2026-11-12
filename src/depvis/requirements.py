"""Parsing of PEP 508 dependency strings taken from package metadata.

A release lists its dependencies as strings such as
``urllib3<3,>=1.21.1`` or ``colorama; sys_platform == "win32"``. This
module splits them into the package name, extras, version specifier
and environment marker by itself, without any packaging libraries.
"""

import re
from dataclasses import dataclass

from depvis.errors import RequirementError

NAME_SEPARATORS = re.compile(r"[-_.]+")
NAME_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?")
REQUIREMENT_PATTERN = re.compile(
    r"(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\s*"
    r"(?:\[(?P<extras>[^\]]*)\])?\s*"
    r"(?P<specifier>[^;]*?)\s*"
    r"(?:;(?P<marker>.*))?"
)
SPECIFIER_CLAUSE_PATTERN = re.compile(
    r"(?:~=|===|==|!=|<=|>=|<|>)\s*[A-Za-z0-9.*+!_-]+"
)
QUOTED_TEXT_PATTERN = re.compile(r"'[^']*'|\"[^\"]*\"")
EXTRA_VARIABLE_PATTERN = re.compile(r"\bextra\b")
URL_REFERENCE_PREFIX = "@"


@dataclass(frozen=True)
class Requirement:
    """One dependency of a release, split into its parts.

    ``name`` is kept as written in the metadata, ``key`` is its PEP 503
    normalized form that is used to compare package names.
    """

    name: str
    extras: tuple = ()
    specifier: str = ""
    marker: str = ""

    @property
    def key(self):
        """Return the normalized package name (PEP 503)."""
        return canonical_name(self.name)

    @property
    def is_optional(self):
        """Tell whether the dependency is needed only for an extra."""
        unquoted = QUOTED_TEXT_PATTERN.sub("", self.marker)
        return bool(EXTRA_VARIABLE_PATTERN.search(unquoted))


def canonical_name(name):
    """Return the PEP 503 form of a name: lower case, '-' separators."""
    return NAME_SEPARATORS.sub("-", name).lower()


def name_matches(name, substring):
    """Tell whether ``name`` contains ``substring`` (PEP 503 compared)."""
    if not substring:
        return False
    return canonical_name(substring) in canonical_name(name)


def parse_requirement(text):
    """Split a PEP 508 dependency string into a ``Requirement``."""
    match = REQUIREMENT_PATTERN.fullmatch(text.strip())
    if not match:
        raise RequirementError("not a PEP 508 dependency string")
    return Requirement(
        name=match["name"],
        extras=split_extras(match["extras"] or ""),
        specifier=clean_specifier(match["specifier"]),
        marker=(match["marker"] or "").strip(),
    )


def split_extras(text):
    """Return the extras listed inside ``[...]`` as a tuple of names."""
    extras = tuple(part.strip() for part in text.split(",") if part.strip())
    for extra in extras:
        if not NAME_PATTERN.fullmatch(extra):
            raise RequirementError(f"invalid extra name {extra!r}")
    return extras


def clean_specifier(text):
    """Return the version specifier without spaces and parentheses."""
    specifier = strip_parentheses(text.strip())
    if not specifier or specifier.startswith(URL_REFERENCE_PREFIX):
        return specifier
    clauses = [clause.strip() for clause in specifier.split(",")]
    for clause in clauses:
        if not SPECIFIER_CLAUSE_PATTERN.fullmatch(clause):
            raise RequirementError(f"invalid version specifier {clause!r}")
    return ",".join("".join(clause.split()) for clause in clauses)


def strip_parentheses(text):
    """Remove the optional parentheses around a version specifier."""
    if text.startswith("(") and text.endswith(")"):
        return text.removeprefix("(").removesuffix(")").strip()
    return text
