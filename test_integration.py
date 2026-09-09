import pytest
import subprocess
from pathlib import Path
from maintenance_tracker import MaintenanceTracker, Action, Task, ActionRecordResults
from repository import (
    FileTaskRepository,
    FileActionRepository,
    TaskListPersister,
    ActionListPersister,
)
from core import TaskLister, ActionLister
from datetime import datetime, UTC, timedelta
import json

import pytest


PROJECT_ROOT = Path(__file__).parent


def run_cli(config_dir: Path, *args: str, input_text: str | None = None):
    return subprocess.run(
        ["uv", "run", "python", "main.py", "--config-dir", str(config_dir), *args],
        cwd=PROJECT_ROOT,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def assert_cli_success(result, *expected_output: str):
    assert result.returncode == 0, result.stderr or result.stdout
    assert result.stderr == ""
    for expected in expected_output:
        assert expected in result.stdout


def assert_cli_failure(result, expected_output: str):
    assert result.returncode != 0
    assert expected_output in result.stdout or expected_output in result.stderr


# The top-level help must expose every command group documented for users.
def test_manual_help_lists_commands(tmp_path):
    result = run_cli(tmp_path, "--help")

    assert_cli_success(result, "add", "record", "list", "get", "edit", "delete", "report")


# Task creation, lookup, and overdue listing must persist across CLI processes.
def test_manual_task_creation_lookup_and_overdue_listing(tmp_path):
    assert_cli_success(
        run_cli(
            tmp_path,
            "add",
            "task",
            "Water plants",
            "2024-01-01 09:00",
            "7 days",
            "Water indoor plants",
        ),
        "Successfully created task",
        "Water plants",
    )
    assert_cli_success(
        run_cli(
            tmp_path,
            "add",
            "task",
            "Replace filter",
            "2030-01-01 09:00",
            "0",
            "One-time task",
        ),
        "Successfully created task",
        "Replace filter",
    )

    task_list = run_cli(tmp_path, "list", "tasks")
    assert_cli_success(task_list, "Water plants", "Replace filter", "One-time task")
    assert "7 days" in task_list.stdout
    assert "repeating" not in task_list.stdout.lower() or "Replace filter" in task_list.stdout

    assert_cli_success(run_cli(tmp_path, "get", "task", "Water plants"), "Water plants")
    assert_cli_success(run_cli(tmp_path, "get", "tasks", "--name", "Water"), "Water plants")
    assert_cli_success(run_cli(tmp_path, "list", "tasks", "--overdue"), "Water plants")


# Interactive editing should change every field except the existing task name.
def test_manual_interactive_task_creation_and_edit(tmp_path):
    create = run_cli(
        tmp_path,
        "add",
        "task",
        "-i",
        input_text="Interactive task\nnow\n1 day\nCreated interactively\n",
    )
    assert_cli_success(create, "Task Name", "Successfully created task", "Interactive task")

    edit = run_cli(
        tmp_path,
        "edit",
        "task",
        "Interactive task",
        "-i",
        input_text="2024-02-01 09:00\n2 days\nEdited interactively\nInteractive task\n",
    )
    assert_cli_success(edit, "updated successfully", "Interactive task", "Edited interactively")
    assert "New Start Time" in edit.stdout
    assert "New Periodicity" in edit.stdout
    assert "New Description" in edit.stdout
    assert "New Name" in edit.stdout

    persisted = run_cli(tmp_path, "get", "task", "Interactive task")
    assert_cli_success(persisted, "Interactive task", "Edited interactively", "2 days", "Feb 01 2024")


# Actions must be recordable, reportable, listable, and deletable by name.
def test_manual_action_record_report_and_name_delete(tmp_path):
    assert_cli_success(
        run_cli(tmp_path, "add", "task", "Water plants", "2024-01-01 09:00", "7 days"),
        "Successfully created task",
    )
    assert_cli_success(
        run_cli(
            tmp_path,
            "record",
            "run",
            "Water plants",
            "Alex",
            "--timestamp",
            "2024-01-08 09:15",
            "weekly watering",
        ),
        "Successfully recorded action",
    )
    assert_cli_success(
        run_cli(
            tmp_path,
            "add",
            "action",
            "Water plants",
            "Sam",
            "--timestamp",
            "2024-01-15 09:00",
            "second watering",
        ),
        "Successfully recorded action",
    )

    all_actions = run_cli(tmp_path, "list", "actions")
    assert_cli_success(all_actions, "weekly watering", "second watering", "Alex", "Sam")
    assert_cli_success(run_cli(tmp_path, "list", "actions", "Water plants"), "weekly watering", "second watering")
    assert_cli_success(
        run_cli(tmp_path, "report", "actions", "--at", "2024-01", "--for", "Water plants"),
        "weekly watering",
        "second watering",
    )

    assert_cli_success(
        run_cli(tmp_path, "delete", "action", "Water plants", "--action-name", "weekly watering"),
        "deleted",
    )
    remaining = run_cli(tmp_path, "list", "actions", "Water plants")
    assert_cli_success(remaining, "second watering")
    assert "weekly watering" not in remaining.stdout


# Time-range deletion must remove only the matching action and allow re-recording.
def test_manual_action_time_range_delete_and_rerecord(tmp_path):
    assert_cli_success(run_cli(tmp_path, "add", "task", "Water plants"), "Successfully created task")
    assert_cli_success(
        run_cli(
            tmp_path,
            "record",
            "run",
            "Water plants",
            "Sam",
            "--timestamp",
            "2024-01-15 09:00",
            "second watering",
        ),
        "Successfully recorded action",
    )
    assert_cli_success(
        run_cli(
            tmp_path,
            "delete",
            "action",
            "Water plants",
            "--start-time",
            "2024-01-15 00:00",
            "--end-time",
            "2024-01-15 23:59",
        ),
        "deleted",
    )
    empty = run_cli(tmp_path, "list", "actions", "Water plants")
    assert_cli_success(empty, "Action List")
    assert "second watering" not in empty.stdout
    assert_cli_success(
        run_cli(
            tmp_path,
            "record",
            "run",
            "Water plants",
            "Sam",
            "--timestamp",
            "2024-01-15 09:00",
            "second watering",
        ),
        "Successfully recorded action",
    )


# Renaming preserves action relationships, while dependent deletion is blocked.
def test_manual_rename_reports_and_dependency_delete(tmp_path):
    assert_cli_success(
        run_cli(tmp_path, "add", "task", "Water plants", "2024-01-01 09:00", "7 days"),
        "Successfully created task",
    )
    assert_cli_success(
        run_cli(
            tmp_path,
            "record",
            "run",
            "Water plants",
            "Sam",
            "--timestamp",
            "2024-01-15 09:00",
            "second watering",
        ),
        "Successfully recorded action",
    )
    assert_cli_success(
        run_cli(tmp_path, "edit", "task", "Water plants", "--rename", "Water houseplants"),
        "updated successfully",
    )
    assert_cli_success(run_cli(tmp_path, "get", "task", "Water houseplants"), "Water houseplants")
    assert_cli_success(
        run_cli(tmp_path, "report", "next", "--for", "Water houseplants", "--at", "2024-01-16"),
        "Water houseplants",
    )
    assert_cli_success(
        run_cli(tmp_path, "report", "tasks", "--between", "2024-01-01", "2024-01-31"),
        "Water houseplants",
    )
    assert_cli_success(
        run_cli(tmp_path, "report", "overdue", "--at", "2024-02-01"),
        "Water houseplants",
    )

    blocked = run_cli(tmp_path, "delete", "task", "Water houseplants")
    assert_cli_failure(blocked, "action")
    assert_cli_success(
        run_cli(tmp_path, "delete", "action", "Water houseplants", "--action-name", "second watering"),
        "deleted",
    )
    assert_cli_success(run_cli(tmp_path, "delete", "task", "Water houseplants"), "deleted")
    final_tasks = run_cli(tmp_path, "list", "tasks")
    final_actions = run_cli(tmp_path, "list", "actions")
    assert_cli_success(final_tasks, "Task List")
    assert_cli_success(final_actions, "Action List")
    assert "Water houseplants" not in final_tasks.stdout


# Invalid commands must explain failures without corrupting saved data.
def test_manual_errors_and_final_persistence(tmp_path):
    assert_cli_success(run_cli(tmp_path, "add", "task", "Replace filter", "2030-01-01 09:00", "0"), "created")
    assert_cli_failure(run_cli(tmp_path, "add", "task", "", "now", "1 day"), "something went wrong")
    assert_cli_failure(run_cli(tmp_path, "record", "run", "does not exist"), "not found")

    no_criteria = run_cli(tmp_path, "delete", "action", "Replace filter")
    assert_cli_success(no_criteria, "No action to delete")

    assert_cli_success(run_cli(tmp_path, "list", "tasks"), "Replace filter")
    final_actions = run_cli(tmp_path, "list", "actions")
    assert_cli_success(final_actions, "Action List")
    assert "second watering" not in final_actions.stdout


@pytest.fixture(scope="function")
def task1():
    return Task(
        name="my first task",
        description="a description for my task1",
        start_time=datetime(2023, 12, 24, 17, 32, tzinfo=UTC),
        interval=timedelta(minutes=60),
    )


@pytest.fixture(scope="function")
def action1_t1(task1: Task):
    return Action(
        datetime(2024, 1, 1, tzinfo=UTC), task1, "ran task1 on new year day", "me"
    )


@pytest.fixture(scope="function")
def action2_t1(task1: Task):
    return Action(
        datetime(2024, 1, 2, tzinfo=UTC),
        task1,
        "ran task1 on the second of the year, 6 AM",
        "me",
    )


# Persisted tasks and actions should reload into a new tracker instance.
def test_load_via_persister(tmp_path):
    # prepare task and action lists and save them using repository persisters
    t1 = Task(name="t_loaded")
    a1 = Action(timestamp=datetime(2024, 5, 5, tzinfo=UTC), ref_task=t1, name="act")

    task_list = TaskLister([t1])
    action_list = ActionLister([a1])

    tlp = TaskListPersister(task_list, dirname=str(tmp_path))
    alp = ActionListPersister(action_list, dirname=str(tmp_path))

    tlp._remove_file()
    alp._remove_file()
    tlp.save()
    alp.save()

    # initialize tracker with load=True pointing at the tmp_path
    mt = MaintenanceTracker(load=True, save_dir=str(tmp_path))

    # ensure loaded data is present
    assert any(t.name == "t_loaded" for t in mt.task_list)
    assert any(a.name == "act" for a in mt.action_list)


# An end-only time filter should return actions up to the specified cutoff.
def test_get_actions_for_task_with_end_only(task1):
    mt = MaintenanceTracker()
    mt.register_task(task1)
    # create actions around the cutoff
    a_old = Action(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC), ref_task=task1, name="old"
    )
    a_new = Action(
        timestamp=datetime(2024, 6, 1, tzinfo=UTC), ref_task=task1, name="new"
    )
    mt.record_run(a_old)
    mt.record_run(a_new)

    # request actions with only end_time (should set start to datetime.min internally)
    end_time = datetime(2024, 2, 1, tzinfo=UTC)
    actions = mt.get_actions_for_task(task1, start_time=None, end_time=end_time)
    assert len(actions) == 1
    assert actions[0].name == "old"


