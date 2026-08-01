# cli implements the typer app

import csv
import json
import logging
import sys
from enum import Enum
from typing import Optional

import rich
from rich.table import Table
from rich.console import Console
import typer
from typing_extensions import Annotated

import app
import utils
from core import *
from maintenance_tracker import *

logger = logging.getLogger(__name__)

GENERIC_FAIL_CODE = 1


class OutputFormat(str, Enum):
    TABLE = "table"
    JSON = "json"
    CSV = "csv"


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

from presenters import (
    _rich_task,
    _print_task_list_table,
    _print_action_list_table,
    _output_task_list_json,
    _output_task_list_csv,
    _output_action_list_json,
    _output_action_list_csv,
)

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
def add_action(
    task_name: Annotated[
        str, typer.Argument(help="name of the task to record an action for")
    ],
    actor: Annotated[
        Optional[str], typer.Argument(help="name of the person who did the action")
    ] = "",
    timestamp: Annotated[
        Optional[str], typer.Option(help="timestamp of the action, defaults to now")
    ] = None,
    action_name: Annotated[
        Optional[str], typer.Argument(help="name of the action")
    ] = "",
):
    """Adds an action to the tracker (alias for record run)."""
    record_run(task_name, actor, timestamp, action_name)


########################################
# record app
########################################


@record_app.command("run")
def record_run(
    task_name: Annotated[
        str, typer.Argument(help="name of the task to record an action for")
    ],
    actor: Annotated[
        Optional[str], typer.Argument(help="name of the person who did the action")
    ] = "",
    timestamp: Annotated[
        Optional[str], typer.Option(help="timestamp of the action, defaults to now")
    ] = None,
    action_name: Annotated[
        Optional[str], typer.Argument(help="name of the action")
    ] = "",
):
    """Records an action for a task."""
    ts = utils.parse_date(timestamp) if timestamp else None
    # ensure strings are plain str (typer may provide Optional[str])
    action_name = action_name or ""
    actor = actor or ""
    try:
        result = app.record_run(task_name, ts, action_name, actor)
    except Exception as e:
        # Map domain exceptions to friendly CLI errors
        rich.print(f":x: [red]{str(e)}[/red]")
        raise typer.Exit(code=GENERIC_FAIL_CODE)

    if result == ActionRecordResults.SUCCESS:
        rich.print(
            f":heavy_check_mark: [green]Successfully recorded action for task '{task_name}'[/green]"
        )
    else:
        rich.print(f":x: [red]Something went wrong[/red]")
        raise typer.Exit(code=GENERIC_FAIL_CODE)


########################################
# list app
########################################


@list_app.command("tasks", help="Prints a list of task")
def list_tasks_cli(
    overdue: Annotated[
        bool, typer.Option("--overdue", help="list only overdue tasks")
    ] = False,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="output format: table, json, or csv"),
    ] = OutputFormat.TABLE,
):
    if overdue:
        task_list = app.get_overdue_tasks()
        title = "Overdue Tasks"
    else:
        task_list = app.get_all_tasks()
        title = "Task List"

    if output == OutputFormat.JSON:
        _output_task_list_json(task_list)
    elif output == OutputFormat.CSV:
        _output_task_list_csv(task_list)
    else:
        _print_task_list_table(task_list, title=title)


@list_app.command("actions", help="Prints a list of actions")
def list_actions_cli(
    task_name: Annotated[
        Optional[str], typer.Argument(help="name of the task to filter actions")
    ] = None,
    output: Annotated[
        OutputFormat,
        typer.Option("--output", "-o", help="output format: table, json, or csv"),
    ] = OutputFormat.TABLE,
):
    if task_name:
        action_list = app.get_actions_for_task_filtered(task_name)
    else:
        action_list = app.get_all_actions()

    if output == OutputFormat.JSON:
        _output_action_list_json(action_list)
    elif output == OutputFormat.CSV:
        _output_action_list_csv(action_list)
    else:
        _print_action_list_table(action_list)


########################################
# get app
########################################


