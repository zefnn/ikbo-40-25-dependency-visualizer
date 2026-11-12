"""Unit tests for the test repository file in depvis.file_repository."""

import pytest

from depvis.dependencies import PackageInfo
from depvis.errors import (
    PackageNotFoundError,
    RepositoryError,
    RepositoryFormatError,
)
from depvis.file_repository import load_file_repository, parse_lines

VALID_TEXT = "\n".join(
    [
        "# A test repository",
        "A: B C   # A depends on B and C",
        "",
        "B: D, C",
        "C:",
        "D: D B B",
    ]
)
UTF8_BOM = "\ufeff"


def write_repository(tmp_path, text):
    """Write ``text`` to a test repository file and return its path."""
    path = tmp_path / "repo.txt"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_lines_are_parsed_into_packages():
    """Comments, empty lines, commas and repeated names are handled."""
    packages, problems = parse_lines(VALID_TEXT.splitlines())
    assert packages == {
        "A": ("B", "C"),
        "B": ("D", "C"),
        "C": (),
        "D": ("D", "B"),
    }
    assert not problems


def test_format_problems_are_listed_with_line_numbers():
    """Every broken line is reported with its number."""
    lines = ["A B", "a: B", "B: c", "A: C", "C:", "C: A"]
    packages, problems = parse_lines(lines)
    assert packages == {"A": ("C",), "C": ()}
    assert problems == [
        "line 1: expected 'NAME: DEPENDENCIES', got 'A B'",
        "line 2: 'a' is not a test package name (capital letters A-Z)",
        "line 3: 'c' is not a test package name (capital letters A-Z)",
        "line 6: package 'C' is repeated",
    ]


def test_described_package_is_returned(tmp_path):
    """A package from the file is described by its dependencies."""
    repository = load_file_repository(write_repository(tmp_path, VALID_TEXT))
    assert repository.describe("A") == PackageInfo("A", "", ("B", "C"))


def test_package_without_description_is_not_found(tmp_path):
    """Asking for a package missing from the file raises an error."""
    path = write_repository(tmp_path, VALID_TEXT)
    repository = load_file_repository(path)
    with pytest.raises(PackageNotFoundError) as caught:
        repository.describe("Z")
    assert str(caught.value) == f"package 'Z' is not described in {path}"


def test_utf8_bom_is_accepted(tmp_path):
    """A byte order mark at the start of the file is ignored."""
    path = write_repository(tmp_path, UTF8_BOM + "A: B\nB:\n")
    assert load_file_repository(path).describe("A").dependencies == ("B",)


def test_broken_file_is_reported_with_all_problems(tmp_path):
    """Format problems are collected into RepositoryFormatError."""
    path = write_repository(tmp_path, "A B\nB: c\n")
    with pytest.raises(RepositoryFormatError) as caught:
        load_file_repository(path)
    assert caught.value.path == path
    assert caught.value.messages == [
        "line 1: expected 'NAME: DEPENDENCIES', got 'A B'",
        "line 2: 'c' is not a test package name (capital letters A-Z)",
    ]


def test_missing_file_is_reported(tmp_path):
    """A file removed after the config check is still reported."""
    path = str(tmp_path / "missing.txt")
    with pytest.raises(RepositoryError, match="cannot read test repository"):
        load_file_repository(path)


def test_file_that_is_not_utf8_is_reported(tmp_path):
    """A file in another encoding is reported."""
    path = tmp_path / "repo.txt"
    path.write_bytes(b"A: B\n\xff\n")
    with pytest.raises(RepositoryError, match="is not UTF-8 text"):
        load_file_repository(str(path))
