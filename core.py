# Second try at the maintenance tracker, keeping fewer dependencies between objects
#
# Structure:
# - task: a repetitive thing we need to do and want to track
#         includes information about what needs to be done (title, description) and
#         when it needs to be done (frequency or due date)
# - action: something we did and want to track. Can be tied to a task or not
#           includes information about what was done (title, description)
#           and when (timestamp)
#
# - listers:
#   |-- task_lister: tracks a list of tasks, including assigning an ID to each task
#   |-- action_lister: tracks list of actions, including assigning an ID to each action
#
# - persisters: save data of tasks and actions
#
# - maintenance_tracker: compares tasks and actions to check which are due, overdue, etc

import json
import logging  # debug(), info(), warning(), error() and critical()
from abc import ABC, abstractmethod
from collections import UserList
from copy import deepcopy
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Sequence

DEFAULT_SAVE_DIR = "./data"
DEFAULT_ACTION_LIST_FILE = "action_list.json"
DEFAULT_TASK_LIST_FILE = "task_list.json"


class Ordering(Enum):
    ASC = 1
    DESC = 2


@dataclass(frozen=True)
class task:
    name: str = "default_task"
    description: str = "No description provided"
    start_time: datetime | None = None
    interval: timedelta = timedelta(seconds=0)

    def copy(self):
        return deepcopy(self)


@dataclass(frozen=True)
class action:
    timestamp: datetime
    ref_task: task
    name: str = ""
    description: str = ""
    actor: str = ""

    def copy(self):
        return deepcopy(self)


class TaskWithSameNameError(KeyError):
    pass


class task_lister(UserList):
    def __init__(self, task_list: Sequence[task] = []):
        names = [t.name for t in task_list]
        if len(names) > len(set(names)):
            error_msg = f"Error adding a task to the list: cannot have two tasks with the same name. Got these names'{names}'."
            logging.debug(error_msg)
            raise TaskWithSameNameError(error_msg)

        super().__init__(task_list)

    def _check_task_name_available(self, target_task_name: str) -> bool:
        for t in self.data:
            if t.name == target_task_name:
                return False
        return True

    def add(self, new_task: task) -> None:
        self.append(new_task)

    def extend(self, new_tasks: Sequence[task]) -> None:
        for t in new_tasks:
            self.append(t)

    def append(self, new_task: task) -> None:
        if self._check_task_name_available(new_task.name):
            super().append(new_task)
        else:
            error_msg = f"Error adding a task to the list: cannot have two tasks with the same name. '{new_task.name}' already exist."
            logging.debug(error_msg)
            raise (TaskWithSameNameError(error_msg))


class action_lister(UserList):
    def __init__(self, action_list: Sequence[action] = []):
        super().__init__(action_list)

    def __eq__(self, other):
        if not isinstance(other, action_lister):
            raise TypeError(f"Cannot compare action_list to {type(other)}")

        if len(self) != len(other):
            return False

        sorted_self = sorted(self.data, key=lambda a: a.timestamp)
        sorted_other = sorted(self.data, key=lambda a: a.timestamp)

        for i, j in zip(sorted_self, sorted_other):
            if i != j:
                return False

        return True


class MtnTrackerJSONEncoder(json.JSONEncoder):
    """
    Converts a python object, where datetime and timedelta objects are converted
    into objects that can be decoded using the DateTimeAwareJSONDecoder.
    """

    def default(self, obj):
        # TODO add an check for tasks and one for actions
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
    """
    Converts a json string, where datetime and timedelta objects were converted
    into objects using the DateTimeAwareJSONEncoder, back into a python object.
    """

    def __init__(self):
        json.JSONDecoder.__init__(self, object_hook=self.dict_to_object)

    def dict_to_object(self, d):
        if "__type__" not in d:
            return d

        type = d.pop("__type__")
        if type == "datetime":
            return datetime(**d)
        elif type == "timedelta":
            return timedelta(**d)
        elif type == "task":
            return task(**d)
        elif type == "action":
            return action(**d)
        else:
            # Oops... better put this back together.
            d["__type__"] = type
            return d


class persister:
    dirname: str = DEFAULT_SAVE_DIR
    filename: str
    save_path: Path

    def __init__(self, persisted_object):
        self.obj = persisted_object

    def save(self):
        with open(self.save_path, "w", encoding="utf8") as f:
            json.dump(self.obj.data, f, cls=MtnTrackerJSONEncoder)
        return self.obj

    def load(self):
        with open(self.save_path, "r", encoding="utf8") as f:
            loaded_data = json.load(f, cls=MtnTrackerJSONDecoder)

        self.obj.data = loaded_data

        return self.obj

    def _remove_file(self):
        import os

        try:
            os.remove(self.save_path)
        except FileNotFoundError:
            logging.warning(
                f"Tried removing file {self.save_path}, but it didn't exist. Will continue."
            )


class action_list_persister(persister):
    def __init__(self, action_list, dirname=None, filename=None):
        super().__init__(action_list)
        if dirname is not None:
            self.dirname = dirname
        if filename is None:
            filename = DEFAULT_ACTION_LIST_FILE
        self.filename = filename
        self.save_path = Path(self.dirname).joinpath(self.filename)


class task_list_persister(persister):
    def __init__(self, task_list, dirname=None, filename=None):
        super().__init__(task_list)
        if dirname is not None:
            self.dirname = dirname
        if filename is None:
            filename = DEFAULT_TASK_LIST_FILE
        self.filename = filename
        self.save_path = Path(self.dirname).joinpath(self.filename)


if __name__ == "__main__":
    pass
