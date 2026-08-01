"""Persistence layer (infrastructure). Contains repository/persister adapters for Tasks and Actions.

This module centralizes JSON encoding/decoding and file I/O so domain models remain pure.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dataclasses import asdict, is_dataclass
from typing import Any, Optional
from abc import ABC, abstractmethod

import core
from errors import DuplicateTaskError

logger = logging.getLogger(__name__)

DEFAULT_SAVE_DIR = "./data"
DEFAULT_ACTION_LIST_FILE = "action_list.json"
DEFAULT_TASK_LIST_FILE = "task_list.json"


class MtnTrackerJSONEncoder(json.JSONEncoder):
    """Converts python objects (datetimes, timedeltas, dataclasses) for JSON serialization."""

    def default(self, o: Any) -> Any:
        # keep signature compatible with json.JSONEncoder.default (param commonly named 'o')
        if isinstance(o, datetime):
            return {
                "__type__": "datetime",
                "year": o.year,
                "month": o.month,
                "day": o.day,
                "hour": o.hour,
                "minute": o.minute,
                "second": o.second,
                "microsecond": o.microsecond,
                "utcoffset": o.utcoffset(),
            }

        elif isinstance(o, timedelta):
            return {
                "__type__": "timedelta",
                "days": o.days,
                "seconds": o.seconds,
                "microseconds": o.microseconds,
            }

        elif is_dataclass(o):
            # asdict can be picky about the exact type, cast to Any to appease type checkers
            return {"__type__": getattr(o.__class__, "__name__", "dataclass")} | asdict(o)  # type: ignore[arg-type]

        else:
            return json.JSONEncoder.default(self, o)


class MtnTrackerJSONDecoder(json.JSONDecoder):
    """Decodes objects serialized by MtnTrackerJSONEncoder back into python objects."""

    def __init__(self):
        json.JSONDecoder.__init__(self, object_hook=self.dict_to_object)

    def dict_to_object(self, d: dict) -> Any:
        if "__type__" not in d:
            return d

        type_name = d.pop("__type__")
        if type_name == "datetime":
            return datetime(
                year=d["year"],
                month=d["month"],
                day=d["day"],
                hour=d["hour"],
                minute=d["minute"],
                second=d["second"],
                microsecond=d["microsecond"],
                tzinfo=timezone(d["utcoffset"]),
            )
        elif type_name == "timedelta":
            return timedelta(**d)
        elif type_name == "Task":
            return core.Task(**d)
        elif type_name == "Action":
            if "ref_task" in d and isinstance(d["ref_task"], dict):
                d["ref_task"] = core.Task(**d["ref_task"])
            return core.Action(**d)
        else:
            d["__type__"] = type_name
            return d


class Persister:
    dirname: str = DEFAULT_SAVE_DIR
    filename: str
    save_path: Path

    def __init__(self, persisted_object):
        self.obj = persisted_object

    def save(self) -> Any:
        """Persist the backing lister to disk and return the lister object."""
        logger.info(f"writing to {self.save_path}")
        # Ensure directory exists
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.save_path, "w", encoding="utf8") as f:
            json.dump(self.obj.data, f, cls=MtnTrackerJSONEncoder, indent=4)
        return self.obj

    def load(self) -> Any:
        """Load persisted data into the backing lister and return it (TaskLister/ActionLister)."""
        if not self.save_path.exists():
            # create an empty file with current object
            self.save()

        with open(self.save_path, "r", encoding="utf8") as f:
            loaded_data = json.load(f, cls=MtnTrackerJSONDecoder)

        self.obj.data = loaded_data

        return self.obj

    def _remove_file(self):
        import os

        try:
            os.remove(self.save_path)
        except FileNotFoundError:
            logger.warning(
                f"Tried removing file {self.save_path}, but it didn't exist. Will continue."
            )


class ActionListPersister(Persister):
    def __init__(self, action_list, dirname=None, filename=None):
        super().__init__(action_list)
        if dirname is not None:
            self.dirname = dirname
        if filename is None:
            filename = DEFAULT_ACTION_LIST_FILE
        self.filename = filename
        self.save_path = Path(self.dirname).joinpath(self.filename)


class TaskListPersister(Persister):
    def __init__(self, task_list, dirname=None, filename=None):
        super().__init__(task_list)
        if dirname is not None:
            self.dirname = dirname
        if filename is None:
            filename = DEFAULT_TASK_LIST_FILE
        self.filename = filename
        self.save_path = Path(self.dirname).joinpath(self.filename)


# --- Repository wrappers to enable dependency injection and a repository pattern ---
class TaskRepository(ABC):
    """Repository interface for tasks.

    Implementations must provide list/get/add/remove/save/load. Methods return
    core.TaskLister where appropriate (list/load) to keep types consistent.
    """

    @abstractmethod
    def list(self) -> core.TaskLister:
        """Return a TaskLister containing all tasks."""
        pass

    @abstractmethod
    def get_by_name(self, name: Optional[str]) -> Optional[core.Task]:
        """Return a Task by exact name or None if not found."""
        pass

    @abstractmethod
    def add(self, task: core.Task) -> None:
        """Add a Task to the repository; raise DuplicateTaskError on conflict."""
        pass

    @abstractmethod
    def remove(self, task: core.Task | None) -> None:
        """Remove a Task from the repository. Accepts None for convenience in some callers."""
        pass

    @abstractmethod
    def save(self) -> core.TaskLister:
        """Persist repository contents to storage and return TaskLister."""
        pass

    @abstractmethod
    def load(self) -> core.TaskLister:
        """Load repository contents from storage and return a TaskLister."""
        pass


class FileTaskRepository(TaskRepository):
    """File-backed TaskRepository using TaskListPersister internally.

    list() returns a TaskLister instance and add/remove mutate that lister.
    """

    def __init__(
        self,
        task_list: Optional[core.TaskLister] = None,
        dirname: Optional[str] = None,
        filename: Optional[str] = None,
    ):
        import core

        if task_list is None:
            task_list = core.TaskLister([])
        self.task_list: core.TaskLister = task_list
        self.persister: TaskListPersister = TaskListPersister(
            self.task_list, dirname, filename
        )
        self.dirname = self.persister.dirname
        self.filename = self.persister.filename

    def list(self) -> core.TaskLister:
        """Return the TaskLister backing this repository."""
        return self.task_list

    def get_by_name(self, name: Optional[str]) -> Optional[core.Task]:
        """Return a Task by name or None."""
        if name is None:
            return None
        return self.task_list.get_task_by_name(name)

    def add(self, task: core.Task) -> None:
        """Append a task to the internal TaskLister.

        Raises:
            DuplicateTaskError: if a task with the same name already exists
        """
        try:
            self.task_list.append(task)
        except Exception as e:
            # Normalize underlying TaskWithSameNameError to DuplicateTaskError
            raise DuplicateTaskError(str(e)) from e

    def remove(self, task: core.Task | None) -> None:
        """Remove a task from the internal TaskLister."""
        if task is None:
            # nothing to remove
            return
        self.task_list.remove(task)

    def save(self) -> core.TaskLister:
        """Persist the task list to disk via the persister and return TaskLister."""
        return self.persister.save()

    def load(self) -> core.TaskLister:
        """Load persisted task list via the persister and return TaskLister."""
        return self.persister.load()


class ActionRepository(ABC):
    """Repository interface for actions.

    Implementations should return core.ActionLister from list(), get_for_task() and get_by_time()
    to keep the public API consistent.
    """

    @abstractmethod
    def list(self) -> core.ActionLister:
        """Return an ActionLister of all actions."""
        pass

    @abstractmethod
    def add(self, action: core.Action) -> None:
        """Add an Action to the repository."""
        pass

    @abstractmethod
    def remove(self, action: core.Action | None) -> None:
        """Remove an Action from the repository. Accepts None for convenience in some callers."""
        pass

    @abstractmethod
    def get_for_task(
        self,
        task: core.Task,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        ordered: Optional["core.Ordering"] = None,
    ) -> core.ActionLister:
        """Return ActionLister of actions for a given task (optionally filtered by time).

        Signature accepts (task, start_time=None, end_time=None, ordered=Ordering.ASC).
        """
        pass

    @abstractmethod
    def get_by_time(
        self, start_time: datetime, end_time: Optional[datetime] = None
    ) -> core.ActionLister:
        """Return an ActionLister of actions within a time range."""
        pass

    @abstractmethod
    def save(self) -> core.ActionLister:
        """Persist repository contents to storage and return ActionLister."""
        pass

    @abstractmethod
    def load(self) -> core.ActionLister:
        """Load repository contents from storage and return an ActionLister."""
        pass


class FileActionRepository(ActionRepository):
    """File-backed ActionRepository using ActionListPersister internally.

    Methods return ActionLister to match the repository contract.
    """

    def __init__(
        self,
        action_list: Optional[core.ActionLister] = None,
        dirname: Optional[str] = None,
        filename: Optional[str] = None,
    ):
        import core

        if action_list is None:
            action_list = core.ActionLister([])
        self.action_list: core.ActionLister = action_list
        self.persister: ActionListPersister = ActionListPersister(
            self.action_list, dirname, filename
        )
        self.dirname = self.persister.dirname
        self.filename = self.persister.filename

    def list(self) -> core.ActionLister:
        """Return the ActionLister backing this repository."""
        return self.action_list

    def add(self, action: core.Action) -> None:
        """Append an action to the internal ActionLister."""
        self.action_list.append(action)

    def remove(self, action: core.Action | None) -> None:
        """Remove an action from the internal ActionLister."""
        if action is None:
            return
        self.action_list.remove(action)

    def get_for_task(
        self,
        task: core.Task,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        ordered: Optional["core.Ordering"] = None,
    ) -> core.ActionLister:
        """Return an ActionLister filtered by task and optional time range/order."""
        # replicate existing filtering semantics
        result_list = [a for a in self.action_list if a.ref_task.name == task.name]
        if start_time or end_time:
            if start_time is None:
                start_time = datetime.min.replace(tzinfo=timezone.utc)
            if end_time is None:
                end_time = datetime.now(timezone.utc)
            result_list = [
                a for a in result_list if start_time <= a.timestamp <= end_time
            ]
        if ordered:
            from core import Ordering

            # ensure ordered is Ordering enum
            if not isinstance(ordered, Ordering):
                ordered = Ordering(ordered) if ordered is not None else Ordering.ASC
            result_list = sorted(
                result_list,
                key=lambda a: a.timestamp,
                reverse=(ordered == Ordering.DESC),
            )
        # return ActionLister for consistency
        from core import ActionLister as _ActionLister

        return _ActionLister(result_list)

    def get_by_time(
        self, start_time: datetime, end_time: Optional[datetime] = None
    ) -> core.ActionLister:
        """Return an ActionLister of actions within a time window."""
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        from core import ActionLister as _ActionLister

        return _ActionLister(
            [a for a in self.action_list if start_time <= a.timestamp <= end_time]
        )

    def save(self) -> core.ActionLister:
        """Persist the action list to disk via the persister and return ActionLister."""
        return self.persister.save()

    def load(self) -> core.ActionLister:
        """Load persisted action list via the persister and return ActionLister."""
        return self.persister.load()
