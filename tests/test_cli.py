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

REQUESTS_OUTPUT = (
    "Direct dependencies of requests 2.32.3:\n"
    "  charset-normalizer <4,>=2\n"
    "  idna <4,>=2.5\n"
    "  urllib3 <3,>=1.21.1\n"
    "  certifi >=2017.4.17\n"
    "Skipped optional dependencies (extras): PySocks, chardet\n"
)
PYTEST_REQUIRES_DIST = [
    "iniconfig",
    "packaging",
    "pluggy<2,>=1.5",
    'exceptiongroup>=1.0.0rc8; python_version < "3.11"',
    'tomli>=1; python_version < "3.11"',
    'colorama; sys_platform == "win32"',
    'argcomplete; extra == "dev"',
    'attrs>=19.2; extra == "dev"',
    'hypothesis>=3.56; extra == "dev"',
    'mock; extra == "dev"',
    'pygments>=2.7.2; extra == "dev"',
    'requests; extra == "dev"',
    'setuptools; extra == "dev"',
    'xmlschema; extra == "dev"',
]
PYTEST_OUTPUT = (
    "Direct dependencies of pytest 8.3.3:\n"
    "  iniconfig\n"
    "  packaging\n"
    "  pluggy <2,>=1.5\n"
    '  exceptiongroup >=1.0.0rc8 ; python_version < "3.11"\n'
    '  tomli >=1 ; python_version < "3.11"\n'
    '  colorama ; sys_platform == "win32"\n'
    "Skipped optional dependencies (extras): argcomplete, attrs, "
    "hypothesis, mock,\n"
    "  pygments, requests, setuptools, xmlschema\n"
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


def test_main_prints_direct_dependencies(fake_repository, make_config, capsys):
    """The direct dependencies of the release go to stdout."""
    exit_code = main(["-c", make_config()])
    captured = capsys.readouterr()
    assert exit_code == EXIT_SUCCESS
    assert captured.out == REQUESTS_OUTPUT
    assert captured.err == ""
    assert fake_repository.requests


def test_main_reads_config_ini_by_default(
    fake_repository, make_config, capsys
):
    """Without -c the file config.ini of the working directory is used."""
    make_config()
    assert main([]) == EXIT_SUCCESS
    assert capsys.readouterr().out == REQUESTS_OUTPUT
    assert fake_repository.requests


def test_main_shows_markers_and_wraps_extras(
    fake_repository, make_config, capsys
):
    """Platform markers are shown, the list of extras is wrapped."""
    fake_repository.add_release("pytest", "8.3.3", PYTEST_REQUIRES_DIST)
    path = make_config(package_name="pytest", version="8.3.3")
    assert main(["-c", path]) == EXIT_SUCCESS
    assert capsys.readouterr().out == PYTEST_OUTPUT


def test_main_reports_release_without_dependencies(
    fake_repository, make_config, capsys
):
    """A release with no dependencies is reported as such."""
    fake_repository.add_release("certifi", "2024.8.30", None)
    path = make_config(package_name="certifi", version="2024.8.30")
    assert main(["-c", path]) == EXIT_SUCCESS
    assert capsys.readouterr().out == (
        "Direct dependencies of certifi 2024.8.30:\n  (none)\n"
    )


def test_main_warns_about_unparsable_dependencies(
    fake_repository, make_config, capsys
):
    """Broken dependency strings are skipped with a warning."""
    fake_repository.add_release("odd", "1.0", ["idna", "!!!"])
    path = make_config(package_name="odd", version="1.0")
    assert main(["-c", path]) == EXIT_SUCCESS
    captured = capsys.readouterr()
    assert captured.out == "Direct dependencies of odd 1.0:\n  idna\n"
    assert captured.err == (
        "warning: skipped dependency '!!!': "
        "not a PEP 508 dependency string\n"
    )


def test_main_reports_repository_errors(fake_repository, make_config, capsys):
    """Repository problems go to stderr with their own exit code."""
    path = make_config(version="9.9.9")
    assert main(["-c", path]) == EXIT_REPOSITORY_ERROR
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        f"error: package 'requests' has no version '9.9.9' in "
        f"{fake_repository.url} (latest version: 2.32.3)\n"
    )


def test_main_does_not_support_test_mode_yet(make_config, repo_file, capsys):
    """Test mode is reported as not implemented before any download."""
    path = make_config(
        package_name="A", test_mode="true", repository=repo_file
    )
    assert main(["-c", path]) == EXIT_CONFIG_ERROR
    assert capsys.readouterr().err == (
        "error: test mode (test_mode = true) is not implemented yet\n"
    )


def test_main_reports_config_errors_to_stderr(make_config, capsys):
    """Every config problem goes to stderr before any download."""
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


def test_module_runs_as_a_program(
    fake_repository, make_config, monkeypatch, capsys
):
    """``python -m depvis`` exits with the code returned by main()."""
    monkeypatch.setattr(sys, "argv", ["depvis", "-c", make_config()])
    with pytest.raises(SystemExit) as caught:
        runpy.run_module("depvis", run_name="__main__")
    assert caught.value.code == EXIT_SUCCESS
    assert capsys.readouterr().out == REQUESTS_OUTPUT
    assert fake_repository.requests
