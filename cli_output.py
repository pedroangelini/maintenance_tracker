from core import *
from enum import Enum


class Format(Enum):
    READABLE = 1
    MACHINE = 2


class CliOutput:

    output_type: str = "cli"

    def task(self, task: Task) -> None: ...

    def actions(self, action: Action) -> None: ...

    def task_list(
        self, task_list: TaskLister, format: Format = Format.READABLE
    ) -> None: ...

    def action_list(
        self, action_list: ActionLister, Format=Format.READABLE
    ) -> None: ...

    def task_report(
        self, task: Task, action_list: ActionLister, format: Format = Format.READABLE
    ) -> None: ...
