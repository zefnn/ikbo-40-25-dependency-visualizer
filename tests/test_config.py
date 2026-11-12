"""Unit tests for reading the configuration file in depvis.config."""

import pytest

from depvis.config import PARAMETER_NAMES, Settings, load_settings
from depvis.errors import ConfigError

UTF8_BOM = "\ufeff"


def load_errors(path):
    """Return the messages of the ConfigError raised for ``path``."""
    with pytest.raises(ConfigError) as caught:
        load_settings(path)
    return caught.value.messages


def test_parameter_names_match_the_task():
    """All seven parameters from the task are configurable."""
    assert PARAMETER_NAMES == (
        "package_name",
        "repository",
        "test_mode",
        "version",
        "output_image",
        "ascii_tree",
        "filter_substring",
    )


def test_valid_config_is_loaded(make_config):
    """A correct file gives Settings with converted values."""
    assert load_settings(make_config()) == Settings(
        package_name="requests",
        repository="https://pypi.org/pypi",
        test_mode=False,
        version="2.32.3",
        output_image="graph.png",
        ascii_tree=False,
        filter_substring="",
    )


def test_test_mode_config_is_loaded(make_config, repo_file):
    """In test mode the repository is a file and names are capitals."""
    path = make_config(
        package_name="A",
        repository=repo_file,
        test_mode="yes",
        ascii_tree="on",
        filter_substring="C",
    )
    settings = load_settings(path)
    assert settings.test_mode is True
    assert settings.ascii_tree is True
    assert settings.repository == repo_file
    assert settings.filter_substring == "C"


def test_parameter_names_are_case_insensitive(config_path):
    """Parameter names may be written in any letter case."""
    config_path.write_text(
        "[settings]\n"
        "PACKAGE_NAME = requests\n"
        "Repository = https://pypi.org/pypi\n"
        "Test_Mode = false\n"
        "VERSION = 2.32.3\n"
        "output_image = graph.png\n"
        "ASCII_TREE = no\n"
        "filter_substring =\n",
        encoding="utf-8",
    )
    assert load_settings(str(config_path)).package_name == "requests"


def test_utf8_bom_is_accepted(make_config, config_path):
    """A byte order mark written by some editors does not break parsing."""
    path = make_config()
    text = config_path.read_text(encoding="utf-8")
    config_path.write_text(UTF8_BOM + text, encoding="utf-8")
    assert load_settings(path).version == "2.32.3"


def test_percent_sign_is_kept_verbatim(make_config):
    """Interpolation is off, so a '%' in a value is not an error."""
    url = "https://example.com/simple%20index"
    assert load_settings(make_config(repository=url)).repository == url


def test_missing_file_is_reported():
    """A config file that does not exist is reported."""
    assert load_errors("absent.ini") == ["file not found"]


def test_directory_is_reported(tmp_path):
    """A directory given instead of a file is reported."""
    assert load_errors(str(tmp_path)) == ["this is a directory, not a file"]


def test_unreadable_path_is_reported(tmp_path):
    """Other operating system errors are reported with their reason."""
    plain = tmp_path / "plain.txt"
    plain.write_text("text", encoding="utf-8")
    (message,) = load_errors(str(plain / "config.ini"))
    assert message.startswith("cannot read the file")


def test_non_utf8_file_is_reported(config_path):
    """A file in another encoding is reported."""
    config_path.write_bytes(b"[settings]\npackage_name = caf\xe9\n")
    assert load_errors(str(config_path)) == ["the file is not UTF-8 text"]


def test_parameter_before_section_is_reported(config_path):
    """A parameter written before any section header is reported."""
    config_path.write_text(
        "; comment\npackage_name = requests\n", encoding="utf-8"
    )
    assert load_errors(str(config_path)) == [
        "line 2: parameter outside of any section"
    ]


def test_lines_without_equals_sign_are_reported(config_path):
    """Every line that is not a 'key = value' pair is reported."""
    config_path.write_text(
        "[settings]\npackage_name requests\nversion: 1.0\n",
        encoding="utf-8",
    )
    assert load_errors(str(config_path)) == [
        "line 2: expected 'key = value'",
        "line 3: expected 'key = value'",
    ]


def test_repeated_parameter_is_reported(config_path):
    """A parameter given twice is reported with its line."""
    config_path.write_text(
        "[settings]\nversion = 1.0\nversion = 2.0\n", encoding="utf-8"
    )
    assert load_errors(str(config_path)) == [
        "line 3: parameter 'version' is repeated"
    ]


