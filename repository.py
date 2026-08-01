"""Persistence layer (infrastructure). Contains repository/persister adapters for Tasks and Actions.

This module centralizes JSON encoding/decoding and file I/O so domain models remain pure.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dataclasses import asdict, is_dataclass
from typing import Any

import core

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

    def save(self):
        logger.info(f"writing to {self.save_path}")
        # Ensure directory exists
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.save_path, "w", encoding="utf8") as f:
            json.dump(self.obj.data, f, cls=MtnTrackerJSONEncoder, indent=4)
        return self.obj

    def load(self):
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
class TaskRepository:
    """Simple repository interface for tasks."""

    def list(self):
        raise NotImplementedError

    def get_by_name(self, name: str):
        raise NotImplementedError

    def add(self, task):
        raise NotImplementedError

    def remove(self, task):
        raise NotImplementedError

    def save(self):
        raise NotImplementedError

    def load(self):
        raise NotImplementedError


class FileTaskRepository(TaskRepository):
    def __init__(self, task_list=None, dirname=None, filename=None):
        import core

        if task_list is None:
            task_list = core.TaskLister([])
        self.task_list = task_list
        self.persister = TaskListPersister(self.task_list, dirname, filename)
        self.dirname = self.persister.dirname
        self.filename = self.persister.filename

    def list(self):
        return self.task_list

    def get_by_name(self, name: str):
        return self.task_list.get_task_by_name(name)

    def add(self, task):
        self.task_list.append(task)

    def remove(self, task):
        self.task_list.remove(task)

    def save(self):
        return self.persister.save()

    def load(self):
        return self.persister.load()


class ActionRepository:
    """Simple repository interface for actions."""

    def list(self):
        raise NotImplementedError

    def add(self, action):
        raise NotImplementedError

    def remove(self, action):
        raise NotImplementedError

    def get_for_task(self, task):
        raise NotImplementedError

    def get_by_time(self, start_time, end_time=None):
        raise NotImplementedError

    def save(self):
        raise NotImplementedError

    def load(self):
        raise NotImplementedError


class FileActionRepository(ActionRepository):
    def __init__(self, action_list=None, dirname=None, filename=None):
        import core

        if action_list is None:
            action_list = core.ActionLister([])
        self.action_list = action_list
        self.persister = ActionListPersister(self.action_list, dirname, filename)
        self.dirname = self.persister.dirname
        self.filename = self.persister.filename

    def list(self):
        return self.action_list

    def add(self, action):
        self.action_list.append(action)

    def remove(self, action):
        self.action_list.remove(action)

    def get_for_task(self, task, start_time=None, end_time=None, ordered=False):
        # replicate existing filtering semantics
        result_list = [a for a in self.action_list if a.ref_task.name == task.name]
        if start_time or end_time:
            if start_time is None:
                start_time = datetime.min.replace(tzinfo=timezone.utc)
            if end_time is None:
                end_time = datetime.now(timezone.utc)
            result_list = [a for a in result_list if start_time <= a.timestamp <= end_time]
        if ordered:
            from core import Ordering
            result_list = sorted(result_list, key=lambda a: a.timestamp, reverse=(ordered == Ordering.DESC))
        return result_list

    def get_by_time(self, start_time, end_time=None):
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        return [a for a in self.action_list if start_time <= a.timestamp <= end_time]

    def save(self):
        return self.persister.save()

    def load(self):
        return self.persister.load()
