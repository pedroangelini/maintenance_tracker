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


def _rich_action(a: Action) -> str:
    ret_str = f"Action for Task: [bold]{a.ref_task.name}[/bold]\n"
    ret_str += f"Timestamp:   {utils.human_date_str(a.timestamp)}\n"
    if a.name:
        ret_str += f"Action Name: {a.name}\n"
    if a.actor:
        ret_str += f"Actor:       {a.actor}\n"
    if a.description:
        ret_str += f"Description: [italic]{a.description}[/italic]\n"
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


def _print_action_list_table(action_list: ActionLister) -> None:
    table = rich.table.Table(title="Action List")

    table.add_column("Task", justify="left", no_wrap=True)
    table.add_column("Action Name")
    table.add_column("Timestamp", justify="right", style="green")
    table.add_column("Actor", justify="right", style="blue")

    for a in action_list:
        table.add_row(
            a.ref_task.name,
            a.name,
            utils.human_date_str(a.timestamp),
            a.actor,
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
def add_action(
    task_name: Annotated[str, typer.Argument(help="name of the task to record an action for")],
    timestamp: Annotated[
        Optional[str], typer.Option(help="timestamp of the action, defaults to now")
    ] = None,
    action_name: Annotated[
        Optional[str], typer.Argument(help="name of the action")
    ] = "",
    actor: Annotated[
        Optional[str], typer.Argument(help="name of the person who did the action")
    ] = "",
):
    """Adds an action to the tracker (alias for record run)."""
    record_run(task_name, timestamp, action_name, actor)


########################################
# record app
########################################


@record_app.command("run")
def record_run(
    task_name: Annotated[str, typer.Argument(help="name of the task to record an action for")],
    timestamp: Annotated[
        Optional[str], typer.Option(help="timestamp of the action, defaults to now")
    ] = None,
    action_name: Annotated[
        Optional[str], typer.Argument(help="name of the action")
    ] = "",
    actor: Annotated[
        Optional[str], typer.Argument(help="name of the person who did the action")
    ] = "",
):
    """Records an action for a task."""
    ts = utils.parse_date(timestamp) if timestamp else None
    result = app.record_run(task_name, ts, action_name, actor)
    if result == ActionRecordResults.SUCCESS:
        rich.print(f":heavy_check_mark: [green]Successfully recorded action for task '{task_name}'[/green]")
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
):
    if overdue:
        task_list = app.get_overdue_tasks()
    else:
        task_list = app.get_all_tasks()
    _print_task_list_table(task_list)


@list_app.command("actions", help="Prints a list of actions")
def list_actions_cli(
    task_name: Annotated[
        Optional[str], typer.Argument(help="name of the task to filter actions")
    ] = None,
):
    if task_name:
        action_list = app.get_actions_for_task_filtered(task_name)
    else:
        action_list = app.get_all_actions()
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
    t = _rich_task(app.get_task_by_name(name))
    rich.print(t)


@get_app.command("actions")
def get_actions_cli(
    task_name: Annotated[str, typer.Argument(help="name of the task")],
    action_name: Annotated[Optional[str], typer.Option(help="filter by action name")] = None,
    start_time: Annotated[Optional[str], typer.Option(help="filter by start time")] = None,
    end_time: Annotated[Optional[str], typer.Option(help="filter by end time")] = None,
):
    """Prints detailed information for actions of a specific task."""
    start = utils.parse_date(start_time) if start_time else None
    end = utils.parse_date(end_time) if end_time else None
    actions = app.get_actions_for_task_filtered(task_name, start, end, action_name)
    if not actions:
        rich.print(f"No actions found for task '{task_name}'")
        return
    rich.print(f"found {len(actions)} actions")
    for a in actions:
        rich.print(_rich_action(a))


@get_app.command("action", no_args_is_help=True)
def get_action_cli(
    task_name: Annotated[str, typer.Argument(help="name of the task")],
    search_criteria: Annotated[str, typer.Argument(help="timestamp or name of the action")],
):
    """Prints details of a single action. Returns error -10 if multiple actions match."""
    ts = None
    try:
        ts = utils.parse_date(search_criteria)
    except utils.DateParseError:
        pass
    actions = (
        app.get_actions_for_task_filtered(task_name, start_time=ts, end_time=ts)
        if ts
        else app.get_actions_for_task_filtered(task_name, action_name=search_criteria)
    )
    if not actions:
        rich.print(
            f":x: [red]No action found for task '{task_name}' matching '{search_criteria}'[/red]"
        )
        raise typer.Exit(code=GENERIC_FAIL_CODE)
    if len(actions) > 1:
        rich.print(f":x: [red]Multiple actions found matching '{search_criteria}':[/red]")
        _print_action_list_table(actions)
        raise typer.Exit(code=-10)
    rich.print(_rich_action(actions[0]))


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


