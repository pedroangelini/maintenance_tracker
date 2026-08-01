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

    def default(self, obj):
        if isinstance(obj, datetime):
            return {
                "__type__": "datetime",
                "year": obj.year,
                "month": obj.month,
                "day": obj.day,
                "hour": obj.hour,
                "minute": obj.minute,
                "second": obj.second,
                "microsecond": obj.microsecond,
                "utcoffset": obj.utcoffset(),
            }

        elif isinstance(obj, timedelta):
            return {
                "__type__": "timedelta",
                "days": obj.days,
                "seconds": obj.seconds,
                "microseconds": obj.microseconds,
            }

        elif is_dataclass(obj):
            return {"__type__": obj.__class__.__name__} | asdict(obj)

        else:
            return json.JSONEncoder.default(self, obj)


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