@get_app.command(
    "tasks",
    # no_args_is_help=True,
)
def get_tasks(
    name: Annotated[Optional[str], typer.Option()] = "",
    start_time: Annotated[Optional[str], typer.Option()] = None,
    end_time: Annotated[Optional[str], typer.Option()] = None,
):
    """get all tasks based on either a name or a time interval"""
    task_list = TaskLister()
    if name:
        task_list = app.get_tasks_by_name(name)
    elif start_time or end_time:
        start = utils.parse_date(start_time) if start_time else utils.parse_date("now")
        end = utils.parse_date(end_time) if end_time else utils.parse_date("now")
        task_list = app.get_tasks_by_time(start, end)

    if len(task_list) > 0:
        rich.print(f"found {len(task_list)} tasks")
        for t in task_list:
            rich.print(_rich_task(t))
    else:
        rich.print("No tasks found")


@get_app.command(
    "task",
    no_args_is_help=True,
)
def get_task(name: Annotated[str, typer.Argument()]):
    """get tasks by name"""
    task = app.get_task_by_name(name)
    if task is None:
        rich.print(f":x: [red]Task '{name}' not found[/red]")
        raise typer.Exit(code=GENERIC_FAIL_CODE)
    t = _rich_task(task)
    rich.print(t)


@get_app.command(
    "actions",
    no_args_is_help=True,
)
def get_actions(
    task_name: Annotated[str, typer.Argument(help="name of the task")],
):
    """get all actions for a task"""
    action_list = app.get_actions_for_task_filtered(task_name)
    if len(action_list) > 0:
        _print_action_list_table(action_list)
    else:
        rich.print(f"No actions found for task '{task_name}'")


@get_app.command(
    "action",
    no_args_is_help=True,
)
def get_action(
    task_name: Annotated[str, typer.Argument(help="name of the task")],
    action_ref: Annotated[
        Optional[str], typer.Argument(help="action timestamp or name to search for")
    ] = None,
):
    """get a specific action for a task"""
    if action_ref is None:
        rich.print(":x: [red]Must provide an action timestamp or name[/red]")
        raise typer.Exit(code=GENERIC_FAIL_CODE)

    # Try parsing as timestamp first
    try:
        timestamp = utils.parse_date(action_ref)
        action = app.get_action(task_name, timestamp)
        if action:
            rich.print(
                f"Actor: {action.actor}\nTimestamp: {utils.human_date_str(action.timestamp)}\nAction Name: {action.name}\nTask: {action.ref_task.name}"
            )
        else:
            rich.print(f":x: [red]Action not found[/red]")
            raise typer.Exit(code=GENERIC_FAIL_CODE)
    except Exception:
        # If timestamp parsing fails, try as action name
        action_list = app.get_actions_for_task_filtered(
            task_name, action_name=action_ref
        )
        if len(action_list) == 0:
            rich.print(f":x: [red]No action found with name '{action_ref}'[/red]")
            raise typer.Exit(code=GENERIC_FAIL_CODE)
        elif len(action_list) == 1:
            action = action_list[0]
            rich.print(
                f"Actor: {action.actor}\nTimestamp: {utils.human_date_str(action.timestamp)}\nAction Name: {action.name}\nTask: {action.ref_task.name}"
            )
        else:
            rich.print(
                f":x: [red]Multiple actions found with name '{action_ref}'. Please provide more specific criteria (timestamp).[/red]"
            )
            _print_action_list_table(action_list)
            raise typer.Exit(code=-10)


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
        rich.print(f":cross_mark: [red]Could not update '{task_name}'[/red]\n")
        raise typer.Exit(code=GENERIC_FAIL_CODE)


