import sqlite3
from datetime import datetime, timezone, timedelta
from enum import Enum, auto
from typing import Self
import json

import pytimeparse2

# abbreviation for maintenance is mtn


def _parse_str_timedelta(input: str | timedelta) -> timedelta:
    if isinstance(input, str):
        result = pytimeparse2.parse(input, as_timedelta=True, raise_exception=True)
    elif isinstance(input, timedelta):
        result = input
    else:
        raise TypeError(
            f"Expected 'interval' to be a string or timedelta, got '{type(input)}' instead"
        )
    return result  # type: ignore


class list_options(Enum):
    ALL = auto()
    OVERDUE = auto()
    SOON_OVERDUE = auto()
    NOT_OVERDUE = auto()


class TaskWithSameNameError(ValueError):
    pass


class TaskNotFound(ValueError):
    pass


DEFAULT_SOON_OVERDUE = timedelta(days=3)


class mtn_instance:
    # an instance when the task was executed
    dtime_run: datetime
    is_skipped: bool = True
    other_data: dict = {}

    def __init__(
        self,
        dtime_run: datetime | None = None,
        skipped: bool = False,
        other_data: dict = {},
    ):
        if dtime_run is None:
            self.dtime_run = datetime.now(timezone.utc)
        else:
            dtime_run = dtime_run
        self.skipped = skipped
        self.other_data = {}


class mtn_task:
    # a task is a repetitive activity we want to track
    name: str
    mtn_instances: list[mtn_instance]  # ordered by datetime ascending
    interval: timedelta

    def __init__(
        self, name: str, interval: timedelta, mtn_instances: list[mtn_instance] = []
    ):
        self.name = name
        if isinstance(interval, str):
            self.interval = pytimeparse2.parse(interval, as_timedelta=True, raise_exception=True)  # type: ignore
        elif isinstance(interval, timedelta):
            self.interval = interval
        else:
            raise TypeError(
                f"Expected 'interval' to be a string or timedelta, got '{type(interval)}' instead"
            )
        self.mtn_instances = mtn_instances

    def record_run(
        self,
        instance: mtn_instance,
    ):
        self.mtn_instances.append(instance)

    def get_last_instance(self) -> mtn_instance:
        return self.mtn_instances[-1]

    def get_dtime_overdue(self) -> datetime:
        # returns the next overdue time in UTC

        # if the task has never been run, it is overdue now
        if len(self.mtn_instances) == 0:
            return datetime.now(timezone.utc)

        last_instance = self.mtn_instances[-1]
        return self.get_last_instance().dtime_run + self.interval

    def check_if_overdue(self, overdue_datetime_utc: datetime | None = None) -> bool:
        if overdue_datetime_utc is None:
            overdue_datetime_utc = datetime.now(tz=timezone.utc)

        return self.get_dtime_overdue() < overdue_datetime_utc

    def time_since_last_exec(
        self,
    ) -> timedelta:
        return datetime.now(tz=timezone.utc) - self.get_last_instance().dtime_run


