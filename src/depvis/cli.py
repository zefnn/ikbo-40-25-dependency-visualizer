"""Command-line interface of the dependency graph visualizer."""

import argparse
import sys

from depvis.config import load_settings
from depvis.dependencies import RepositorySource
from depvis.errors import ConfigError, RepositoryError, RepositoryFormatError
from depvis.file_repository import load_file_repository
from depvis.graph import build_graph
from depvis.report import format_graph

DEFAULT_CONFIG_PATH = "config.ini"
EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 1
EXIT_REPOSITORY_ERROR = 3


def parse_arguments(argv=None):
    """Parse the command line; only the config file path is accepted."""
    parser = argparse.ArgumentParser(
        prog="depvis",
        description=(
            "Dependency graph visualizer for pip packages. "
            "All parameters are read from an INI configuration file."
        ),
    )
    parser.add_argument(
        "-c",
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help="path to the INI configuration file (default: %(default)s)",
    )
    return parser.parse_args(argv)


def report_problems(title, messages):
    """Print an error title and its list of problems to stderr."""
    print(f"error: {title}:", file=sys.stderr)
    for message in messages:
        print(f"  {message}", file=sys.stderr)


def open_source(settings):
    """Return where packages are described: test file or repository."""
    if settings.test_mode:
        return load_file_repository(settings.repository)
    return RepositorySource(
        settings.repository, settings.package_name, settings.version
    )


def collect_graph(settings):
    """Build the dependency graph; on failure report it, return None."""
    try:
        return build_graph(
            settings.package_name,
            open_source(settings),
            settings.filter_substring,
        )
    except RepositoryFormatError as error:
        title = f"invalid test repository {error.path!r}"
        report_problems(title, error.messages)
    except RepositoryError as error:
        print(f"error: {error}", file=sys.stderr)
    return None


def source_note(settings):
    """Name the test repository file in the report title."""
    if settings.test_mode:
        return f" (test repository {settings.repository})"
    return ""


def main(argv=None):
    """Run the application and return the process exit code."""
    arguments = parse_arguments(argv)
    try:
        settings = load_settings(arguments.config)
    except ConfigError as error:
        title = f"cannot use config file {error.path!r}"
        report_problems(title, error.messages)
        return EXIT_CONFIG_ERROR
    graph = collect_graph(settings)
    if graph is None:
        return EXIT_REPOSITORY_ERROR
    for warning in graph.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(format_graph(graph, source_note(settings)))
    return EXIT_SUCCESS
