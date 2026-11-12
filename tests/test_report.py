"""Unit tests for the text report in depvis.report."""

from depvis.file_repository import FileRepository
from depvis.graph import build_graph
from depvis.report import (
    OUTPUT_WIDTH,
    WRAP_INDENT,
    format_graph,
    format_node,
    node_title,
)


def make_graph(packages, filter_substring=""):
    """Build a graph of package A from a mapping of dependencies."""
    source = FileRepository("repo.txt", packages)
    return build_graph("A", source, filter_substring)


def test_title_shows_version_and_missing_mark():
    """Versions are added to names, unknown packages are marked."""
    graph = make_graph({"A": ("B",)})
    graph.nodes["a"].version = "1.0"
    assert node_title(graph, "a") == "A 1.0"
    assert node_title(graph, "b") == "B (not found)"


def test_long_dependency_lists_are_wrapped():
    """A line longer than the output width continues indented."""
    names = tuple(f"PACKAGE{letter}" for letter in "BCDEFGHIJK")
    graph = make_graph({"A": names})
    lines = format_node(graph, "a").split("\n")
    assert all(len(line) <= OUTPUT_WIDTH for line in lines)
    assert lines[1:]
    assert all(line.startswith(WRAP_INDENT) for line in lines[1:])
    assert " ".join(line.strip() for line in lines) == (
        "A -> " + ", ".join(names)
    )


def test_report_lists_packages_filter_and_cycles():
    """The report shows the BFS order, skipped packages and cycles."""
    graph = make_graph(
        {"A": ("B", "C", "X"), "B": ("A",), "C": (), "X": ()}, "x"
    )
    assert format_graph(graph, " (test repository repo.txt)") == (
        "Dependency graph of A (test repository repo.txt):\n"
        "  A -> B, C\n"
        "  B -> A\n"
        "  C\n"
        "Skipped by filter 'x': X\n"
        "Cycles:\n"
        "  A -> B -> A"
    )
