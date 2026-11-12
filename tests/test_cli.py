"""Unit tests for the command-line interface in depvis.cli."""

import runpy
import sys

import pytest

from depvis.cli import (
    DEFAULT_CONFIG_PATH,
    EXIT_CONFIG_ERROR,
    EXIT_SUCCESS,
    format_value,
    main,
    parse_arguments,
)

EXPECTED_OUTPUT = (
    "package_name=requests\n"
    "repository=https://pypi.org/pypi\n"
    "test_mode=false\n"
    "version=2.32.3\n"
    "output_image=graph.png\n"
    "ascii_tree=false\n"
    "filter_substring=\n"
)


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


@pytest.mark.parametrize(
    "value, text",
    [(True, "true"), (False, "false"), ("graph.png", "graph.png")],
)
def test_format_value(value, text):
    """Booleans are shown as true/false, strings as they are."""
    assert format_value(value) == text


def test_main_prints_every_parameter(make_config, capsys):
    """A valid config prints all parameters as key=value lines."""
    exit_code = main(["-c", make_config()])
    captured = capsys.readouterr()
    assert exit_code == EXIT_SUCCESS
    assert captured.out == EXPECTED_OUTPUT
    assert captured.err == ""


def test_main_reads_config_ini_by_default(make_config, capsys):
    """Without -c the file config.ini of the working directory is used."""
    make_config()
    assert main([]) == EXIT_SUCCESS
    assert capsys.readouterr().out == EXPECTED_OUTPUT


def test_main_reports_errors_to_stderr(make_config, capsys):
    """Every problem goes to stderr and the exit code signals failure."""
    path = make_config(version="2.x", ascii_tree="sometimes")
    exit_code = main(["-c", path])
    captured = capsys.readouterr()
    assert exit_code == EXIT_CONFIG_ERROR
    assert captured.out == ""
    assert captured.err == (
        f"error: cannot use config file {path!r}:\n"
        "  version: '2.x' is not a PEP 440 version (e.g. 2.32.3)\n"
        "  ascii_tree: 'sometimes' is not a boolean "
        "(use true/false, yes/no, on/off, 1/0)\n"
    )


def test_main_reports_missing_config(capsys):
    """A missing config file is an error, not a crash."""
    assert main(["-c", "absent.ini"]) == EXIT_CONFIG_ERROR
    assert capsys.readouterr().err == (
        "error: cannot use config file 'absent.ini':\n  file not found\n"
    )


def test_module_runs_as_a_program(make_config, monkeypatch, capsys):
    """``python -m depvis`` exits with the code returned by main()."""
    monkeypatch.setattr(sys, "argv", ["depvis", "-c", make_config()])
    with pytest.raises(SystemExit) as caught:
        runpy.run_module("depvis", run_name="__main__")
    assert caught.value.code == EXIT_SUCCESS
    assert capsys.readouterr().out == EXPECTED_OUTPUT
