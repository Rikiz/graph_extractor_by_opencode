"""
Custom exceptions for the repo analyzer module.
"""


class RepoAnalyzerError(Exception):
    """Base exception for all repo analyzer errors."""

    pass


class ConfigurationError(RepoAnalyzerError):
    """Raised when there's a configuration problem."""

    pass


class Neo4jConnectionError(RepoAnalyzerError):
    """Raised when connection to Neo4j fails."""

    pass


class Neo4jQueryError(RepoAnalyzerError):
    """Raised when a Neo4j query fails."""

    pass


class ParserError(RepoAnalyzerError):
    """Raised when parsing a file fails."""

    pass


class ValidationError(RepoAnalyzerError):
    """Raised when validation fails."""

    pass


class RepoNotFoundError(RepoAnalyzerError):
    """Raised when a repo doesn't exist in Neo4j."""

    pass


class GroupNotFoundError(RepoAnalyzerError):
    """Raised when a group doesn't exist."""

    pass


class DuplicateEntityError(RepoAnalyzerError):
    """Raised when trying to create a duplicate entity."""

    pass


class MatchError(RepoAnalyzerError):
    """Raised when matching fails unexpectedly."""

    pass
