"""Unit tests for the command-line interface in depvis.cli."""

import runpy
import sys

import pytest

from depvis.cli import (
    DEFAULT_CONFIG_PATH,
    EXIT_CONFIG_ERROR,
    EXIT_REPOSITORY_ERROR,
    EXIT_SUCCESS,
    main,
    parse_arguments,
)

REQUESTS_GRAPH = (
    "Dependency graph of requests 2.32.3:\n"
    "  requests 2.32.3 -> charset-normalizer, idna, urllib3, certifi\n"
    "  charset-normalizer 3.4.0\n"
    "  idna 3.10\n"
    "  urllib3 2.2.3\n"
    "  certifi 2024.8.30\n"
)
CYCLE_REPOSITORY = "A: B X\nB: C\nC: A D\nD:\nX: D\n"


def run(argv, capsys):
    """Run main() and return its exit code, stdout and stderr."""
    exit_code = main(argv)
    captured = capsys.readouterr()
    return exit_code, captured.out, captured.err


def make_test_mode_config(make_config, tmp_path, text, **changes):
    """Write a test repository and a config that uses it.

    Returns the config path and the test repository path.
    """
    repository = tmp_path / "repo.txt"
    repository.write_text(text, encoding="utf-8")
    values = {
        "package_name": "A",
        "test_mode": "true",
        "repository": str(repository),
    }
    values.update(changes)
    return make_config(**values), str(repository)


def test_config_path_defaults_to_config_ini():
    """Without arguments the application reads config.ini."""
    assert parse_arguments([]).config == DEFAULT_CONFIG_PATH


@pytest.mark.parametrize("flag", ["-c", "--config"])
def test_config_path_can_be_given(flag):
    """The config file path is given with -c or --config."""
    assert parse_arguments([flag, "other.ini"]).config == "other.ini"


def test_unknown_argument_stops_the_program(capsys):
    """Arguments other than the config path are rejected by argparse."""
    with pytest.raises(SystemExit):
        parse_arguments(["--depth", "3"])
    assert "unrecognized arguments" in capsys.readouterr().err


def test_main_prints_the_dependency_graph(
    fake_repository, make_config, capsys
):
    """The graph of the configured package goes to stdout."""
    assert run(["-c", make_config()], capsys) == (
        EXIT_SUCCESS,
        REQUESTS_GRAPH,
        "",
    )
    assert fake_repository.requests


def test_main_reads_config_ini_by_default(
    fake_repository, make_config, capsys
):
    """Without -c the file config.ini of the working directory is used."""
    make_config()
    assert run([], capsys) == (EXIT_SUCCESS, REQUESTS_GRAPH, "")
    assert fake_repository.requests


def test_main_shows_filter_and_cycles_in_test_mode(
    make_config, tmp_path, capsys
):
    """Test mode reads the file; filtered packages and cycles are shown."""
    config, repository = make_test_mode_config(
        make_config, tmp_path, CYCLE_REPOSITORY, filter_substring="x"
    )
    assert run(["-c", config], capsys) == (
        EXIT_SUCCESS,
        f"Dependency graph of A (test repository {repository}):\n"
        "  A -> B\n"
        "  B -> C\n"
        "  C -> A, D\n"
        "  D\n"
        "Skipped by filter 'x': X\n"
        "Cycles:\n"
        "  A -> B -> C -> A\n",
        "",
    )


def test_main_warns_about_missing_test_packages(
    make_config, tmp_path, capsys
):
    """A dependency missing from the file is marked and reported."""
    config, repository = make_test_mode_config(
        make_config, tmp_path, "A: B C\nB:\n"
    )
    assert run(["-c", config], capsys) == (
        EXIT_SUCCESS,
        f"Dependency graph of A (test repository {repository}):\n"
        "  A -> B, C\n"
        "  B\n"
        "  C (not found)\n",
        f"warning: package 'C' is not described in {repository}\n",
    )


def test_main_reports_invalid_test_repository(
    make_config, tmp_path, capsys
):
    """Format errors of the test repository are listed by line."""
    config, repository = make_test_mode_config(
        make_config, tmp_path, "A B\n"
    )
    assert run(["-c", config], capsys) == (
        EXIT_REPOSITORY_ERROR,
        "",
        f"error: invalid test repository {repository!r}:\n"
        "  line 1: expected 'NAME: DEPENDENCIES', got 'A B'\n",
    )


def test_main_reports_missing_root_in_test_mode(
    make_config, tmp_path, capsys
):
    """The analysed package must be described in the test file."""
    config, repository = make_test_mode_config(
        make_config, tmp_path, "A:\n", package_name="Z"
    )
    assert run(["-c", config], capsys) == (
        EXIT_REPOSITORY_ERROR,
        "",
        f"error: package 'Z' is not described in {repository}\n",
    )


def test_main_reports_repository_errors(fake_repository, make_config, capsys):
    """Repository problems go to stderr with their own exit code."""
    assert run(["-c", make_config(version="9.9.9")], capsys) == (
        EXIT_REPOSITORY_ERROR,
        "",
        f"error: package 'requests' has no version '9.9.9' in "
        f"{fake_repository.url} (latest version: 2.32.3)\n",
    )


def test_main_warns_about_unparsable_dependencies(
    fake_repository, make_config, capsys
):
    """Broken dependency strings are skipped with a warning."""
    fake_repository.add_release("odd", "1.0", ["idna", "!!!"])
    path = make_config(package_name="odd", version="1.0")
    assert run(["-c", path], capsys) == (
        EXIT_SUCCESS,
        "Dependency graph of odd 1.0:\n"
        "  odd 1.0 -> idna\n"
        "  idna 3.10\n",
        "warning: odd 1.0: skipped dependency '!!!': "
        "not a PEP 508 dependency string\n",
    )


def test_main_reports_config_errors_to_stderr(make_config, capsys):
    """Every config problem goes to stderr before any download."""
    path = make_config(version="2.x", ascii_tree="sometimes")
    assert run(["-c", path], capsys) == (
        EXIT_CONFIG_ERROR,
        "",
        f"error: cannot use config file {path!r}:\n"
        "  version: '2.x' is not a PEP 440 version (e.g. 2.32.3)\n"
        "  ascii_tree: 'sometimes' is not a boolean "
        "(use true/false, yes/no, on/off, 1/0)\n",
    )


def test_main_reports_missing_config(capsys):
    """A missing config file is an error, not a crash."""
    assert run(["-c", "absent.ini"], capsys) == (
        EXIT_CONFIG_ERROR,
        "",
        "error: cannot use config file 'absent.ini':\n  file not found\n",
    )


def test_module_runs_as_a_program(
    fake_repository, make_config, monkeypatch, capsys
):
    """``python -m depvis`` exits with the code returned by main()."""
    monkeypatch.setattr(sys, "argv", ["depvis", "-c", make_config()])
    with pytest.raises(SystemExit) as caught:
        runpy.run_module("depvis", run_name="__main__")
    assert caught.value.code == EXIT_SUCCESS
    assert capsys.readouterr().out == REQUESTS_GRAPH
    assert fake_repository.requests
