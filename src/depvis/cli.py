"""Command-line interface of the dependency graph visualizer."""

import argparse
import sys

from depvis.config import load_settings
from depvis.errors import ConfigError

DEFAULT_CONFIG_PATH = "config.ini"
EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 1


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


def format_value(value):
    """Show booleans as true/false and any other value as text."""
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def format_settings(settings):
    """Return every parameter as a ``key=value`` line."""
    return "\n".join(
        f"{name}={format_value(value)}" for name, value in settings.items()
    )


def report_error(error):
    """Print every problem of the configuration file to stderr."""
    print(f"error: cannot use config file {error.path!r}:", file=sys.stderr)
    for message in error.messages:
        print(f"  {message}", file=sys.stderr)


def main(argv=None):
    """Run the application and return the process exit code."""
    arguments = parse_arguments(argv)
    try:
        settings = load_settings(arguments.config)
    except ConfigError as error:
        report_error(error)
        return EXIT_CONFIG_ERROR
    print(format_settings(settings))
    return EXIT_SUCCESS