# Editing an action should support changing its timestamp and referenced task.
def test_edit_action_change_timestamp_and_task(task1):
    mt = MaintenanceTracker()
    mt.register_task(task1)
    a = Action(timestamp=datetime(2024, 7, 7, tzinfo=UTC), ref_task=task1, name="x")
    mt.record_run(a)

    # change timestamp
    ts = a.timestamp.isoformat()
    new_ts = datetime(2025, 1, 1, tzinfo=UTC)
    edited = mt.edit_action(task1.name, ts, new_timestamp=new_ts)
    assert edited is not None
    assert edited.timestamp == new_ts

    # change task to a newly created task
    new_task = Task(name="other")
    mt.register_task(new_task)
    edited2 = mt.edit_action(task1.name, new_ts.isoformat(), new_task_name="other")
    assert edited2 is not None
    assert edited2.ref_task.name == "other"


# A failed action replacement should report no edited action to the caller.
def test_edit_action_failure_branch(monkeypatch, task1):
    mt = MaintenanceTracker()
    mt.register_task(task1)
    a = Action(timestamp=datetime(2024, 8, 8, tzinfo=UTC), ref_task=task1, name="z")
    mt.record_run(a)

    # force record_run to return FAILURE to exercise the 'return None' branch
    monkeypatch.setattr(
        MaintenanceTracker,
        "record_run",
        lambda self, new_action: ActionRecordResults.FAILURE,
    )

    res = mt.edit_action(task1.name, a.timestamp.isoformat(), new_actor="nobody")
    assert res is None
