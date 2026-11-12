"""Reading the INI configuration file into validated settings.

The file must contain exactly one section, ``[settings]``, holding
every parameter listed in ``PARAMETER_NAMES``. Any problem is reported
through ``ConfigError``, which lists all of them at once.
"""

import configparser
from dataclasses import dataclass, fields

from depvis.errors import ConfigError, ValidationError
from depvis.validation import (
    check_filter,
    check_output_image,
    check_package_name,
    check_repository,
    check_version,
    parse_flag,
)

SECTION = "settings"


@dataclass(frozen=True)
class Settings:
    """User parameters from the configuration file, already validated."""

    package_name: str
    repository: str
    test_mode: bool
    version: str
    output_image: str
    ascii_tree: bool
    filter_substring: str

    def items(self):
        """Return ``(name, value)`` pairs in the order of the fields."""
        return [
            (item.name, getattr(self, item.name)) for item in fields(self)
        ]


PARAMETER_NAMES = tuple(item.name for item in fields(Settings))
MODE_FREE_CHECKS = (
    ("version", check_version),
    ("output_image", check_output_image),
    ("ascii_tree", parse_flag),
    ("filter_substring", check_filter),
)
MODE_DEPENDENT_CHECKS = (
    ("package_name", check_package_name),
    ("repository", check_repository),
)


def load_settings(path):
    """Read the INI file at ``path`` and return validated ``Settings``."""
    parser = read_config_file(path)
    check_layout(parser, path)
    return build_settings(dict(parser[SECTION]), path)


def read_config_file(path):
    """Parse the INI file at ``path``; only ``=`` separates the value."""
    parser = configparser.ConfigParser(interpolation=None, delimiters=("=",))
    try:
        with open(path, encoding="utf-8-sig") as stream:
            parser.read_file(stream)
    except FileNotFoundError:
        raise ConfigError(path, ["file not found"]) from None
    except IsADirectoryError:
        raise ConfigError(path, ["this is a directory, not a file"]) from None
    except OSError as error:
        message = f"cannot read the file ({error.strerror})"
        raise ConfigError(path, [message]) from None
    except UnicodeDecodeError:
        raise ConfigError(path, ["the file is not UTF-8 text"]) from None
    except configparser.Error as error:
        raise ConfigError(path, describe_syntax_error(error)) from None
    return parser


def describe_syntax_error(error):
    """Turn a configparser exception into messages naming the lines."""
    if isinstance(error, configparser.MissingSectionHeaderError):
        return [f"line {error.lineno}: parameter outside of any section"]
    if isinstance(error, configparser.ParsingError):
        return [
            f"line {entry[0]}: expected 'key = value'"
            for entry in error.errors
        ]
    if isinstance(error, configparser.DuplicateSectionError):
        return [
            f"line {error.lineno}: section [{error.section}] is repeated"
        ]
    if isinstance(error, configparser.DuplicateOptionError):
        return [
            f"line {error.lineno}: parameter {error.option!r} is repeated"
        ]
    return [error.message]


def check_layout(parser, path):
    """Require the [settings] section with exactly the known parameters."""
    problems = [
        f"unknown section [{name}]"
        for name in parser.sections()
        if name != SECTION
    ]
    if parser.has_section(SECTION):
        problems.extend(find_name_problems(list(parser[SECTION])))
    else:
        problems.append(f"section [{SECTION}] is missing")
    if problems:
        raise ConfigError(path, problems)


def find_name_problems(names):
    """List the unknown parameters and the parameters that are missing."""
    unknown = [
        f"unknown parameter {name!r}"
        for name in names
        if name not in PARAMETER_NAMES
    ]
    missing = [
        f"missing parameter {name!r}"
        for name in PARAMETER_NAMES
        if name not in names
    ]
    return unknown + missing


def build_settings(raw_values, path):
    """Validate raw strings and report every invalid parameter at once.

    ``package_name`` and ``repository`` follow different rules in test
    mode, so they are checked only when ``test_mode`` itself is valid.
    """
    problems = {}
    test_mode = run_check(
        problems, "test_mode", parse_flag, raw_values["test_mode"]
    )
    values = {"test_mode": test_mode}
    for name, check in MODE_FREE_CHECKS:
        values[name] = run_check(problems, name, check, raw_values[name])
    if test_mode is not None:
        for name, check in MODE_DEPENDENT_CHECKS:
            values[name] = run_check(
                problems, name, check, raw_values[name], test_mode
            )
    if problems:
        raise ConfigError(path, describe_problems(problems))
    return Settings(**values)


def run_check(problems, name, check, *arguments):
    """Return ``check(*arguments)``; on failure record why, return None."""
    try:
        return check(*arguments)
    except ValidationError as error:
        problems[name] = str(error)
        return None


def describe_problems(problems):
    """Format the problems in the order the parameters are documented."""
    return [
        f"{name}: {problems[name]}"
        for name in PARAMETER_NAMES
        if name in problems
    ]
