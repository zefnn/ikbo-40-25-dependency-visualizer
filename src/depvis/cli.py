"""Command-line interface of the dependency graph visualizer."""

import argparse
import sys
import textwrap

from depvis.config import load_settings
from depvis.dependencies import get_direct_dependencies
from depvis.errors import ConfigError, RepositoryError

DEFAULT_CONFIG_PATH = "config.ini"
EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 1
EXIT_REPOSITORY_ERROR = 3
OUTPUT_WIDTH = 79
TEST_MODE_NOT_READY = "test mode (test_mode = true) is not implemented yet"


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


def describe_requirement(requirement):
    """Return a dependency as text: name, version specifier, marker."""
    text = requirement.name
    if requirement.specifier:
        text += f" {requirement.specifier}"
    if requirement.marker:
        text += f" ; {requirement.marker}"
    return text


def format_optional(requirements):
    """List the names of the skipped optional dependencies, wrapped."""
    names = {}
    for requirement in requirements:
        names.setdefault(requirement.key, requirement.name)
    return textwrap.fill(
        "Skipped optional dependencies (extras): " + ", ".join(names.values()),
        width=OUTPUT_WIDTH,
        subsequent_indent="  ",
        break_long_words=False,
        break_on_hyphens=False,
    )


def format_dependencies(name, version, dependencies):
    """Build the report with the direct dependencies of a release."""
    lines = [f"Direct dependencies of {name} {version}:"]
    lines.extend(
        f"  {describe_requirement(item)}" for item in dependencies.required
    )
    if not dependencies.required:
        lines.append("  (none)")
    if dependencies.optional:
        lines.append(format_optional(dependencies.optional))
    return "\n".join(lines)


def report_config_error(error):
    """Print every problem of the configuration file to stderr."""
    print(f"error: cannot use config file {error.path!r}:", file=sys.stderr)
    for message in error.messages:
        print(f"  {message}", file=sys.stderr)


def show_direct_dependencies(settings):
    """Print the direct dependencies of the configured package."""
    try:
        dependencies = get_direct_dependencies(
            settings.repository, settings.package_name, settings.version
        )
    except RepositoryError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_REPOSITORY_ERROR
    for problem in dependencies.invalid:
        print(f"warning: skipped dependency {problem}", file=sys.stderr)
    print(
        format_dependencies(
            settings.package_name, settings.version, dependencies
        )
    )
    return EXIT_SUCCESS


def main(argv=None):
    """Run the application and return the process exit code."""
    arguments = parse_arguments(argv)
    try:
        settings = load_settings(arguments.config)
    except ConfigError as error:
        report_config_error(error)
        return EXIT_CONFIG_ERROR
    if settings.test_mode:
        print(f"error: {TEST_MODE_NOT_READY}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    return show_direct_dependencies(settings)
