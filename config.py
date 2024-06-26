# gets or defines the app directory and makes a Config available to the user
import json
import logging
from pathlib import Path
from typing import Any

import typer

logger = logging.getLogger(__name__)

APP_NAME = "mtnt"
CONFIG_FILE_NAME = "mtnt_config.json"
DEFAULT_CONFIG_ENTRIES = {"data_dir": ".", "debug_logging": False}


class Configuration:
    """Holds configuration for the app"""

    app_dir: str  # these configs are not saved
    verbose: bool  # these configs are not saved
    saved_configs: dict
    initialized: bool = False

    def __init__(self):
        self.saved_configs = DEFAULT_CONFIG_ENTRIES

    def init_config(self, config_dir: str | None = None, verbose: bool = False) -> None:
        self.verbose = verbose

        if config_dir is None:
            self.app_dir = typer.get_app_dir(APP_NAME)
        else:
            self.app_dir = config_dir

        config_file_path = Path(self.app_dir) / Path(CONFIG_FILE_NAME)
        logger.debug(f"{config_file_path = }")

        try:
            logger.debug(f"loading config from {config_file_path}")
            with config_file_path.open("r", encoding="utf8") as conf_fp:
                self.saved_configs = json.load(conf_fp)
            logger.info(f"loaded config file {self.saved_configs = }")

        except FileNotFoundError:
            # new config
            self.saved_configs = DEFAULT_CONFIG_ENTRIES
            logger.info(
                f"could not find file, saving default config {self.saved_configs = }"
            )
            try:
                with config_file_path.open("w", encoding="utf8") as conf_fp:
                    json.dump(
                        obj=self.saved_configs,
                        fp=conf_fp,
                        indent=4,
                    )
            except FileExistsError:
                logger.critical(
                    f"Unable to create the config file {config_file_path}. "
                )

        data_dir = Path(self.data_dir)
        if not data_dir.is_absolute():
            logger.debug(
                "data_dir from config file is not absolute... using app_dir as base directory"
            )
            data_dir = self.app_dir / data_dir

        self.saved_configs["data_dir"] = data_dir

        data_dir.mkdir(parents=True, exist_ok=True)

        logging.info(
            f"initialized configuration - {self.app_dir = }, {self.verbose = }\n"
            f"{self.saved_configs = }\n"
        )
        self.initialized = True

    def __getattr__(self, name: str) -> Any:
        if name in DEFAULT_CONFIG_ENTRIES.keys():
            return self.saved_configs.get(name)
        raise AttributeError(name=name)

    def __repr__(self) -> str:
        rep: str = ""
        rep += "initialized " if self.initialized else "un-initialized "
        rep = f"config.Configuration()\n"
        for k, v in self.__dict__.items():
            rep += f"    {k} = {v}\n"
        return rep


config = Configuration()
