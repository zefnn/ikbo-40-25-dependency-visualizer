"""Text report of the dependency graph for the terminal."""

import textwrap

from depvis.graph import find_cycles

OUTPUT_WIDTH = 79
ITEM_INDENT = "  "
WRAP_INDENT = "      "


def wrap(text, first_indent="", next_indent=ITEM_INDENT):
    """Wrap a line to the output width without splitting names."""
    return textwrap.fill(
        text,
        width=OUTPUT_WIDTH,
        initial_indent=first_indent,
        subsequent_indent=next_indent,
        break_long_words=False,
        break_on_hyphens=False,
    )


def node_title(graph, key):
    """Return a package name with its version and a 'not found' mark."""
    node = graph.nodes[key]
    title = node.label
    if node.version:
        title += f" {node.version}"
    if node.missing:
        title += " (not found)"
    return title


def names(graph, keys):
    """Return the shown names of the packages with the given keys."""
    return [graph.nodes[key].label for key in keys]


def format_node(graph, key):
    """Return one line of the graph: 'package -> dependency, ...'."""
    text = node_title(graph, key)
    targets = graph.nodes[key].dependencies
    if targets:
        text += " -> " + ", ".join(names(graph, targets))
    return wrap(text, ITEM_INDENT, WRAP_INDENT)


def format_cycle(graph, cycle):
    """Return a cycle as 'A -> B -> A'."""
    return wrap(" -> ".join(names(graph, cycle)), ITEM_INDENT, WRAP_INDENT)


def format_graph(graph, source_note=""):
    """Build the report: packages in BFS order, filtered ones, cycles."""
    title = node_title(graph, graph.root)
    lines = [f"Dependency graph of {title}{source_note}:"]
    lines.extend(format_node(graph, key) for key in graph.nodes)
    if graph.skipped:
        skipped = ", ".join(graph.skipped.values())
        lines.append(
            wrap(f"Skipped by filter {graph.filter_substring!r}: {skipped}")
        )
    cycles = find_cycles(graph)
    if cycles:
        lines.append("Cycles:")
        lines.extend(format_cycle(graph, cycle) for cycle in cycles)
    return "\n".join(lines)
