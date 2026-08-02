import csv
import datetime
import io
import json
from datetime import UTC
from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest
from typer.testing import CliRunner

from main import typer_app
from core import Task, TaskLister, Action
from maintenance_tracker import ActionRecordResults, TaskRecordResults, ActionLister
import config as config_module

import cli as cli_mod
import typer

runner = CliRunner()


@pytest.fixture(autouse=True)
def reset_global_config_state():
    """Resets the global DEFAULT_CONFIG_ENTRIES to prevent cross-test pollution."""
    config_module.DEFAULT_CONFIG_ENTRIES["data_dir"] = "."
    config_module.DEFAULT_CONFIG_ENTRIES["debug_logging"] = False


@pytest.fixture
def mock_app():
    # Patch app in cli module, as that's where the logic is called
    with patch("cli.app") as mock_app:
        yield mock_app


@pytest.fixture
def mock_rich_console():
    with patch("rich.console.Console") as mock_console:
        yield mock_console


@pytest.fixture
def tmp_config_dir(tmp_path):
    return tmp_path / "config"


def invoke_app(args, config_dir, input=None):
    """Helper to invoke app with config dir before subcommand"""
    # args is like ["add", "task", ...]
    # We want ["--config-dir", str(config_dir)] + args
    full_args = ["--config-dir", str(config_dir)] + args
    return runner.invoke(typer_app, full_args, input=input)


def test_add_task_success(mock_app, tmp_config_dir):
    """Test adding a task successfully."""
    mock_app.register_task.return_value = None

    result = invoke_app(["add", "task", "MyTask", "now", "1d"], tmp_config_dir)

    assert result.exit_code == 0
    assert "Successfully created task" in result.stdout
    mock_app.register_task.assert_called_once()

    # Verify the task object created
    created_task = mock_app.register_task.call_args[0][0]
    assert created_task.name == "MyTask"
    assert created_task.interval == datetime.timedelta(days=1)


def test_add_task_failure(mock_app, tmp_config_dir):
    """Test failure when adding a task raises an exception."""
    mock_app.register_task.side_effect = Exception("Test Error")

    result = invoke_app(["add", "task", "MyTask"], tmp_config_dir)

    assert result.exit_code == 1
    assert "something went wrong" in result.stdout
    assert "Test Error" in result.stdout


def test_add_task_interactive(mock_app, tmp_config_dir):
    """Test interactive task creation."""
    mock_app.register_task.return_value = None

    # Inputs for the prompts: Name, Start Time, Interval, Description
    inputs = "InteractiveTask\nnow\n1w\nTest Description\n"

    # Can't use helper easily with input, manual invoke
    result = runner.invoke(
        typer_app,
        ["--config-dir", str(tmp_config_dir), "add", "task", "-i"],
        input=inputs,
    )

    assert result.exit_code == 0
    assert "InteractiveTask" in result.stdout

    created_task = mock_app.register_task.call_args[0][0]
    assert created_task.name == "InteractiveTask"
    assert created_task.description == "Test Description"


def test_add_action_alias(mock_app, tmp_config_dir):
    """Test 'add action' alias for recording a run."""
    mock_app.record_run.return_value = ActionRecordResults.SUCCESS

    result = invoke_app(
        ["add", "action", "MyTask", "--timestamp", "2023-01-01"], tmp_config_dir
    )

    assert result.exit_code == 0
    assert "Successfully recorded action" in result.stdout
    mock_app.record_run.assert_called_once()


def test_record_run_success(mock_app, tmp_config_dir):
    """Test successfully recording a run."""
    mock_app.record_run.return_value = ActionRecordResults.SUCCESS

    result = invoke_app(["record", "run", "MyTask"], tmp_config_dir)

    assert result.exit_code == 0
    assert "Successfully recorded action" in result.stdout


