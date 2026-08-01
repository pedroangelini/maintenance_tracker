import json
from pathlib import Path

import pytest

import config as config_module
from config import (
    CONFIG_FILE_NAME,
    DEFAULT_CONFIG_ENTRIES,
    Configuration,
)


@pytest.fixture(autouse=True)
def reset_global_config_state():
    """Resets the global DEFAULT_CONFIG_ENTRIES to prevent cross-test pollution.
    The Configuration class stores a reference to this dict and mutates it.
    """
    config_module.DEFAULT_CONFIG_ENTRIES["data_dir"] = "."
    config_module.DEFAULT_CONFIG_ENTRIES["debug_logging"] = False


@pytest.fixture
def config():
    """Returns a fresh Configuration instance."""
    return Configuration()


def test_configuration_initial_state(config: Configuration):
    """Tests the default state of a new Configuration object."""
    assert not config.initialized
    assert config.saved_configs["data_dir"] == "."
    assert config.saved_configs["debug_logging"] is False


def test_getattr_success():
    """Tests that __getattr__ correctly retrieves existing config values."""
    config = Configuration()
    # Assign a new dict to avoid mutating the global DEFAULT_CONFIG_ENTRIES
    config.saved_configs = {"data_dir": "/test/dir", "debug_logging": False}
    assert config.data_dir == "/test/dir"


def test_getattr_failure(config: Configuration):
    """Tests that __getattr__ raises an AttributeError for non-existent keys."""
    with pytest.raises(AttributeError):
        _ = config.non_existent_key


def test_repr(config: Configuration):
    """Tests the string representation of the Configuration object."""
    representation = repr(config)
    assert "Configuration" in representation
    assert "saved_configs" in representation


def test_init_config_no_file_found(tmp_path: Path):
    """
    Tests initialization when no config file exists.
    """
    config = Configuration()
    test_config_dir = tmp_path / "app_config_new"
    test_config_dir.mkdir()

    config.init_config(config_dir=str(test_config_dir))

    config_file_path = test_config_dir / CONFIG_FILE_NAME
    assert config_file_path.exists()

    with config_file_path.open("r", encoding="utf8") as f:
        content = json.load(f)

    assert content["debug_logging"] is False
    # init_config resolves "." to the absolute path of the config_dir
    assert config.data_dir == test_config_dir.resolve()
    assert config.initialized


def test_init_config_loads_existing_file(tmp_path: Path):
    """
    Tests initialization when a config file already exists.
    """
    config = Configuration()
    test_config_dir = tmp_path / "app_config_load"
    test_config_dir.mkdir()
    config_file_path = test_config_dir / CONFIG_FILE_NAME

    existing_config_data = {"data_dir": "data_subdir", "debug_logging": True}
    config_file_path.write_text(json.dumps(existing_config_data))

    config.init_config(config_dir=str(test_config_dir))

    expected_data_dir = (test_config_dir / "data_subdir").resolve()
    assert config.data_dir == expected_data_dir
    assert config.debug_logging is True
    assert config.initialized


def test_init_config_relative_data_dir(tmp_path: Path):
    """
    Tests resolution of relative data_dir.
    """
    config = Configuration()
    test_config_dir = tmp_path / "app_config_rel_res"
    test_config_dir.mkdir()
    config_file_path = test_config_dir / CONFIG_FILE_NAME

    existing_config_data = {"data_dir": "my_data", "debug_logging": False}
    config_file_path.write_text(json.dumps(existing_config_data))

    config.init_config(config_dir=str(test_config_dir))

    expected_path = (test_config_dir / "my_data").resolve()
    assert config.data_dir == expected_path
    assert config.initialized


def test_init_config_with_explicit_dir(tmp_path: Path):
    """
    Tests providing an explicit config_dir.
    """
    config = Configuration()
    explicit_dir = tmp_path / "explicit_test_dir"
    explicit_dir.mkdir()

    # Use a clean dict for JSON serialization to avoid TypeError from polluted global state
    clean_config = {"data_dir": ".", "debug_logging": False}
    (explicit_dir / CONFIG_FILE_NAME).write_text(json.dumps(clean_config))

    config.init_config(config_dir=str(explicit_dir))

    assert config.app_dir == str(explicit_dir)
    assert config.initialized
