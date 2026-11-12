"""Exceptions raised by the dependency graph visualizer."""


class ValidationError(Exception):
    """Raised by a parameter check when the value cannot be used."""


class RequirementError(Exception):
    """Raised when a dependency string is not valid PEP 508."""


class RepositoryError(Exception):
    """Raised when the package repository cannot give the needed data."""


class PackageNotFoundError(RepositoryError):
    """Raised when the repository has no such package or version."""


class ConfigError(Exception):
    """Raised when the configuration file cannot be used.

    ``messages`` holds one line per problem found in the file, so that
    every mistake is reported in a single run of the application.
    """

    def __init__(self, path, messages):
        """Remember the file and the list of problems found in it."""
        self.path = path
        self.messages = list(messages)
        super().__init__(f"{path}: " + "; ".join(self.messages))