def test_record_run_failure(mock_app, tmp_config_dir):
    """Test failure in recording a run."""
    mock_app.record_run.return_value = ActionRecordResults.FAILURE

    result = invoke_app(["record", "run", "MyTask"], tmp_config_dir)

    assert result.exit_code == 1
    assert "Something went wrong" in result.stdout


def test_list_tasks(mock_app, tmp_config_dir):
    """Test listing tasks."""
    t1 = Task("Task1", description="Desc1")
    t2 = Task("Task2", interval=datetime.timedelta(days=1))
    mock_app.get_all_tasks.return_value = TaskLister([t1, t2])

    result = invoke_app(["list", "tasks"], tmp_config_dir)

    assert result.exit_code == 0
    assert "Task1" in result.stdout
    assert "Task2" in result.stdout
    assert "Desc1" in result.stdout


def test_list_tasks_overdue(mock_app, tmp_config_dir):
    """Test listing overdue tasks."""
    mock_app.get_overdue_tasks.return_value = TaskLister([Task("OverdueTask")])

    result = invoke_app(["list", "tasks", "--overdue"], tmp_config_dir)

    assert result.exit_code == 0
    assert "OverdueTask" in result.stdout
    mock_app.get_overdue_tasks.assert_called_once()


def test_list_tasks_json_output(mock_app, tmp_config_dir):
    """Task lists can be emitted as machine-readable JSON."""
    task = Task(
        "Task1",
        description="Desc1",
        start_time=datetime.datetime(2024, 1, 2, 10, 0, tzinfo=UTC),
        interval=datetime.timedelta(days=7),
    )
    mock_app.get_all_tasks.return_value = TaskLister([task])

    result = invoke_app(["list", "tasks", "--output", "json"], tmp_config_dir)

    assert result.exit_code == 0
    assert json.loads(result.stdout) == [
        {
            "name": "Task1",
            "description": "Desc1",
            "start_time": "2024-01-02T10:00:00+00:00",
            "interval": "7 days, 0:00:00",
        }
    ]


def test_list_actions_csv_output(mock_app, tmp_config_dir):
    """Action lists can be emitted as CSV to standard output."""
    task = Task("Task1")
    action = Action(
        timestamp=datetime.datetime(2024, 1, 2, 10, 0, tzinfo=UTC),
        ref_task=task,
        name="Completed",
        actor="Alex",
    )
    mock_app.get_all_actions.return_value = ActionLister([action])

    result = invoke_app(["list", "actions", "--output", "csv"], tmp_config_dir)

    assert result.exit_code == 0
    assert list(csv.reader(io.StringIO(result.stdout))) == [
        ["Task", "Actor", "Timestamp", "Action Name"],
        ["Task1", "Alex", "2024-01-02T10:00:00+00:00", "Completed"],
    ]


def test_list_rejects_unknown_output_format(mock_app, tmp_config_dir):
    """Output format values are constrained to the documented formats."""
    result = invoke_app(["list", "tasks", "--output", "yaml"], tmp_config_dir)

    assert result.exit_code == 2
    assert "Invalid value" in result.stdout


def test_no_args_shows_help_when_database_does_not_exist(mock_app, tmp_config_dir):
    """The first run keeps the existing no-argument help behavior."""
    result = invoke_app([], tmp_config_dir)

    assert result.exit_code == 0
    assert "Usage:" in result.stdout
    mock_app.get_overdue_tasks.assert_not_called()
    mock_app.get_next_runs.assert_not_called()