class persistance_backend:
    # TODO: load from a config file?
    DB_CONFIG = {
        "FILE_PATH": "./data/maintenance.db",
        "DB_NAME": "main_db",
        "TASK_LIST_TABLE": "task_list",
        "TASK_TABLE": "tasks",
        "INSTANCE_TABLE": "instances",
    }

    def __init__(
        self,
    ):
        self.con = sqlite3.connect(self.DB_CONFIG["FILE_PATH"])
        self._create_tables_if_not_exist()

    def _create_tables_if_not_exist(self):
        with self.con as c:
            c.execute(
                f"""
                    CREATE TABLE IF NOT EXISTS {self.DB_CONFIG["TASK_TABLE"]} ( 
                    task_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT NOT NULL,
                    interval TEXT
                    );
                """
            )
            c.execute(
                f"""
                    CREATE TABLE IF NOT EXISTS {self.DB_CONFIG["INSTANCE_TABLE"]} ( 
                    instance_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER,
                    dtime_run TEXT NOT NULL,
                    is_skipped INTEGER,
                    other_data TEXT
                    );
                """
            )

    def load_task_list(self) -> list[mtn_task]:
        with self.con as c:
            tasks = c.execute(
                f"SELECT [task_id], [task_name], [interval] FROM {self.DB_CONFIG['TASK_TABLE']}"
            )

        return_list = []
        for t in tasks:
            insts = self.load_instances_from_task(t["task_id"])
            return_list.append(
                mtn_task(
                    name=t["task_name"], interval=t["interval"], mtn_instances=insts
                )
            )

        return return_list

    def load_instances_from_task(self, task_id: int) -> list[mtn_instance]:
        with self.con as c:
            insts = c.execute(
                f"""
                SELECT [instance_id], [dtime_run], [is_skipped], [other_data]
                FROM {self.DB_CONFIG['INSTANCE_TABLE']}
                WHERE [task_id] = {task_id}
                """
            )
        return_list = [
            mtn_instance(i["dtime_run"], i["is_skipped"], json.loads(i["other_data"]))
            for i in insts
        ]

        return return_list

    # brute force re-loading everything from scratch,
    # surelly we can make this more effective, but it will work for the prototype
    def save(self, lst: list[mtn_task]):
        with self.con as c:
            c.execute(f"DELETE FROM {self.DB_CONFIG['TASK_TABLE']}")
            c.execute(f"DELETE FROM {self.DB_CONFIG['INSTANCE_TABLE']}")

        with self.con as c:
            cur = c.cursor()
            sql_tupples = [(t.name, str(t.interval)) for t in lst]
            cur.executemany(
                f"INSERT INTO {self.DB_CONFIG['TASK_TABLE']} (name, interval) VALUES (?,?)",
                sql_tupples,
            )
            # CONTINUE HERE
            sql_tupples = [()]


class mtn_list:
    # list of all the maintenance tasks
    lst: list[mtn_task] = []
    backend: persistance_backend

    def __init__(
        self,
        task_list: list[mtn_task],
    ):
        self.lst = task_list
        self.backend = persistance_backend()
        lst = self.backend.load_task_list()

    def add_task(self, task: mtn_task) -> Self:
        # adds a task to the list
        # does not let two tasks with the same name to be added
        for t in self.lst:
            if t.name == task.name:
                raise TaskWithSameNameError(
                    f"tried to add a task named {task.name} but there's already one in the list"
                )
        self.lst.append(task)
        self.backend.save(self.lst)
        return self

    def delete_task(self, task: mtn_task) -> Self:
        self.lst.remove(task)
        self.backend.save(self.lst)
        return self

    def get_task_by_name(self, name: str) -> mtn_task:
        for t in self.lst:
            if t.name == name:
                return t
        raise TaskNotFound(name)

    def list_tasks(
        self,
        options: list_options = list_options.ALL,
        tasks_filter: list[str | mtn_task] | None = None,
        how_soon_overdue: str | timedelta | None = None,
    ) -> list:
        # get all the tasks that match the
        if tasks_filter is None:
            filter_result = self.lst
        else:
            filter_result = [
                tsk if isinstance(tsk, mtn_task) else self.get_task_by_name(str(tsk))
                for tsk in tasks_filter
            ]

        match options:
            case list_options.ALL:
                return filter_result
            case list_options.OVERDUE:
                return [t for t in filter_result if t.check_if_overdue()]
            case list_options.SOON_OVERDUE:
                if how_soon_overdue is None:
                    how_soon_overdue = DEFAULT_SOON_OVERDUE
                elif isinstance(how_soon_overdue, str):
                    how_soon_overdue = _parse_str_timedelta(how_soon_overdue)

                return [
                    t
                    for t in filter_result
                    if t.check_if_overdue(
                        datetime.now(tz=timezone.utc) + how_soon_overdue
                    )
                ]
            case list_options.NOT_OVERDUE:
                return [t for t in filter_result if not t.check_if_overdue()]


class schedulable_mnt_task(mtn_task):
    # a type of task that runs in specific times of the day, week, month, year
    pass


class timeout_mnt_task(mtn_task):
    # a type of task that becomes overdue after a certain amount of time
    pass
