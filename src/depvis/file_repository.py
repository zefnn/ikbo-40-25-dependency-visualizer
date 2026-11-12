"""Test repository: a text file that describes a dependency graph.

Each line describes one package as ``NAME: DEPENDENCY DEPENDENCY ...``.
Names are made of capital Latin letters, dependencies are separated by
spaces or commas, text after ``#`` is a comment and empty lines are
ignored. In the example below A depends on B and C, and B depends on A,
which makes a cycle::

    A: B C
    B: A
    C:
"""

import re

from depvis.dependencies import PackageInfo
from depvis.errors import (
    PackageNotFoundError,
    RepositoryError,
    RepositoryFormatError,
    ValidationError,
)
from depvis.validation import TEST_PACKAGE_NAME_PATTERN

COMMENT_MARK = "#"
NAME_SEPARATOR = ":"
DEPENDENCY_SEPARATORS = re.compile(r"[\s,]+")


class FileRepository:
    """Dependency graph read from a test repository file."""

    def __init__(self, path, packages):
        """Keep the file path and the mapping package -> dependencies."""
        self.path = path
        self.packages = packages

    def describe(self, name):
        """Return the dependencies of a package described in the file."""
        if name not in self.packages:
            raise PackageNotFoundError(
                f"package {name!r} is not described in {self.path}"
            )
        return PackageInfo(
            name=name, version="", dependencies=self.packages[name]
        )


def load_file_repository(path):
    """Read and check a test repository file."""
    try:
        with open(path, encoding="utf-8-sig") as stream:
            lines = stream.read().splitlines()
    except OSError as error:
        raise RepositoryError(
            f"cannot read test repository {path!r} ({error.strerror})"
        ) from None
    except UnicodeDecodeError:
        raise RepositoryError(
            f"test repository {path!r} is not UTF-8 text"
        ) from None
    packages, problems = parse_lines(lines)
    if problems:
        raise RepositoryFormatError(path, problems)
    return FileRepository(path, packages)


def parse_lines(lines):
    """Turn the lines of a file into packages and a list of problems."""
    packages = {}
    problems = []
    for number, line in enumerate(lines, start=1):
        text = line.partition(COMMENT_MARK)[0].strip()
        if not text:
            continue
        try:
            name, dependencies = parse_line(text)
        except ValidationError as error:
            problems.append(f"line {number}: {error}")
            continue
        if name in packages:
            problems.append(f"line {number}: package {name!r} is repeated")
            continue
        packages[name] = dependencies
    return packages, problems


def parse_line(text):
    """Split ``NAME: DEPENDENCIES`` into the name and a tuple of names."""
    name, separator, rest = text.partition(NAME_SEPARATOR)
    if not separator:
        raise ValidationError(f"expected 'NAME: DEPENDENCIES', got {text!r}")
    name = check_test_name(name.strip())
    parts = [part for part in DEPENDENCY_SEPARATORS.split(rest) if part]
    unique_parts = dict.fromkeys(check_test_name(part) for part in parts)
    return name, tuple(unique_parts)


def check_test_name(name):
    """Return ``name`` if it is made of capital Latin letters only."""
    if not TEST_PACKAGE_NAME_PATTERN.fullmatch(name):
        raise ValidationError(
            f"{name!r} is not a test package name (capital letters A-Z)"
        )
    return name
