"""Dependencies drawn as an ASCII tree.

Only ASCII characters are used: "+-- " marks a branch, a backslash
with two dashes marks the last branch, and "|   " continues a branch
that goes on below.
"""

from depvis.report import node_title

BRANCH = "+-- "
LAST_BRANCH = "\\-- "
PIPE = "|   "
SPACE = "    "
REPEAT_MARK = " (*)"
CYCLE_MARK = " (cycle)"
REPEAT_NOTE = "(*) its dependencies are already shown above"


def ascii_tree(graph):
    """Draw the graph as an ASCII tree that starts at the root package.

    The tree is drawn depth-first with an explicit stack, without
    recursion. A package whose dependencies are already drawn gets
    "(*)" instead of a second copy of its subtree, and a package that
    is already on the current branch gets "(cycle)", so cycles end.
    """
    lines = [node_title(graph, graph.root)]
    drawn = {graph.root}
    stack = child_entries(graph, graph.root, "", (graph.root,))
    while stack:
        key, prefix, is_last, ancestors = stack.pop()
        mark = repeat_mark(graph, key, ancestors, drawn)
        connector = LAST_BRANCH if is_last else BRANCH
        lines.append(prefix + connector + node_title(graph, key) + mark)
        if not mark:
            drawn.add(key)
            inner = prefix + (SPACE if is_last else PIPE)
            stack.extend(child_entries(graph, key, inner, ancestors + (key,)))
    if any(line.endswith(REPEAT_MARK) for line in lines):
        lines.append(REPEAT_NOTE)
    return "\n".join(lines)


def child_entries(graph, key, prefix, ancestors):
    """Return stack entries for the dependencies of ``key``.

    The entries are reversed, so the first dependency is popped first.
    """
    targets = graph.nodes[key].dependencies
    last = targets[-1] if targets else None
    entries = [
        (target, prefix, target == last, ancestors) for target in targets
    ]
    entries.reverse()
    return entries


def repeat_mark(graph, key, ancestors, drawn):
    """Mark a package that closes a cycle or whose subtree is drawn."""
    if key in ancestors:
        return CYCLE_MARK
    if key in drawn and graph.nodes[key].dependencies:
        return REPEAT_MARK
    return ""
