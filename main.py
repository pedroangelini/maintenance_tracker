# main creates the tracker, deals with configs, and starts the typer app

import typer
from cli import *


app = typer.Typer(
    no_args_is_help=True,
    help="mtnt: a simple cli maintenance tracker for your repetitive tasks",
    name="mtnt: the simple Maintenance Tracker",
)

app.add_typer(add_app, name="add")
app.add_typer(edit_app, name="edit")
app.add_typer(record_app, name="record")
app.add_typer(list_app, name="list")
app.add_typer(get_app, name="get")
app.add_typer(edit_app, name="edit")
app.add_typer(delete_app, name="delete")
app.add_typer(report_app, name="report")


if __name__ == "__main__":
    app()
