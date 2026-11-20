"""Unit tests for the ASCII tree in depvis.tree."""

from depvis.file_repository import FileRepository, ReverseFileRepository
from depvis.graph import build_graph
from depvis.tree import ascii_tree


def tree_of(packages, root="A", reverse=False):
    """Draw the ASCII tree of ``root`` for a mapping of dependencies."""
    source = FileRepository("repo.txt", packages)
    if reverse:
        source = ReverseFileRepository(source)
    return ascii_tree(build_graph(root, source, reverse=reverse))


def test_flat_dependencies():
    """Direct dependencies hang from the root, the last with a corner."""
    assert tree_of({"A": ("B", "C"), "B": (), "C": ()}) == (
        "A\n"
        "+-- B\n"
        "\\-- C"
    )


def test_nested_dependencies_keep_the_branch_lines():
    """A branch that goes on below is drawn with '|'."""
    packages = {
        "A": ("B", "C"),
        "B": ("D", "E"),
        "C": ("F",),
        "D": (),
        "E": (),
        "F": (),
    }
    assert tree_of(packages) == (
        "A\n"
        "+-- B\n"
        "|   +-- D\n"
        "|   \\-- E\n"
        "\\-- C\n"
        "    \\-- F"
    )


def test_repeated_subtree_is_marked():
    """A package with dependencies is expanded only the first time."""
    packages = {
        "A": ("B", "C"),
        "B": ("D",),
        "C": ("D",),
        "D": ("E",),
        "E": (),
    }
    assert tree_of(packages) == (
        "A\n"
        "+-- B\n"
        "|   \\-- D\n"
        "|       \\-- E\n"
        "\\-- C\n"
        "    \\-- D (*)\n"
        "(*) its dependencies are already shown above"
    )


def test_repeated_leaf_needs_no_mark():
    """A package without dependencies is simply shown again."""
    packages = {"A": ("B", "C"), "B": ("D",), "C": ("D",), "D": ()}
    assert tree_of(packages) == (
        "A\n"
        "+-- B\n"
        "|   \\-- D\n"
        "\\-- C\n"
        "    \\-- D"
    )


def test_cycle_is_cut():
    """Going back to a package on the branch ends with '(cycle)'."""
    assert tree_of({"A": ("B",), "B": ("C",), "C": ("A",)}) == (
        "A\n"
        "\\-- B\n"
        "    \\-- C\n"
        "        \\-- A (cycle)"
    )


def test_missing_package_is_marked():
    """A package the repository does not know is shown as not found."""
    assert tree_of({"A": ("B",)}) == "A\n\\-- B (not found)"


def test_tree_of_reverse_dependencies():
    """In reverse mode the tree shows who needs the package."""
    packages = {"A": ("B", "C"), "B": ("D",), "C": ("D",), "D": ()}
    assert tree_of(packages, root="D", reverse=True) == (
        "D\n"
        "+-- B\n"
        "|   \\-- A\n"
        "\\-- C\n"
        "    \\-- A"
    )
