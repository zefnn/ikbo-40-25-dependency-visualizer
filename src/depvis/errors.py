"""Exceptions raised while reading and checking the configuration."""


class ValidationError(Exception):
    """Raised by a parameter check when the value cannot be used."""


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