def test_no_args_shows_dashboard_when_database_exists(mock_app, tmp_config_dir):
    """An existing database opens the overdue and next-task overview."""
    tmp_config_dir.mkdir(parents=True)
    (tmp_config_dir / "task_list.json").write_text("[]", encoding="utf8")
    overdue_task = Task("OverdueTask")
    next_task = Task("NextTask")
    mock_app.get_overdue_tasks.return_value = TaskLister([overdue_task])
    mock_app.get_next_runs.return_value = [
        (next_task, datetime.datetime(2024, 1, 2, 10, 0, tzinfo=UTC))
    ]

    result = invoke_app([], tmp_config_dir)

    assert result.exit_code == 0
    assert "overdue tasks" in result.stdout
    assert "OverdueTask" in result.stdout
    assert "next expected tasks" in result.stdout
    assert "NextTask" in result.stdout
    mock_app.get_overdue_tasks.assert_called_once_with()
    mock_app.get_next_runs.assert_called_once_with(None, None)


def test_list_actions_all(mock_app, tmp_config_dir):
    """Test listing all actions."""
    t1 = Task("Task1")
    a1 = Action(timestamp=datetime.datetime.now(), ref_task=t1, name="Action1")
    mock_app.get_all_actions.return_value = ActionLister([a1])

    result = invoke_app(["list", "actions"], tmp_config_dir)

    assert result.exit_code == 0
    assert "Action1" in result.stdout
    assert "Task1" in result.stdout
    mock_app.get_all_actions.assert_called_once()


def test_list_actions_filtered(mock_app, tmp_config_dir):
    """Test listing actions filtered by task."""
    t1 = Task("Task1")
    a1 = Action(timestamp=datetime.datetime.now(), ref_task=t1, name="Action1")
    mock_app.get_actions_for_task_filtered.return_value = ActionLister([a1])

    result = invoke_app(["list", "actions", "Task1"], tmp_config_dir)

    assert result.exit_code == 0
    assert "Action1" in result.stdout
    mock_app.get_actions_for_task_filtered.assert_called_with("Task1")


def test_get_tasks_by_name(mock_app, tmp_config_dir):
    """Test getting tasks by name."""
    mock_app.get_tasks_by_name.return_value = TaskLister([Task("FoundTask")])

    result = invoke_app(["get", "tasks", "--name", "Found"], tmp_config_dir)

    assert result.exit_code == 0
    assert "FoundTask" in result.stdout
    mock_app.get_tasks_by_name.assert_called_with("Found")


def test_get_tasks_by_time(mock_app, tmp_config_dir):
    """Test getting tasks by time interval."""
    mock_app.get_tasks_by_time.return_value = TaskLister([Task("TimeTask")])

    result = invoke_app(["get", "tasks", "--start-time", "2023-01-01"], tmp_config_dir)

    assert result.exit_code == 0
    assert "TimeTask" in result.stdout
    mock_app.get_tasks_by_time.assert_called_once()


def test_get_tasks_none_found(mock_app, tmp_config_dir):
    """Test output when no tasks are found."""
    mock_app.get_tasks_by_name.return_value = TaskLister([])

    result = invoke_app(["get", "tasks", "--name", "Nothing"], tmp_config_dir)

    assert result.exit_code == 0
    assert "No tasks found" in result.stdout


def test_get_single_task(mock_app, tmp_config_dir):
    """Test getting a single task by exact name."""
    mock_app.get_task_by_name.return_value = Task("SingleTask")

    result = invoke_app(["get", "task", "SingleTask"], tmp_config_dir)

    assert result.exit_code == 0
    assert "SingleTask" in result.stdout
    mock_app.get_task_by_name.assert_called_with("SingleTask")


def test_edit_task_success(mock_app, tmp_config_dir):
    """Test editing a task successfully."""
    original = Task("Original")
    mock_app.get_task_by_name.return_value = original
    mock_app.edit_task.return_value = Task("Renamed")

    result = invoke_app(
        ["edit", "task", "Original", "--rename", "Renamed"], tmp_config_dir
    )

    assert result.exit_code == 0
    assert "updated successfully" in result.stdout
    mock_app.edit_task.assert_called_once()
    assert mock_app.edit_task.call_args[0][0] == original
    assert mock_app.edit_task.call_args[0][1] == {"name": "Renamed"}


