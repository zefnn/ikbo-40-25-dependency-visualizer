"""Unit tests for the breadth-first graph search in depvis.graph."""

import pytest

from depvis.dependencies import RepositorySource
from depvis.errors import PackageNotFoundError
from depvis.file_repository import (
    FileRepository,
    ReverseFileRepository,
    parse_lines,
)
from depvis.graph import build_graph, find_cycles


class CountingRepository(FileRepository):
    """A test repository that remembers which packages were described."""

    def __init__(self, text):
        """Parse the lines of ``text`` as a test repository file."""
        packages, problems = parse_lines(text.splitlines())
        assert not problems
        super().__init__("repo.txt", packages)
        self.described = []

    def describe(self, name):
        """Record the request and describe the package."""
        self.described.append(name)
        return super().describe(name)


def labels(graph, keys):
    """Return the names shown for the given keys."""
    return [graph.nodes[key].label for key in keys]


def edges(graph, key):
    """Return the names of the direct dependencies of a package."""
    return labels(graph, graph.nodes[key].dependencies)


def cycle_names(graph):
    """Return the cycles of the graph as lists of names."""
    return [labels(graph, cycle) for cycle in find_cycles(graph)]


def test_packages_are_visited_level_by_level():
    """BFS reaches B and C (level 1) before D and E (level 2)."""
    source = CountingRepository("A: B C\nB: D\nC: E\nD:\nE:\n")
    graph = build_graph("A", source)
    assert labels(graph, graph.nodes) == ["A", "B", "C", "D", "E"]
    assert source.described == ["A", "B", "C", "D", "E"]


def test_chain_is_followed_to_the_end():
    """Transitive dependencies are collected at any depth."""
    graph = build_graph("A", CountingRepository("A: B\nB: C\nC: D\nD:\n"))
    assert labels(graph, graph.nodes) == ["A", "B", "C", "D"]
    assert edges(graph, "c") == ["D"]


def test_shared_dependency_is_described_once():
    """In a diamond the common dependency is visited only once."""
    source = CountingRepository("A: B C\nB: D\nC: D\nD:\n")
    graph = build_graph("A", source)
    assert source.described == ["A", "B", "C", "D"]
    assert edges(graph, "b") == ["D"]
    assert edges(graph, "c") == ["D"]
    assert not find_cycles(graph)


def test_cycle_does_not_loop_forever():
    """A cycle is walked once and reported from its first package."""
    source = CountingRepository("A: B\nB: C\nC: A D\nD:\n")
    graph = build_graph("A", source)
    assert source.described == ["A", "B", "C", "D"]
    assert edges(graph, "c") == ["A", "D"]
    assert cycle_names(graph) == [["A", "B", "C", "A"]]


def test_self_dependency_is_a_cycle():
    """A package that depends on itself forms a cycle of one."""
    graph = build_graph("A", CountingRepository("A: A B\nB:\n"))
    assert cycle_names(graph) == [["A", "A"]]


def test_several_cycles_are_listed_once_each():
    """Two cycles of two packages and a self-loop are all found."""
    text = "A: B C\nB: A\nC: D\nD: C E\nE: E\n"
    graph = build_graph("A", CountingRepository(text))
    assert cycle_names(graph) == [
        ["A", "B", "A"],
        ["C", "D", "C"],
        ["E", "E"],
    ]


def test_edge_back_without_a_way_back_is_not_a_cycle():
    """An edge to an earlier package is not a cycle by itself."""
    graph = build_graph("A", CountingRepository("A: B C\nC: B\nB:\n"))
    assert not find_cycles(graph)


def test_filtered_packages_are_skipped_with_their_dependencies():
    """Filtered packages and what only they need are left out."""
    text = (
        "A: B TEST C\nB: TESTLIB D\nC: D\n"
        "TEST: E\nTESTLIB: F\nD:\nE:\nF:\n"
    )
    source = CountingRepository(text)
    graph = build_graph("A", source, "test")
    assert labels(graph, graph.nodes) == ["A", "B", "C", "D"]
    assert list(graph.skipped.values()) == ["TEST", "TESTLIB"]
    assert source.described == ["A", "B", "C", "D"]
    assert edges(graph, "a") == ["B", "C"]