def test_repeated_section_is_reported(config_path):
    """A section given twice is reported with its line."""
    config_path.write_text("[settings]\n[settings]\n", encoding="utf-8")
    assert load_errors(str(config_path)) == [
        "line 2: section [settings] is repeated"
    ]


def test_wrong_section_is_reported(config_path):
    """A misspelled section is unknown and [settings] is missing."""
    config_path.write_text(
        "[setting]\npackage_name = requests\n", encoding="utf-8"
    )
    assert load_errors(str(config_path)) == [
        "unknown section [setting]",
        "section [settings] is missing",
    ]


def test_empty_file_is_reported(config_path):
    """An empty file has no [settings] section."""
    config_path.write_text("", encoding="utf-8")
    assert load_errors(str(config_path)) == ["section [settings] is missing"]


def test_unknown_parameter_is_reported(make_config):
    """A parameter the application does not know is reported."""
    assert load_errors(make_config(depth="3")) == [
        "unknown parameter 'depth'"
    ]


def test_missing_parameters_are_reported(make_config):
    """Every parameter absent from the file is reported."""
    path = make_config(version=None, ascii_tree=None)
    assert load_errors(path) == [
        "missing parameter 'version'",
        "missing parameter 'ascii_tree'",
    ]


def test_empty_values_are_all_reported(make_config):
    """Empty values are reported for every required parameter."""
    path = make_config(
        package_name="",
        repository="",
        version="",
        output_image="",
        ascii_tree="",
    )
    assert load_errors(path) == [
        "package_name: must not be empty",
        "repository: must not be empty",
        "version: must not be empty",
        "output_image: must not be empty",
        "ascii_tree: must not be empty",
    ]


def test_several_invalid_values_are_reported_together(make_config):
    """All invalid values are reported in the documented order."""
    path = make_config(
        filter_substring="a b",
        ascii_tree="sometimes",
        output_image="graph.jpg",
        version="2.x",
        repository="pypi.org/pypi",
        package_name="requests!",
    )
    assert load_errors(path) == [
        "package_name: 'requests!' is not a valid pip package name",
        "repository: 'pypi.org/pypi' is not an http(s) URL "
        "(test files need test_mode = true)",
        "version: '2.x' is not a PEP 440 version (e.g. 2.32.3)",
        "output_image: 'graph.jpg' does not end with .png",
        "ascii_tree: 'sometimes' is not a boolean "
        "(use true/false, yes/no, on/off, 1/0)",
        "filter_substring: 'a b' may contain only Latin letters, "
        "digits and . _ -",
    ]


def test_invalid_test_mode_skips_mode_dependent_checks(make_config):
    """Without a valid mode the name and repository are not checked."""
    path = make_config(
        test_mode="maybe", package_name="bad name", repository="bad url"
    )
    assert load_errors(path) == [
        "test_mode: 'maybe' is not a boolean "
        "(use true/false, yes/no, on/off, 1/0)"
    ]


def test_test_mode_requires_existing_repository_file(make_config):
    """In test mode a missing repository file is reported."""
    path = make_config(
        package_name="A", test_mode="true", repository="missing.txt"
    )
    assert load_errors(path) == [
        "repository: file 'missing.txt' does not exist"
    ]


def test_test_mode_rejects_pip_package_name(make_config, repo_file):
    """In test mode the package name must be made of capitals."""
    path = make_config(test_mode="true", repository=repo_file)
    assert load_errors(path) == [
        "package_name: 'requests' is not a test package name "
        "(capital letters A-Z)"
    ]


def test_filter_matching_the_package_is_reported(make_config):
    """A filter that removes the analysed package itself is an error."""
    assert load_errors(make_config(filter_substring="REQ")) == [
        "filter_substring: 'REQ' matches the analysed package "
        "'requests' itself, so nothing would be left to analyse"
    ]


def test_filter_matching_a_test_package_is_reported(make_config, repo_file):
    """The check also works for test package names, case-insensitively."""
    path = make_config(
        package_name="A",
        test_mode="true",
        repository=repo_file,
        filter_substring="a",
    )
    assert load_errors(path) == [
        "filter_substring: 'a' matches the analysed package "
        "'A' itself, so nothing would be left to analyse"
    ]


def test_config_error_text_lists_all_problems():
    """The text of ConfigError names the file and every problem."""
    error = ConfigError("a.ini", ["first", "second"])
    assert error.path == "a.ini"
    assert error.messages == ["first", "second"]
    assert str(error) == "a.ini: first; second"
