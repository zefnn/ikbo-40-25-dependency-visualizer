"""Text of the dependency graph in the Mermaid diagram language.

Every package becomes a node with a short identifier (n0, n1, ...) and
a quoted label "name version"; every dependency becomes an arrow that
means "depends on". Packages missing from the repository are dashed.
"""

from depvis.report import node_title

DIAGRAM_HEADER = "flowchart TD"
INDENT = "    "
QUOTE_ENTITY = "#quot;"
MISSING_STYLE = "stroke-dasharray: 5 5"


def node_ids(graph):
    """Give every package a short Mermaid identifier: n0, n1, ..."""
    return {key: f"n{index}" for index, key in enumerate(graph.nodes)}


def mermaid_label(text):
    """Quote a node label, replacing double quotes with an entity."""
    return '"' + text.replace('"', QUOTE_ENTITY) + '"'


def dependency_edges(graph):
    """Return (package, dependency) key pairs of the graph.

    In a graph of reverse dependencies (Stage 4) an edge leads from a
    package to one that depends on it, so it is turned around: arrows
    in the picture always mean "depends on".
    """
    pairs = []
    for key, node in graph.nodes.items():
        for target in node.dependencies:
            pairs.append((target, key) if graph.reverse else (key, target))
    return pairs


def to_mermaid(graph):
    """Build the Mermaid flowchart text of the dependency graph."""
    ids = node_ids(graph)
    lines = [DIAGRAM_HEADER]
    for key in graph.nodes:
        label = mermaid_label(node_title(graph, key))
        lines.append(f"{INDENT}{ids[key]}[{label}]")
    for source, target in dependency_edges(graph):
        lines.append(f"{INDENT}{ids[source]} --> {ids[target]}")
    for key, node in graph.nodes.items():
        if node.missing:
            lines.append(f"{INDENT}style {ids[key]} {MISSING_STYLE}")
    return "\n".join(lines)