@edit_app.command(
    "action",
    no_args_is_help=True,
)
def edit_action(
    task_name: Annotated[str, typer.Argument(help="name of the task of the action")],
    action_ref: Annotated[
        Optional[str],
        typer.Argument(
            help="action timestamp or name to identify which action to edit"
        ),
    ] = None,
    new_actor: Annotated[Optional[str], typer.Argument(help="new actor name")] = None,
    new_timestamp: Annotated[
        Optional[str], typer.Argument(help="new timestamp for the action")
    ] = None,
    new_action_name: Annotated[
        Optional[str], typer.Argument(help="new name for the action")
    ] = None,
    new_task_name: Annotated[
        Optional[str], typer.Argument(help="new task name for the action")
    ] = None,
    interactive: Annotated[
        bool, typer.Option("-i", "--interactive", help="edit action interactively")
    ] = False,
):
    """Edits an action in the tracker"""
    if action_ref is None:
        rich.print(":x: [red]Must provide an action timestamp or name[/red]")
        raise typer.Exit(code=GENERIC_FAIL_CODE)

    try:
        # Get the original action for interactive mode
        actions = app.get_actions_for_task_filtered(task_name)
        original_action = None

        # Try to find by timestamp first
        try:
            timestamp = utils.parse_date(action_ref)
            original_action = app.get_action(task_name, timestamp)
        except Exception:
            # Try by name
            for action in actions:
                if action.name == action_ref:
                    original_action = action
                    break

        if original_action is None:
            rich.print(f":x: [red]Action not found[/red]")
            raise typer.Exit(code=GENERIC_FAIL_CODE)

        if interactive:
            logger.info("interactively editing action")
            if new_actor is None:
                new_actor = typer.prompt(
                    "New Actor", type=str, default=original_action.actor
                )
            if new_timestamp is None:
                new_timestamp = typer.prompt(
                    "New Timestamp",
                    type=str,
                    default=utils.human_date_str(original_action.timestamp),
                )
            if new_action_name is None:
                new_action_name = typer.prompt(
                    "New Action Name", type=str, default=original_action.name
                )
            if new_task_name is None:
                new_task_name = typer.prompt(
                    "New Task Name", type=str, default=original_action.ref_task.name
                )

        # Parse the new values
        parsed_timestamp = utils.parse_date(new_timestamp) if new_timestamp else None

        # Edit the action
        updated_action = app.edit_action(
            task_name,
            action_ref,
            new_actor=new_actor,
            new_timestamp=parsed_timestamp,
            new_action_name=new_action_name,
            new_task_name=new_task_name,
        )

        if updated_action is not None:
            rich.print(f":heavy_check_mark: [green]Action updated successfully[/green]")
            rich.print(
                f"Actor: {updated_action.actor}\nTimestamp: {utils.human_date_str(updated_action.timestamp)}\nAction Name: {updated_action.name}\nTask: {updated_action.ref_task.name}"
            )
        else:
            rich.print(f":x: [red]Could not update action[/red]")
            raise typer.Exit(code=GENERIC_FAIL_CODE)
    except ValueError as e:
        rich.print(f":x: [red]{str(e)}[/red]")
        raise typer.Exit(code=GENERIC_FAIL_CODE)


########################################
# delete app
########################################


@delete_app.command("task")
def delete_task(
    task_name: Annotated[str, typer.Argument(help="name of the task to delete")],
):
    """Deletes a task."""
    try:
        result = app.delete_task(task_name)
    except Exception as e:
        rich.print(f":x: [red]{str(e)}[/red]")
        raise typer.Exit(code=GENERIC_FAIL_CODE)

    if result == TaskRecordResults.SUCCESS:
        rich.print(
            f":heavy_check_mark: [green]Successfully deleted task '{task_name}'[/green]"
        )
    else:
        rich.print(
            f":x: [red]Could not delete task '{task_name}'. It might not exist or have actions that depend on it.[/red]"
        )
        raise typer.Exit(code=GENERIC_FAIL_CODE)


@delete_app.command("action")
def delete_action(
    task_name: Annotated[
        str, typer.Argument(help="name of the task of the action to delete")
    ],
    start_time: Annotated[
        Optional[str], typer.Option(help="start time of the actions to delete")
    ] = None,
    end_time: Annotated[
        Optional[str], typer.Option(help="end time of the actions to delete")
    ] = None,
    action_name: Annotated[
        Optional[str], typer.Option(help="name of the action to delete")
    ] = None,
):
    """Deletes one or more actions."""
    if not start_time and not end_time and not action_name:
        rich.print(
            "No action to delete. Please provide a time range or an action name."
        )
        raise typer.Exit()

    start = utils.parse_date(start_time) if start_time else None
    end = utils.parse_date(end_time) if end_time else None

    deleted_count = app.delete_action(task_name, start, end, action_name)

    if deleted_count > 0:
        rich.print(
            f":heavy_check_mark: [green]Successfully deleted {deleted_count} action(s) for task '{task_name}'[/green]"
        )
    else:
        rich.print(
            f":x: [red]No actions were deleted for task '{task_name}'. They might not exist or the provided criteria didn't match.[/red]"
        )


