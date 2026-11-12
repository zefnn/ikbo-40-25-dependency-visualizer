"""Building the dependency graph with a breadth-first search (BFS).

Packages are visited level by level from the analysed package with a
queue, without recursion. A package is described (downloaded or looked
up) only once, so shared dependencies and cycles cause neither repeated
work nor an endless loop. Packages whose names contain the filter
substring are left out together with the packages reachable only
through them.
"""

from collections import deque
from dataclasses import dataclass, field

from depvis.errors import PackageNotFoundError
from depvis.requirements import canonical_name, name_matches


@dataclass
class Node:
    """One package of the graph.

    ``dependencies`` holds the keys of its direct dependencies;
    ``missing`` is set when the source does not know the package.
    """

    label: str
    version: str = ""
    dependencies: list = field(default_factory=list)
    missing: bool = False


@dataclass
class DependencyGraph:
    """Packages reachable from the analysed package and their edges.

    Packages are identified by the PEP 503 form of their names (keys).
    ``nodes`` maps keys to nodes in the order the search reached them,
    ``skipped`` maps the keys of filtered packages to their names.
    """

    root: str
    filter_substring: str = ""
    nodes: dict = field(default_factory=dict)
    skipped: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)


def build_graph(root_name, source, filter_substring=""):
    """Collect every package reachable from ``root_name`` breadth-first.

    ``source`` describes packages: ``source.describe(name)`` returns a
    ``PackageInfo`` or raises ``PackageNotFoundError``.
    """
    root = canonical_name(root_name)
    graph = DependencyGraph(root=root, filter_substring=filter_substring)
    graph.nodes[root] = Node(root_name)
    queue = deque([root])
    while queue:
        key = queue.popleft()
        for name in describe_package(graph, source, key):
            if name_matches(name, filter_substring):
                graph.skipped.setdefault(canonical_name(name), name)
            elif add_edge(graph, key, name):
                queue.append(canonical_name(name))
    return graph


def describe_package(graph, source, key):
    """Ask the source about one package and return its dependencies.

    A missing dependency only adds a warning; a missing analysed
    package stops the search.
    """
    node = graph.nodes[key]
    try:
        info = source.describe(node.label)
    except PackageNotFoundError as error:
        if key == graph.root:
            raise
        node.missing = True
        graph.warnings.append(str(error))
        return ()
    node.label = info.name
    node.version = info.version
    graph.warnings.extend(info.problems)
    return info.dependencies


def add_edge(graph, source_key, name):
    """Add an edge to package ``name``; return True if it is new."""
    target = canonical_name(name)
    dependencies = graph.nodes[source_key].dependencies
    if target not in dependencies:
        dependencies.append(target)
    if target in graph.nodes:
        return False
    graph.nodes[target] = Node(name)
    return True


def find_cycles(graph):
    """Return the cycles of the graph as lists of keys, first == last.

    Every cycle has an edge that leads to a package reached no later
    than the edge's own source. Such an edge closes a cycle when its
    source can be reached from its target, which is checked with a
    breadth-first search as well. Each cycle is listed once.
    """
    position = {key: index for index, key in enumerate(graph.nodes)}
    cycles = {}
    for key, node in graph.nodes.items():
        for target in node.dependencies:
            if position[target] > position[key]:
                continue
            cycle = close_cycle(graph, target, key, position)
            if cycle:
                cycles.setdefault(tuple(cycle), cycle)
    return list(cycles.values())


def close_cycle(graph, start, end, position):
    """Return the cycle made by a path start..end and the edge end-start.

    The cycle begins with its package that was reached first; None is
    returned when ``end`` cannot be reached from ``start``.
    """
    path = find_path(graph, start, end)
    if path is None:
        return None
    first = path.index(min(path, key=position.__getitem__))
    ordered = path[first:] + path[:first]
    return ordered + ordered[:1]


def find_path(graph, start, goal):
    """Return the shortest list of keys from ``start`` to ``goal``."""
    parents = {start: None}
    queue = deque([start])
    while queue:
        key = queue.popleft()
        if key == goal:
            return rebuild_path(parents, goal)
        for target in graph.nodes[key].dependencies:
            if target not in parents:
                parents[target] = key
                queue.append(target)
    return None


def rebuild_path(parents, goal):
    """Follow the parent links back from ``goal`` and reverse them."""
    path = []
    key = goal
    while key is not None:
        path.append(key)
        key = parents[key]
    path.reverse()
    return path