def test_edit_task_not_found(mock_app, tmp_config_dir):
    """Test editing a non-existent task."""
    mock_app.get_task_by_name.return_value = None

    result = invoke_app(["edit", "task", "Missing"], tmp_config_dir)

    assert result.exit_code == 1
    assert "not found" in result.stdout


def test_edit_task_failure(mock_app, tmp_config_dir):
    """Test failure during task update."""
    mock_app.get_task_by_name.return_value = Task("Exists")
    mock_app.edit_task.return_value = None

    result = invoke_app(["edit", "task", "Exists", "--rename", "Fail"], tmp_config_dir)

    assert result.exit_code == 1
    assert "Could not update" in result.stdout


def test_delete_task_success(mock_app, tmp_config_dir):
    """Test deleting a task successfully."""
    mock_app.delete_task.return_value = TaskRecordResults.SUCCESS

    result = invoke_app(["delete", "task", "ToDelete"], tmp_config_dir)

    assert result.exit_code == 0
    assert "Successfully deleted task" in result.stdout


def test_delete_task_failure(mock_app, tmp_config_dir):
    """Test failing to delete a task."""
    mock_app.delete_task.return_value = TaskRecordResults.FAILURE

    result = invoke_app(["delete", "task", "FailDelete"], tmp_config_dir)

    assert result.exit_code == 1
    assert "Could not delete task" in result.stdout


def test_delete_action_success(mock_app, tmp_config_dir):
    """Test deleting actions successfully."""
    mock_app.delete_action.return_value = 5

    result = invoke_app(
        ["delete", "action", "TaskName", "--action-name", "ActionName"], tmp_config_dir
    )

    assert result.exit_code == 0
    assert "Successfully deleted 5 action(s)" in result.stdout


def test_delete_action_no_criteria(mock_app, tmp_config_dir):
    """Test delete action without criteria."""
    result = invoke_app(["delete", "action", "TaskName"], tmp_config_dir)

    assert result.exit_code == 0
    assert "No action to delete" in result.stdout


def test_report_overdue(mock_app, tmp_config_dir):
    """Test report overdue command."""
    mock_app.get_overdue_tasks.return_value = TaskLister([Task("OverdueTask")])
    result = invoke_app(["report", "overdue", "--at", "2024-01-01"], tmp_config_dir)
    assert result.exit_code == 0
    assert "OverdueTask" in result.stdout
    mock_app.get_overdue_tasks.assert_called_once()


def test_report_next(mock_app, tmp_config_dir):
    """Test report next command."""
    from datetime import datetime, UTC

    task = Task("NextTask")
    mock_app.get_next_runs.return_value = [
        (task, datetime(2024, 1, 2, 10, 0, tzinfo=UTC))
    ]
    result = invoke_app(["report", "next", "--for", "NextTask"], tmp_config_dir)
    assert result.exit_code == 0
    assert "NextTask" in result.stdout
    mock_app.get_next_runs.assert_called_once()


def test_report_tasks(mock_app, tmp_config_dir):
    """Test report tasks command with --at and --between."""
    mock_app.get_tasks_by_time.return_value = TaskLister([Task("ReportTask")])

    # Test --at
    result = invoke_app(["report", "tasks", "--at", "2024-05"], tmp_config_dir)
    assert result.exit_code == 0
    assert "ReportTask" in result.stdout

    # Test --between
    result_bt = invoke_app(
        ["report", "tasks", "--between", "2024-01-01", "2024-01-31"], tmp_config_dir
    )
    assert result_bt.exit_code == 0
    assert "ReportTask" in result_bt.stdout


def test_report_actions(mock_app, tmp_config_dir):
    """Test report actions command."""
    mock_app.get_actions_by_time.return_value = ActionLister([])

    result = invoke_app(
        ["report", "actions", "--at", "2024-05", "--for", "MyTask"], tmp_config_dir
    )
    assert result.exit_code == 0
    mock_app.get_actions_by_time.assert_called()

    # Test report actions without options
    result_default = invoke_app(["report", "actions"], tmp_config_dir)
    assert result_default.exit_code == 0


