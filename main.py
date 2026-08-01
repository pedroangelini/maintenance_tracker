# main creates logging, configures and starts the typer app

import os
import sys
from pathlib import Path
import logging

logging.basicConfig(
    stream=sys.stdout,
    level=logging.WARN,
    format="%(levelname)s: %(name)s - %(message)s",
)

import typer
from typing_extensions import Annotated

from cli import *
from config import config, APP_NAME
from app import tracker
from repository import DEFAULT_TASK_LIST_FILE

logger = logging.getLogger(__name__)

typer_app = typer.Typer(
    no_args_is_help=False,
    invoke_without_command=True,
    # help=,
    name="mtnt: the simple Maintenance Tracker",
)

typer_app.add_typer(add_app, name="add")
typer_app.add_typer(edit_app, name="edit")
typer_app.add_typer(record_app, name="record")
typer_app.add_typer(list_app, name="list")
typer_app.add_typer(get_app, name="get")
typer_app.add_typer(edit_app, name="edit")
typer_app.add_typer(delete_app, name="delete")
typer_app.add_typer(report_app, name="report")


@typer_app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = False,
    config_dir: Annotated[
        Optional[str], typer.Option(help="directory to store configs")
    ] = typer.get_app_dir(APP_NAME),
):
    "mtnt: a simple cli maintenance tracker for your repetitive tasks"
    global config

    config.init_config(config_dir=config_dir, verbose=verbose)

    if config.verbose:
        logging.basicConfig(level=max(logging.INFO, logger.level))
        logger.info("entering verbose mode")

    if config.debug_logging:
        logging.basicConfig(level=max(logging.DEBUG, logger.level))
        logger.info("entering debug mode")

    dir_path = Path(config.app_dir)

    logger.info(f"config directory: {dir_path}")

    logger.info(f"loading tracker from path: {Path(config.data_dir)}")
    # Check before loading: loading a tracker initializes its JSON files when they
    # do not yet exist.  This preserves the first-run help behavior.
    database_exists = (Path(config.data_dir) / DEFAULT_TASK_LIST_FILE).is_file()

    app.tracker = MaintenanceTracker(load=True, save_dir=config.data_dir)
    logger.debug(f"{tracker}")

    if ctx.invoked_subcommand is None:
        if database_exists:
            show_dashboard()
        else:
            typer.echo(ctx.get_help())


if __name__ == "__main__":
    typer_app()
