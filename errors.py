"""Custom domain exceptions for maintenance_tracker.

Exceptions represent control-flow error conditions (not-found, duplicates, dangling dependencies).
"""


class MaintenanceTrackerError(Exception):
    """Base class for tracker-related exceptions."""


class TaskNotFoundError(MaintenanceTrackerError):
    """Raised when a task referenced by name does not exist."""


class DuplicateTaskError(MaintenanceTrackerError):
    """Raised when attempting to register a task with a name that already exists."""


class ActionNotFoundError(MaintenanceTrackerError):
    """Raised when attempting to operate on an action that does not exist."""


class DanglingActionsError(MaintenanceTrackerError):
    """Raised when attempting to delete/replace a task that still has actions attached."""
