# cli implements the typer app

import typer
import rich
import sys
from core import *
from maintenance_tracker import *

logger = logging.getLogger(__name__)


add_app = typer.Typer(
    no_args_is_help=True, help="adds a Task or an Action to the tracker"
)
edit_app = typer.Typer(
    no_args_is_help=True,
)
record_app = typer.Typer(
    no_args_is_help=True,
)
list_app = typer.Typer(
    no_args_is_help=True,
)
get_app = typer.Typer(
    no_args_is_help=True,
)
edit_app = typer.Typer(
    no_args_is_help=True,
)
delete_app = typer.Typer(
    no_args_is_help=True,
)
report_app = typer.Typer(
    no_args_is_help=True,
)


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
    print(f"Adding task {name}")
    print(f"{start_time = }")
    print(f"{interval = }")
    print(f"{description = }")
    raise NotImplementedError()


@add_app.command("action")
def add_action():
    print("add task command!")


def record():
    print("record command!")


def list():
    print("list command!")


def get():
    print("get command!")


def edit():
    print("edit command!")


def delete():
    print("delete command!")


if __name__ == "__main__":
    rich.print("[red]please run the main file[/red]", file=sys.stderr)
    raise SystemExit(0)