@edit_app.command("action", no_args_is_help=True)
def edit_action_cli(
    task_name: Annotated[
        str, typer.Argument(help="name of the task of the action to edit")
    ],
    search_criteria: Annotated[
        str, typer.Argument(help="timestamp or name of the action to search for")
    ],
    new_task_name: Annotated[Optional[str], typer.Option("--task", help="new task name")] = None,
    new_timestamp: Annotated[Optional[str], typer.Option("--timestamp", help="new timestamp")] = None,
    new_name: Annotated[Optional[str], typer.Option("--name", help="new name")] = None,
    new_actor: Annotated[Optional[str], typer.Option("--actor", help="new actor")] = None,
    new_description: Annotated[
        Optional[str], typer.Option("--description", help="new description")
    ] = None,
    interactive: Annotated[
        bool, typer.Option("-i", "--interactive", help="edit interactively")
    ] = False,
):
    """Edits an action in the tracker."""
    ts = None
    try:
        ts = utils.parse_date(search_criteria)
    except utils.DateParseError:
        pass
    actions = (
        app.get_actions_for_task_filtered(task_name, start_time=ts, end_time=ts)
        if ts
        else app.get_actions_for_task_filtered(task_name, action_name=search_criteria)
    )
    if not actions:
        rich.print(f":x: [red]No action found[/red]")
        raise typer.Exit(code=GENERIC_FAIL_CODE)
    if len(actions) > 1:
        rich.print(f":x: [red]Multiple actions found[/red]")
        _print_action_list_table(actions)
        raise typer.Exit(code=-10)
    orig = actions[0]
    if interactive:
        new_task_name = typer.prompt("New Task", default=orig.ref_task.name)
        new_timestamp = typer.prompt("New Timestamp", default=str(orig.timestamp))
        new_name = typer.prompt("New Name", default=orig.name)
        new_actor = typer.prompt("New Actor", default=orig.actor)
        new_description = typer.prompt("New Description", default=orig.description)
    changes = {}
    if new_task_name:
        changes["task_name"] = new_task_name
    if new_timestamp:
        changes["timestamp"] = utils.parse_date(new_timestamp)
    if new_name:
        changes["name"] = new_name
    if new_actor:
        changes["actor"] = new_actor
    if new_description:
        changes["description"] = new_description
    updated = app.edit_action(orig, changes)
    if updated:
        rich.print(
            f":heavy_check_mark: [green]Action updated successfully[/green]\n{_rich_action(updated)}"
        )
    else:
        rich.print(f":x: [red]Could not update action[/red]")
        raise typer.Exit(code=GENERIC_FAIL_CODE)
        


########################################
# delete app
########################################


@delete_app.command("task")
def delete_task(
    task_name: Annotated[str, typer.Argument(help="name of the task to delete")],
):
    """Deletes a task."""
    result = app.delete_task(task_name)
    if result == TaskRecordResults.SUCCESS:
        rich.print(f":heavy_check_mark: [green]Successfully deleted task '{task_name}'[/green]")
    else:
        rich.print(f":x: [red]Could not delete task '{task_name}'. It might not exist or have actions that depend on it.[/red]")
        raise typer.Exit(code=GENERIC_FAIL_CODE)


@delete_app.command("action")
def delete_action(
    task_name: Annotated[str, typer.Argument(help="name of the task of the action to delete")],
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
        rich.print("No action to delete. Please provide a time range or an action name.")
        raise typer.Exit()

    start = utils.parse_date(start_time) if start_time else None
    end = utils.parse_date(end_time) if end_time else None

    deleted_count = app.delete_action(task_name, start, end, action_name)

    if deleted_count > 0:
        rich.print(f":heavy_check_mark: [green]Successfully deleted {deleted_count} action(s) for task '{task_name}'[/green]")
    else:
        rich.print(f":x: [red]No actions were deleted for task '{task_name}'. They might not exist or the provided criteria didn't match.[/red]")



########################################
# report app
########################################

########################################
# footer
########################################

if __name__ == "__main__":
    rich.print("[red]please run the main file[/red]", file=sys.stderr)
    raise SystemExit(0)
