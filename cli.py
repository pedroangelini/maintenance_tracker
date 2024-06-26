# cli implements the typer app

import logging
import sys
from typing import Optional

import rich
import typer
from typing_extensions import Annotated

import app
import utils
from core import *
from maintenance_tracker import *

logger = logging.getLogger(__name__)


add_app = typer.Typer(
    no_args_is_help=True, help="adds a Task or an Action to the tracker"
)
record_app = typer.Typer(
    no_args_is_help=True, help="adds an Action (same as mtnt add action)"
)
list_app = typer.Typer(no_args_is_help=True, help="list Tasks or Actions")
get_app = typer.Typer(no_args_is_help=True, help="gets details of a Task or Action")
edit_app = typer.Typer(no_args_is_help=True, help="edits a Task or Action")
delete_app = typer.Typer(no_args_is_help=True, help="deletes a Task or Action")
report_app = typer.Typer(no_args_is_help=True, help="creates reports")


@add_app.command(
    "task",
    no_args_is_help=True,
)
def add_task(
    name: str,
    start_time: Annotated[str, typer.Argument()] = "now",
    interval: Annotated[str, typer.Argument()] = "",
    description: str = "",
):
    """Adds a task to the tracker"""
    logger.info(f"Adding task: {name}")
    logger.info(f"{start_time = }")
    logger.info(f"{interval = }")
    logger.info(f"{description = }")

    t = Task(
        name, description, utils.parse_date(start_time), utils.parse_interval(interval)
    )
    app.register_task(t)


@add_app.command("action")
def add_action():
    print("add task command!")


def record():
    print("record command!")


def list():
    print("list command!")


@get_app.command(
    "tasks",
    # no_args_is_help=True,
)
def get_tasks(
    name: Annotated[Optional[str], typer.Option()] = "",
    interval: Annotated[Optional[str], typer.Option()] = "",
):
    """get all tasks based on either a name or a time interval"""

    if name == "" and interval == "":
        task_list = app.get_all_tasks()
        for t in task_list:
            print(t)
    elif name is not None:
        print(app.get_task_by_name(name))
    else:
        print("oh no!")


@get_app.command(
    "task",
    # no_args_is_help=True,
)
def get_task(name: Annotated[str, typer.Argument()]):
    """get tasks by name"""
    print(app.get_task_by_name(name))


def edit():
    print("edit command!")


def delete():
    print("delete command!")


if __name__ == "__main__":
    rich.print("[red]please run the main file[/red]", file=sys.stderr)
    raise SystemExit(0)
