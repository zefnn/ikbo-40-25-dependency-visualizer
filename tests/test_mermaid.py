"""Unit tests for the Mermaid text of the graph in depvis.mermaid."""

from depvis.file_repository import FileRepository, ReverseFileRepository
from depvis.graph import DependencyGraph, Node, build_graph
from depvis.mermaid import mermaid_label, node_ids, to_mermaid


def make_graph(packages, root="A", reverse=False):
    """Build the graph (or the reverse graph) of ``root``."""
    source = FileRepository("repo.txt", packages)
    if reverse:
        source = ReverseFileRepository(source)
    return build_graph(root, source, reverse=reverse)


def test_nodes_get_short_identifiers_in_bfs_order():
    """Identifiers n0, n1, ... follow the order of the search."""
    graph = make_graph({"A": ("B", "C"), "B": (), "C": ()})
    assert node_ids(graph) == {"a": "n0", "b": "n1", "c": "n2"}


def test_dependency_graph_becomes_a_flowchart():
    """Every package is a node and every dependency an arrow."""
    graph = make_graph({"A": ("B", "C"), "B": ("C",), "C": ()})
    assert to_mermaid(graph) == (
        "flowchart TD\n"
        '    n0["A"]\n'
        '    n1["B"]\n'
        '    n2["C"]\n'
        "    n0 --> n1\n"
        "    n0 --> n2\n"
        "    n1 --> n2"
    )


def test_cycles_and_self_loops_are_drawn():
    """Edges that close cycles stay in the diagram."""
    graph = make_graph({"A": ("A", "B"), "B": ("A",)})
    edges = [line for line in to_mermaid(graph).splitlines() if "-->" in line]
    assert edges == ["    n0 --> n0", "    n0 --> n1", "    n1 --> n0"]


def test_missing_packages_are_dashed():
    """A package the repository does not know gets a dashed frame."""
    text = to_mermaid(make_graph({"A": ("B",)}))
    assert '    n1["B (not found)"]' in text.splitlines()
    assert text.endswith("    style n1 stroke-dasharray: 5 5")


def test_reverse_edges_are_turned_around():
    """Arrows of a reverse graph still mean 'depends on'."""
    graph = make_graph(
        {"A": ("B",), "B": ("C",), "C": ()}, root="C", reverse=True
    )
    assert to_mermaid(graph) == (
        "flowchart TD\n"
        '    n0["C"]\n'
        '    n1["B"]\n'
        '    n2["A"]\n'
        "    n1 --> n0\n"
        "    n2 --> n1"
    )


def test_labels_show_versions_and_escape_quotes():
    """Labels are quoted; quotes inside them become #quot;."""
    graph = DependencyGraph(root="x")
    graph.nodes["x"] = Node('say "hi"', version="1.0")
    assert to_mermaid(graph) == (
        'flowchart TD\n    n0["say #quot;hi#quot; 1.0"]'
    )
    assert mermaid_label('a"b') == '"a#quot;b"'