########################################
# report app
########################################


@report_app.command("overdue")
def report_overdue(
    at: Annotated[
        Optional[str],
        typer.Option("--at", help="check for overdues at the given timestamp"),
    ] = None,
):
    """Lists overdue tasks"""
    when = utils.parse_date(at) if at else None
    overdue_tasks = app.get_overdue_tasks(when)
    _print_task_list_table(overdue_tasks, title="Overdue Tasks")


@report_app.command("next")
def report_next(
    run: Annotated[Optional[str], typer.Argument()] = None,
    for_task: Annotated[
        Optional[str], typer.Option("--for", help="get next run for a specific task")
    ] = None,
    at: Annotated[
        Optional[str],
        typer.Option("--at", help="check next runs at the given timestamp"),
    ] = None,
):
    """Gets next runs for tasks"""
    target_task = for_task
    if not target_task and run and run != "run":
        target_task = run
    when = utils.parse_date(at) if at else None
    next_runs = app.get_next_runs(target_task, when)

    title = "Next Scheduled Task" if target_task else "Next Scheduled Tasks"
    table = Table(title=title)
    table.add_column("Task", justify="left", no_wrap=True)
    table.add_column("Next Run", justify="right", style="green")

    for task, next_run in next_runs:
        table.add_row(task.name, utils.human_date_str(next_run))

    console = Console()
    console.print(table)


def show_dashboard() -> None:
    """Print the default overview for an existing tracker database."""
    rich.print("[bold]overdue tasks[/bold]")
    list_tasks_cli(overdue=True)
    rich.print("[bold]next expected tasks[/bold]")
    report_next()


@report_app.command("tasks")
def report_tasks(
    run: Annotated[Optional[str], typer.Argument()] = None,
    at: Annotated[
        Optional[str],
        typer.Option("--at", help="list tasks for a specific time period"),
    ] = None,
    between: Annotated[
        Optional[tuple[str, str]],
        typer.Option("--between", help="list tasks between two timestamps"),
    ] = None,
):
    """Lists tasks based on time criteria"""
    if at:
        start, end = utils.parse_partial_timestamp(at)
        tasks = app.get_tasks_by_time(start, end)
        _print_task_list_table(tasks)
    elif between and len(between) == 2:
        start = utils.parse_date(between[0])
        end = utils.parse_date(between[1])
        tasks = app.get_tasks_by_time(start, end)
        _print_task_list_table(tasks)
    else:
        tasks = app.get_all_tasks()
        _print_task_list_table(tasks)


@report_app.command("actions")
def report_actions(
    run: Annotated[Optional[str], typer.Argument()] = None,
    at: Annotated[
        Optional[str],
        typer.Option("--at", help="list actions for a specific time period"),
    ] = None,
    between: Annotated[
        Optional[tuple[str, str]],
        typer.Option("--between", help="list actions between two timestamps"),
    ] = None,
    for_task: Annotated[
        Optional[str], typer.Option("--for", help="filter actions for a specific task")
    ] = None,
):
    """Lists actions based on criteria"""
    if at:
        start, end = utils.parse_partial_timestamp(at)
        actions = app.get_actions_by_time(start, end, for_task)
        _print_action_list_table(actions)
    elif between and len(between) == 2:
        start = utils.parse_date(between[0])
        end = utils.parse_date(between[1])
        actions = app.get_actions_by_time(start, end, for_task)
        _print_action_list_table(actions)
    else:
        start = datetime.min.replace(tzinfo=UTC)
        end = datetime.max.replace(tzinfo=UTC)
        actions = app.get_actions_by_time(start, end, for_task)
        _print_action_list_table(actions)


########################################
# footer
########################################

if __name__ == "__main__":
    rich.print("[red]please run the main file[/red]", file=sys.stderr)
    raise SystemExit(0)