def test_edit_task_interactive_and_partial(mock_app, tmp_config_dir):
    """Test interactive task editing and partial field updates."""
    original = Task(
        "Original",
        start_time=datetime.datetime(2024, 1, 1, tzinfo=UTC),
        interval=datetime.timedelta(days=1),
        description="Desc",
    )
    mock_app.get_task_by_name.return_value = original
    mock_app.edit_task.return_value = Task("Original", description="NewDesc")

    # Partial update with positional arguments
    result = invoke_app(
        ["edit", "task", "Original", "2024-01-02", "2days", "NewDesc"], tmp_config_dir
    )
    assert result.exit_code == 0
    mock_app.edit_task.assert_called()

    # Interactive update with prompts
    result_interactive = invoke_app(
        ["edit", "task", "Original", "-i"],
        tmp_config_dir,
        input="2024-01-02\n2days\nNewDesc\nRenamed\n",
    )
    assert result_interactive.exit_code == 0


def test_delete_action_zero_deleted(mock_app, tmp_config_dir):
    """Test delete action output when 0 actions are deleted."""
    mock_app.delete_action.return_value = 0
    result = invoke_app(
        ["delete", "action", "TaskName", "--action-name", "ActionName"], tmp_config_dir
    )
    assert result.exit_code == 0
    assert "No actions were deleted" in result.stdout


def test_report_next_positional_task(mock_app, tmp_config_dir):
    """Test report next with positional task argument."""
    task = Task("PositionalTask")
    mock_app.get_next_runs.return_value = [
        (task, datetime.datetime(2024, 1, 2, 10, 0, tzinfo=UTC))
    ]
    result = invoke_app(["report", "next", "PositionalTask"], tmp_config_dir)
    assert result.exit_code == 0
    assert "PositionalTask" in result.stdout
    mock_app.get_next_runs.assert_called_with("PositionalTask", None)


def test_report_tasks_default(mock_app, tmp_config_dir):
    """Test report tasks command without criteria."""
    mock_app.get_all_tasks.return_value = TaskLister([Task("AllTask")])
    result = invoke_app(["report", "tasks"], tmp_config_dir)
    assert result.exit_code == 0
    assert "AllTask" in result.stdout


def test_report_next_accepts_literal_run(mock_app, tmp_config_dir):
    mock_app.get_next_runs.return_value = []

    result = invoke_app(["report", "next", "run"], tmp_config_dir)

    assert result.exit_code == 0
    mock_app.get_next_runs.assert_called_once_with(None, None)


def test_report_actions_between_filters_by_task(mock_app, tmp_config_dir):
    task = Task("TaskName")
    mock_app.get_actions_by_time.return_value = ActionLister(
        [Action(datetime.datetime(2024, 1, 2, tzinfo=UTC), task, "completed")]
    )

    result = invoke_app(
        [
            "report",
            "actions",
            "--between",
            "2024-01-01",
            "2024-01-03",
            "--for",
            "TaskName",
        ],
        tmp_config_dir,
    )

    assert result.exit_code == 0
    assert "completed" in result.stdout
    assert mock_app.get_actions_by_time.call_args.args[2] == "TaskName"


# Additional CLI unit tests for internal helper functions
import io
import sys
import cli as cli_mod
import typer


def test_output_task_list_csv(capsys):
    t = Task(
        "CSVTask",
        description="d",
        start_time=datetime.datetime(2024, 1, 1, tzinfo=UTC),
        interval=datetime.timedelta(days=1),
    )
    tl = TaskLister([t])
    cli_mod._output_task_list_csv(tl)
    out = capsys.readouterr().out
    assert "Name,Description,Start Time,Interval" in out
    assert "CSVTask" in out


