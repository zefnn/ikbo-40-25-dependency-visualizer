"""Unit tests for the parameter checks in depvis.validation."""

import pytest

from depvis.errors import ValidationError
from depvis.validation import (
    check_filter,
    check_output_image,
    check_package_name,
    check_repository,
    check_version,
    parse_flag,
    require_text,
)


def test_require_text_strips_spaces():
    """Spaces around a value are removed."""
    assert require_text("  requests  ") == "requests"


@pytest.mark.parametrize("value", ["", "   "])
def test_require_text_rejects_blank_values(value):
    """An empty or blank value is reported as empty."""
    with pytest.raises(ValidationError, match="must not be empty"):
        require_text(value)


@pytest.mark.parametrize("word", ["true", "Yes", "ON", "1"])
def test_parse_flag_accepts_true_words(word):
    """Every spelling of a true value gives True."""
    assert parse_flag(word) is True


@pytest.mark.parametrize("word", ["false", "No", "OFF", "0"])
def test_parse_flag_accepts_false_words(word):
    """Every spelling of a false value gives False."""
    assert parse_flag(word) is False


@pytest.mark.parametrize("word", ["maybe", "2", "truee"])
def test_parse_flag_rejects_other_words(word):
    """A word that is not a boolean is reported."""
    with pytest.raises(ValidationError, match="is not a boolean"):
        parse_flag(word)


def test_parse_flag_rejects_empty_value():
    """A boolean parameter cannot be left empty."""
    with pytest.raises(ValidationError, match="must not be empty"):
        parse_flag("")


@pytest.mark.parametrize(
    "name",
    ["requests", "Django", "zope.interface", "typing_extensions", "x"],
)
def test_package_name_accepts_pip_names(name):
    """Valid pip package names pass in the normal mode."""
    assert check_package_name(name, test_mode=False) == name


@pytest.mark.parametrize(
    "name", ["requests!", "two words", "-dash", "dot.", "пакет"]
)
def test_package_name_rejects_invalid_names(name):
    """Names that break the pip naming rules are reported."""
    with pytest.raises(ValidationError, match="not a valid pip package"):
        check_package_name(name, test_mode=False)


@pytest.mark.parametrize("name", ["A", "B", "ABC"])
def test_package_name_in_test_mode_accepts_capitals(name):
    """Capital Latin letters form a valid test package name."""
    assert check_package_name(name, test_mode=True) == name


@pytest.mark.parametrize("name", ["a", "A1", "Ab", "requests"])
def test_package_name_in_test_mode_rejects_other_names(name):
    """Anything but capital Latin letters is rejected in test mode."""
    with pytest.raises(ValidationError, match="not a test package name"):
        check_package_name(name, test_mode=True)


def test_package_name_rejects_empty_value():
    """The package name cannot be left empty."""
    with pytest.raises(ValidationError, match="must not be empty"):
        check_package_name(" ", test_mode=False)


@pytest.mark.parametrize(
    "url", ["https://pypi.org/pypi", "http://localhost:8080/simple"]
)
def test_repository_accepts_http_urls(url):
    """Absolute http and https URLs are accepted in the normal mode."""
    assert check_repository(url, test_mode=False) == url


@pytest.mark.parametrize(
    "url",
    ["pypi.org/pypi", "ftp://pypi.org/pypi", "https://", "file:///repo"],
)
def test_repository_rejects_other_urls(url):
    """Only http and https URLs with a host name are accepted."""
    with pytest.raises(ValidationError, match="is not an http"):
        check_repository(url, test_mode=False)


def test_repository_rejects_spaces_in_url():
    """A URL with spaces inside is reported."""
    with pytest.raises(ValidationError, match="must not contain spaces"):
        check_repository("https://pypi .org/pypi", test_mode=False)


def test_repository_rejects_malformed_url():
    """A URL that cannot be parsed at all is reported."""
    with pytest.raises(ValidationError, match="is not a valid URL"):
        check_repository("http://[::1/pypi", test_mode=False)


def test_repository_rejects_empty_value():
    """The repository cannot be left empty."""
    with pytest.raises(ValidationError, match="must not be empty"):
        check_repository("", test_mode=False)


def test_repository_in_test_mode_accepts_existing_file(repo_file):
    """In test mode the repository is the path of an existing file."""
    assert check_repository(repo_file, test_mode=True) == repo_file


def test_repository_in_test_mode_rejects_missing_file():
    """A test repository file that does not exist is reported."""
    with pytest.raises(ValidationError, match="does not exist"):
        check_repository("missing.txt", test_mode=True)


def test_repository_in_test_mode_rejects_directory(tmp_path):
    """A directory cannot be used as a test repository file."""
    with pytest.raises(ValidationError, match="is not a file"):
        check_repository(str(tmp_path), test_mode=True)


@pytest.mark.parametrize(
    "version",
    [
        "2.32.3",
        "1.0",
        "1.0rc1",
        "1.0.0-beta.2",
        "2.0.post1",
        "1.0.dev3",
        "1!2.0",
        "1.0+local.7",
        "v1.2",
    ],
)
def test_version_accepts_pep440_versions(version):
    """Versions written by the PEP 440 rules are accepted."""
    assert check_version(version) == version


@pytest.mark.parametrize(
    "version", ["2.x", "latest", "1..2", "1.0 beta", ".1"]
)
def test_version_rejects_other_strings(version):
    """Strings that are not PEP 440 versions are reported."""
    with pytest.raises(ValidationError, match="is not a PEP 440 version"):
        check_version(version)


def test_version_rejects_empty_value():
    """The version cannot be left empty."""
    with pytest.raises(ValidationError, match="must not be empty"):
        check_version("")


@pytest.mark.parametrize("name", ["graph.png", "GRAPH.PNG"])
def test_output_image_accepts_png_names(name):
    """A PNG file name in an existing directory is accepted."""
    assert check_output_image(name) == name


def test_output_image_accepts_path_to_existing_directory(tmp_path):
    """The image may be placed into any existing directory."""
    name = str(tmp_path / "graph.png")
    assert check_output_image(name) == name


@pytest.mark.parametrize(
    "name", ["graph.jpg", "graph", ".png", "graph.png.txt"]
)
def test_output_image_requires_png_suffix(name):
    """The image file name must end with .png."""
    with pytest.raises(ValidationError, match="does not end with .png"):
        check_output_image(name)


def test_output_image_rejects_directory(tmp_path):
    """An existing directory cannot be used as the image file."""
    folder = tmp_path / "picture.png"
    folder.mkdir()
    with pytest.raises(ValidationError, match="is a directory"):
        check_output_image(str(folder))


def test_output_image_requires_existing_directory():
    """The directory that will hold the image must exist."""
    with pytest.raises(ValidationError, match="does not exist"):
        check_output_image("missing/graph.png")


def test_output_image_rejects_empty_value():
    """The image file name cannot be left empty."""
    with pytest.raises(ValidationError, match="must not be empty"):
        check_output_image("")


@pytest.mark.parametrize("text", ["", "test", "py-test_1.0", "  E  "])
def test_filter_accepts_name_characters(text):
    """The filter may be empty or made of package name characters."""
    assert check_filter(text) == text.strip()


@pytest.mark.parametrize("text", ["two words", "a/b", "ü", "*"])
def test_filter_rejects_other_characters(text):
    """Characters that never occur in package names are reported."""
    with pytest.raises(ValidationError, match="may contain only"):
        check_filter(text)
