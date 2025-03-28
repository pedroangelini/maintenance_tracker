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

GENERIC_FAIL_CODE = 1

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

########################################
# Helper functions
########################################


def _rich_task(t: Task) -> str:
    ret_str = f"Task: [bold]{t.name}[/bold]\n"
    if t.description:
        ret_str += f"[italic]{t.description}[/italic]\n"
    ret_str += f"starting on: {utils.human_date_str(t.start_time)}\n"
    ret_str += f"interval:    {utils.human_interval_str(t.interval)}\n"
    return ret_str


def _print_task_list_table(task_list: TaskLister) -> None:
    table = rich.table.Table(title="Task List")

    table.add_column("Name", justify="left", no_wrap=True)
    table.add_column("Description")
    table.add_column("Start Time", justify="right", style="green")
    table.add_column("Interval", justify="right", style="green")

    for t in task_list:
        table.add_row(
            t.name,
            t.description,
            utils.human_date_str(t.start_time),
            utils.human_interval_str(t.interval),
        )

    console = rich.console.Console()
    console.print(table)


########################################
# add app
########################################


@add_app.command(
    "task",
    no_args_is_help=True,
)
def add_task(
    name: Annotated[
        Optional[str],
        typer.Argument(help="name of the task (required)", show_default=False),
    ] = None,
    start_time: Annotated[str, typer.Argument()] = "now",
    interval: Annotated[str, typer.Argument()] = "",
    description: Annotated[str, typer.Argument()] = "",
    interactive: Annotated[
        bool, typer.Option("-i", help="asks for each argument in turn")
    ] = False,
):
    """Adds a task to the tracker"""
    if interactive:
        logger.info("interactively adding a task")
        if name is None:
            name = typer.prompt("Task Name", type=str, default="default task")
        if start_time == "now":
            start_time = typer.prompt("Task Start Time", type=str, default="now")
        if interval == "":
            interval = typer.prompt("Task Interval", type=str, default="")
        if description == "":
            description = typer.prompt("Task Description", type=str, default="")

    logger.info(f"Adding task: {name}")
    logger.info(f"{start_time = }")
    logger.info(f"{interval = }")
    logger.info(f"{description = }")

    try:
        t = Task(
            name,
            description,
            utils.parse_date(start_time),
            utils.parse_interval(interval),
        )
        app.register_task(t)
        rich.print(f":heavy_check_mark: [green]Successfully created task[/green]\n{t}")
    except Exception as e:
        rich.print(f":x: [red]:something went wrong:[/red]\n{str(e)}")
        raise typer.Exit(code=GENERIC_FAIL_CODE)


@add_app.command("action")
def add_action():
    print("add task command!")


########################################
# record app
########################################


def record():
    print("record command!")


########################################
# list app
########################################


@list_app.command("tasks", help="Prints a list of task")
def list():
    task_list = app.get_all_tasks()
    _print_task_list_table(task_list)


########################################
# get app
########################################


@get_app.command(
    "tasks",
    # no_args_is_help=True,
)
def get_tasks(
    name: Annotated[Optional[str], typer.Option()] = "",
    interval: Annotated[Optional[str], typer.Option()] = "",
):
    """get all tasks based on either a name or a time interval"""

    if not name and not interval:
        task_list = app.get_all_tasks()
    elif name is not None:
        print(name)
        task_list = app.get_tasks_by_name(name)
    else:
        task_list = app.get_tasks_by_time()

    rich.print(f"found {len(task_list)} tasks")
    for t in task_list:
        rich.print(_rich_task(t))


@get_app.command(
    "task",
    no_args_is_help=True,
)
def get_task(name: Annotated[str, typer.Argument()]):
    """get tasks by name"""
    t = _rich_task(app.get_task_by_name(name))
    rich.print(t)


########################################
# edit app
########################################


@edit_app.command(
    "task",
    no_args_is_help=True,
)
def edit_task(
    task_name: Annotated[str, typer.Argument(help="name of the task to edit")],
    new_start_time: Annotated[
        Optional[str], typer.Argument(help="new start time for the task")
    ] = None,
    new_periodicity: Annotated[
        Optional[str], typer.Argument(help="new periodicity for the task")
    ] = None,
    new_description: Annotated[
        Optional[str], typer.Argument(help="new description for the task")
    ] = None,
    rename: Annotated[
        Optional[str], typer.Option("--rename", help="new name for the task")
    ] = None,
    interactive: Annotated[
        bool, typer.Option("-i", "--interactive", help="edit task interactively")
    ] = False,
):
    """Edits a task in the tracker"""
    original_task = app.get_task_by_name(task_name)


    if original_task is None:
        rich.print(f":x: [red]Task '{task_name}' not found[/red]")
        raise typer.Exit(code=GENERIC_FAIL_CODE)

    if interactive:
        logger.info("interactively editing task")
        if new_start_time is None:
            new_start_time = typer.prompt(
                "New Start Time", type=str, default=original_task.start_time
            )
        if new_periodicity is None:
            new_periodicity = typer.prompt(
                "New Periodicity", type=str, default=original_task.interval
            )
        if new_description is None:
            new_description = typer.prompt(
                "New Description", type=str, default=original_task.description
            )
        if rename is None:
            rename = typer.prompt("New Name", type=str, default=original_task.name)

    changes: dict = dict()

    if rename:
        changes["name"] = rename
    if new_start_time:
        changes["start_time"] = utils.parse_date(new_start_time)
    if new_periodicity:
        changes["interval"] = utils.parse_interval(new_periodicity)
    if new_description:
        changes["description"] = new_description

    new_task = app.edit_task(original_task, changes)
    

    if new_task is not None:
        rich.print(
            f":heavy_check_mark: [green]Task '{task_name}' updated successfully[/green]\n{new_task}"
        )
    else: 
        rich.print(
            f":cross_mark: [red]Could not update '{task_name}'[/red]\n"
        )
        raise typer.Exit(code=GENERIC_FAIL_CODE)
        


########################################
# delete app
########################################


def delete():
    print("delete command!")


########################################
# report app
########################################

########################################
# footer
########################################

if __name__ == "__main__":
    rich.print("[red]please run the main file[/red]", file=sys.stderr)
    raise SystemExit(0)