def test_filter_ignores_case_and_separators():
    """The filter compares names in their PEP 503 form."""
    source = FileRepository(
        "repo.txt",
        {"root": ("Zope.Interface", "six"), "six": ()},
    )
    graph = build_graph("root", source, "zope_INTER")
    assert labels(graph, graph.nodes) == ["root", "six"]
    assert list(graph.skipped.values()) == ["Zope.Interface"]


def test_missing_dependency_gives_a_warning():
    """A dependency the repository does not know stays without edges."""
    graph = build_graph("A", CountingRepository("A: B C\nB:\n"))
    assert labels(graph, graph.nodes) == ["A", "B", "C"]
    assert graph.nodes["c"].missing
    assert not graph.nodes["c"].dependencies
    assert not graph.nodes["b"].missing
    assert graph.warnings == ["package 'C' is not described in repo.txt"]


def test_missing_root_stops_the_search():
    """Without the analysed package there is no graph at all."""
    with pytest.raises(PackageNotFoundError):
        build_graph("Z", CountingRepository("A:\n"))


def test_repository_graph_uses_names_from_the_repository(fake_repository):
    """Differently spelled names of one package give one node."""
    fake_repository.add_release("Root", "1.0", ["Werkzeug", "Jinja2"])
    fake_repository.add_release("Werkzeug", "3.1.3", ["markupsafe>=2.1"])
    fake_repository.add_release("Jinja2", "3.1.4", ["MarkupSafe>=2.0"])
    fake_repository.add_release("MarkupSafe", "3.0.2", None)
    source = RepositorySource(fake_repository.url, "root", "1.0")
    graph = build_graph("root", source)
    assert labels(graph, graph.nodes) == [
        "Root",
        "Werkzeug",
        "Jinja2",
        "MarkupSafe",
    ]
    assert [node.version for node in graph.nodes.values()] == [
        "1.0",
        "3.1.3",
        "3.1.4",
        "3.0.2",
    ]
    assert edges(graph, "werkzeug") == ["MarkupSafe"]
    assert edges(graph, "jinja2") == ["MarkupSafe"]


def build_reverse(root, text, filter_substring=""):
    """Build the reverse dependency graph of ``root`` from file text."""
    source = ReverseFileRepository(CountingRepository(text))
    return build_graph(root, source, filter_substring, reverse=True)


def test_reverse_dependencies_are_found_breadth_first():
    """Direct dependents come first, then the packages that need them."""
    graph = build_reverse("D", "A: B C\nB: D\nC: D\nD:\n")
    assert graph.reverse
    assert labels(graph, graph.nodes) == ["D", "B", "C", "A"]
    assert edges(graph, "d") == ["B", "C"]
    assert edges(graph, "b") == ["A"]
    assert not edges(graph, "a")


def test_reverse_chain_is_followed_to_the_top():
    """Indirect dependents at any depth are collected."""
    graph = build_reverse("D", "A: B\nB: C\nC: D\nD:\n")
    assert labels(graph, graph.nodes) == ["D", "C", "B", "A"]


def test_package_without_dependents_stays_alone():
    """Nothing depends on the top package of a graph."""
    graph = build_reverse("A", "A: B C\nB: D\nC: D\nD:\n")
    assert labels(graph, graph.nodes) == ["A"]


def test_reverse_search_handles_cycles():
    """A cycle is walked once and reported in the reversed direction."""
    graph = build_reverse("D", "A: B\nB: C\nC: A D\nD:\n")
    assert labels(graph, graph.nodes) == ["D", "C", "B", "A"]
    assert cycle_names(graph) == [["C", "B", "A", "C"]]


def test_reverse_search_uses_the_filter():
    """A filtered dependent is skipped, others are still reached."""
    graph = build_reverse("D", "A: B C\nB: D\nC: D\nD:\n", "b")
    assert labels(graph, graph.nodes) == ["D", "C", "A"]
    assert list(graph.skipped.values()) == ["B"]


def test_reverse_search_of_unknown_package_fails():
    """A package the file never mentions has no reverse dependencies."""
    with pytest.raises(PackageNotFoundError):
        build_reverse("Z", "A: B\nB:\n")
