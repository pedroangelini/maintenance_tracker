import logging

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(levelname)s: %(name)s - %(message)s",
)

import typer
from cli import *
from config import config, APP_NAME

logger = logging.getLogger(__name__)

app = typer.Typer(
    no_args_is_help=True,
    help="mtnt: a simple cli maintenance tracker for your repetitive tasks",
    name="mtnt: the simple Maintenance Tracker",
)

@typer_app.callback()
def main(
    verbose: bool = False,
    config_dir: Annotated[
        str, typer.Option(help="directory to store configs")
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


if __name__ == "__main__":
    app()