def test_output_action_list_json(capsys):
    t = Task("T")
    a = Action(
        timestamp=datetime.datetime(2024, 1, 1, tzinfo=UTC),
        ref_task=t,
        name="act",
        actor="me",
    )
    al = ActionLister([a])
    cli_mod._output_action_list_json(al)
    out = capsys.readouterr().out
    import json as _json

    data = _json.loads(out)
    assert isinstance(data, list)
    assert data[0]["task"] == "T"
    assert data[0]["action_name"] == "act"


def test_print_action_list_table(capsys):
    t = Task("TableTask")
    a = Action(
        timestamp=datetime.datetime(2024, 1, 2, tzinfo=UTC),
        ref_task=t,
        name="doit",
        actor="me",
    )
    al = ActionLister([a])
    cli_mod._print_action_list_table(al)
    out = capsys.readouterr().out
    assert "doit" in out
    assert "TableTask" in out


def test_get_actions_calls_and_no_actions(monkeypatch, capsys):
    # no actions
    monkeypatch.setattr(
        cli_mod.app, "get_actions_for_task_filtered", lambda name: ActionLister([])
    )
    cli_mod.get_actions("no-task")
    out = capsys.readouterr().out
    assert "No actions found" in out

    # with actions
    called = {"v": False}

    def fake_print(al):
        called["v"] = True

    monkeypatch.setattr(cli_mod, "_print_action_list_table", fake_print)
    monkeypatch.setattr(
        cli_mod.app,
        "get_actions_for_task_filtered",
        lambda name: ActionLister(
            [
                Action(
                    datetime.datetime(2024, 1, 2, tzinfo=UTC), Task(name="X"), name="a"
                )
            ]
        ),
    )
    cli_mod.get_actions("any")
    assert called["v"] is True


def test_get_action_by_timestamp_and_by_name(monkeypatch, capsys):
    t = Task("Tk")
    a = Action(
        timestamp=datetime.datetime(2024, 3, 3, tzinfo=UTC),
        ref_task=t,
        name="aname",
        actor="actor",
    )
    # timestamp path
    monkeypatch.setattr(cli_mod.app, "get_action", lambda task_name, ts: a)
    cli_mod.get_action("Tk", a.timestamp.isoformat())
    out = capsys.readouterr().out
    assert "Actor: actor" in out

    # name path multiple
    monkeypatch.setattr(cli_mod.app, "get_action", lambda task_name, ts: None)
    monkeypatch.setattr(
        cli_mod.app,
        "get_actions_for_task_filtered",
        lambda task_name, action_name=None: ActionLister([a, a]),
    )
    with pytest.raises(typer.Exit):
        cli_mod.get_action("Tk", "aname")


def test_edit_action_success_and_not_found(monkeypatch, capsys):
    t = Task("Tedit")
    a = Action(
        timestamp=datetime.datetime(2024, 4, 4, tzinfo=UTC),
        ref_task=t,
        name="old",
        actor="oldactor",
    )
    # case: not found
    monkeypatch.setattr(
        cli_mod.app, "get_actions_for_task_filtered", lambda name: ActionLister([])
    )
    with pytest.raises(typer.Exit):
        cli_mod.edit_action("Tedit", "old")

    # case: found and updated
    monkeypatch.setattr(
        cli_mod.app, "get_actions_for_task_filtered", lambda name: ActionLister([a])
    )
    monkeypatch.setattr(cli_mod.app, "get_action", lambda name, ts: a)
    updated = Action(
        timestamp=datetime.datetime(2025, 5, 5, tzinfo=UTC),
        ref_task=t,
        name="new",
        actor="newactor",
    )
    monkeypatch.setattr(cli_mod.app, "edit_action", lambda tn, ar, **kwargs: updated)
    cli_mod.edit_action("Tedit", a.timestamp.isoformat(), new_actor="newactor")
    out = capsys.readouterr().out
    assert "Action updated successfully" in out
