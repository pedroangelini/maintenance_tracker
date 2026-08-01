import pytest
from unittest.mock import patch
import logging
from datetime import datetime, timedelta, UTC

# import all of app to be able to mock app.tracker
import app
from core import (
    Action,
    ActionLister,
    Task,
    TaskLister,
    TaskWithSameNameError,
)
from maintenance_tracker import (
    MaintenanceTracker,
    Ordering,
    ActionRecordResults,
    TaskRecordResults,
)

logging.basicConfig(level=logging.DEBUG)


# Fixtures from test_core.py
@pytest.fixture(scope="function")
def task1():
    """A simple task for testing"""
    return Task(
        name="my first task",
        description="a description for my task1",
        start_time=datetime(2023, 12, 24, 17, 32, tzinfo=UTC),
        interval=timedelta(minutes=60),
    )


@pytest.fixture(scope="function")
def task2():
    """A second task for testing, different from the first"""
    return Task(
        name="my second task",
        description="a description for my task2",
        start_time=datetime(2023, 12, 25, 17, 32, tzinfo=UTC),
        interval=timedelta(minutes=30),
    )


@pytest.fixture(scope="function")
def task3():
    """A third task for testing, different from the first 2"""
    return Task(
        name="my third task",
        description="adding this one #3",
        start_time=datetime(2023, 12, 25, 17, 5, tzinfo=UTC),
        interval=timedelta(minutes=15),
    )


@pytest.fixture(scope="function")
def action1_t1(task1: Task):
    return Action(
        ref_task=task1,
        timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        name="ran task1 on new year day",
        actor="me",
    )


@pytest.fixture(scope="function")
def action2_t1(task1: Task):
    return Action(
        ref_task=task1,
        timestamp=datetime(2024, 1, 2, 6, 0, tzinfo=UTC),
        name="ran task1 on the second of the year, 6 AM",
        actor="me",
    )


@pytest.fixture(scope="function")
def action3_t1(task1: Task):
    return Action(
        ref_task=task1,
        timestamp=datetime(2024, 1, 3, 0, 0, tzinfo=UTC),
        name="ran task1 on day 3",
        actor="me",
    )


# Autouse fixture to reset the tracker for each test
@pytest.fixture(autouse=True)
def reset_tracker(tmp_path):
    """Resets the global tracker before each test and sets a temporary save directory."""
    # This fixture ensures each test is isolated by creating a new tracker instance
    # that saves its data to a unique temporary directory provided by pytest's tmp_path.
    app.tracker = MaintenanceTracker(save_dir=str(tmp_path))
    yield


def test_register_task(task1):
    app.register_task(task1)
    assert task1 in app.tracker.task_list
    # Verify that the task is saved by creating a new tracker instance and loading
    # from the same temporary directory. This confirms the persistence side effect.
    new_tracker = MaintenanceTracker(
        load=True, save_dir=app.tracker.task_list_saver.dirname
    )
    assert task1 in new_tracker.task_list


def test_get_task_by_name(task1):
    app.register_task(task1)
    found_task = app.get_task_by_name(task1.name)
    assert found_task == task1

    not_found_task = app.get_task_by_name("non-existent task")
    assert not_found_task is None


def test_get_tasks_by_name(task1, task2):
    task3 = Task(name="another task")
    app.register_task(task1)
    app.register_task(task2)
    app.register_task(task3)

    found_tasks = app.get_tasks_by_name("my")
    assert task1 in found_tasks
    assert task2 in found_tasks
    assert task3 not in found_tasks
    assert len(found_tasks) == 2


def test_get_tasks_by_time(task1, task2, action1_t1, action2_t1):
    app.register_task(task1)
    app.register_task(task2)

    t1_from_tracker = app.get_task_by_name(task1.name)
    action1 = action1_t1.replace({"ref_task": t1_from_tracker})
    action2 = action2_t1.replace({"ref_task": t1_from_tracker})
    app.tracker.record_run(action1)
    app.tracker.record_run(action2)

    start = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    end = datetime(2024, 1, 2, 12, 0, tzinfo=UTC)
    tasks = app.get_tasks_by_time(start, end)
    assert len(tasks) == 1
    assert task1.name == tasks[0].name
    assert task2.name != tasks[0].name


def test_get_all_tasks(task1, task2):
    app.register_task(task1)
    app.register_task(task2)

    all_tasks = app.get_all_tasks()
    assert task1 in all_tasks
    assert task2 in all_tasks
    assert len(all_tasks) == 2


def test_edit_task_with_name_change(task1):
    app.register_task(task1)
    task_from_tracker = app.get_task_by_name(task1.name)
    assert task_from_tracker is not None
    app.record_run(task_from_tracker.name, timestamp=datetime.now(UTC))
    original_action = app.tracker.action_list[0]

    changes = {"name": "a new name", "description": "new description"}
    new_task = app.edit_task(task_from_tracker, changes)
    assert new_task is not None
    assert new_task.name == "a new name"
    assert new_task.description == "new description"
    assert app.get_task_by_name(task1.name) is None
    assert app.get_task_by_name("a new name") is not None

    # Check that any actions associated with the old task are reassigned to the new one.
    assert len(app.tracker.action_list) == 1
    updated_action = app.tracker.action_list[0]
    assert updated_action.ref_task.name == "a new name"
    assert updated_action.timestamp == original_action.timestamp

    # Verify persistence by loading from the temp directory to ensure all changes,
    # including the task name update and action reassignment, were saved.
    new_tracker = MaintenanceTracker(
        load=True, save_dir=app.tracker.task_list_saver.dirname
    )
    assert new_tracker.task_list.get_task_by_name("a new name") == new_task
    assert len(new_tracker.action_list) == 1
    assert new_tracker.action_list[0].ref_task.name == "a new name"


def test_edit_task_fails_without_name_change(task1):
    from errors import DuplicateTaskError

    app.register_task(task1)
    task_from_tracker = app.get_task_by_name(task1.name)
    assert task_from_tracker is not None

    changes = {"description": "new description"}
    with pytest.raises(DuplicateTaskError):
        app.edit_task(task_from_tracker, changes)


def test_get_actions_for_task_filtered(task1, action1_t1, action2_t1, action3_t1):
    app.register_task(task1)
    t1 = app.get_task_by_name(task1.name)
    a1 = action1_t1.replace({"ref_task": t1, "name": "run1"})
    a2 = action2_t1.replace({"ref_task": t1, "name": "run2"})
    a3 = action3_t1.replace({"ref_task": t1, "name": "run1"})
    app.tracker.record_run(a1)
    app.tracker.record_run(a2)
    app.tracker.record_run(a3)

    # Test filter by action_name
    actions = app.get_actions_for_task_filtered(task1.name, action_name="run1")
    assert len(actions) == 2
    assert a1 in actions
    assert a3 in actions

    # Test filter by time
    start = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    end = datetime(2024, 1, 2, 12, 0, tzinfo=UTC)
    actions = app.get_actions_for_task_filtered(
        task1.name, start_time=start, end_time=end
    )
    assert len(actions) == 1
    assert a2 in actions

    # Test with non-existent task
    actions = app.get_actions_for_task_filtered("non-existent", action_name="run1")
    assert len(actions) == 0


def test_record_run(task1):
    app.register_task(task1)

    result = app.record_run(
        task1.name, action_name="test run", timestamp=datetime.now(UTC)
    )
    assert result == ActionRecordResults.SUCCESS
    assert len(app.tracker.action_list) == 1
    action = app.tracker.action_list[0]
    assert action.ref_task == task1
    assert action.name == "test run"

    # Verify persistence by loading from the temp directory and checking
    # if the new action was saved correctly.
    new_tracker = MaintenanceTracker(
        load=True, save_dir=app.tracker.task_list_saver.dirname
    )
    assert len(new_tracker.action_list) == 1
    assert new_tracker.action_list[0] == action


def test_record_run_no_task():
    from errors import TaskNotFoundError

    with patch("app.tracker.save") as mock_save:
        with pytest.raises(TaskNotFoundError):
            app.record_run("non-existent task")
        mock_save.assert_not_called()


def test_get_overdue_tasks(task1):
    app.register_task(task1)
    with patch("app.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2025, 1, 1, tzinfo=UTC)
        overdue_tasks = app.get_overdue_tasks()
        assert task1 in overdue_tasks


def test_delete_task(task1):
    app.register_task(task1)
    result = app.delete_task(task1.name)
    assert result == TaskRecordResults.SUCCESS
    assert task1 not in app.tracker.task_list

    # Verify persistence by loading from the temp directory to ensure the task
    # was actually removed from the saved data.
    new_tracker = MaintenanceTracker(
        load=True, save_dir=app.tracker.task_list_saver.dirname
    )
    assert task1 not in new_tracker.task_list


def test_delete_task_not_found():
    from errors import TaskNotFoundError

    with patch("app.tracker.save") as mock_save:
        with pytest.raises(TaskNotFoundError):
            app.delete_task("non-existent task")
        mock_save.assert_not_called()


def test_delete_action(task1, action1_t1, action2_t1):
    app.register_task(task1)
    t1 = app.get_task_by_name(task1.name)
    a1 = action1_t1.replace({"ref_task": t1})
    a2 = action2_t1.replace({"ref_task": t1})
    app.tracker.record_run(a1)
    app.tracker.record_run(a2)

    assert len(app.tracker.action_list) == 2

    # Delete one action by time range
    start = datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    end = datetime(2024, 1, 2, 0, 0, tzinfo=UTC)
    deleted_count = app.delete_action(task1.name, start_time=start, end_time=end)
    assert deleted_count == 1
    assert len(app.tracker.action_list) == 1
    assert a2 in app.tracker.action_list

    # Verify persistence by loading from the temp directory to ensure the action
    # was actually removed from the saved data.
    new_tracker = MaintenanceTracker(
        load=True, save_dir=app.tracker.task_list_saver.dirname
    )
    assert len(new_tracker.action_list) == 1
    assert new_tracker.action_list[0] == a2


def test_get_action(task1):
    app.register_task(task1)
    timestamp = datetime(2025, 1, 1, tzinfo=UTC)

    app.record_run(task1.name, timestamp=timestamp)

    found_action = app.get_action(task1.name, timestamp)
    assert found_action is not None
    assert found_action.timestamp == timestamp
    assert found_action.ref_task.name == task1.name

    assert app.get_action("non-existent task", timestamp) is None
    assert app.get_action(task1.name, datetime(2026, 1, 1, tzinfo=UTC)) is None


def test_get_overdue_tasks_with_at(task1):
    # task1 has start_time 2024-01-01 10:00, interval 1 day
    app.register_task(task1)
    # Check overdue at 2024-01-03 without recorded actions
    at_time = datetime(2024, 1, 3, 12, 0, tzinfo=UTC)
    overdue = app.get_overdue_tasks(at=at_time)
    assert len(overdue) == 1
    assert overdue[0].name == task1.name


def test_get_next_runs(task1):
    app.register_task(task1)
    at_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    next_runs = app.get_next_runs(for_task=task1.name, at=at_time)
    assert len(next_runs) == 1
    t, next_run = next_runs[0]
    assert t.name == task1.name
    assert next_run > at_time

    # Test all tasks
    all_next_runs = app.get_next_runs(at=at_time)
    assert len(all_next_runs) == 1


def test_get_actions_by_time_filtered(task1, action1_t1, action2_t1):
    app.register_task(task1)
    t1 = app.get_task_by_name(task1.name)
    a1 = action1_t1.replace({"ref_task": t1})
    a2 = action2_t1.replace({"ref_task": t1})
    app.tracker.record_run(a1)
    app.tracker.record_run(a2)

    start = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    end = datetime(2024, 1, 2, 12, 0, tzinfo=UTC)

    actions = app.get_actions_by_time(start, end, task_name=task1.name)
    assert len(actions) == 1
    assert actions[0] == a2

    actions_nonexistent = app.get_actions_by_time(start, end, task_name="nonexistent")
    assert len(actions_nonexistent) == 0


def test_get_all_actions(task1, action1_t1):
    app.register_task(task1)
    t1 = app.get_task_by_name(task1.name)
    a1 = action1_t1.replace({"ref_task": t1})
    app.tracker.record_run(a1)
    all_actions = app.get_all_actions()
    assert len(all_actions) == 1
    assert all_actions[0] == a1


def test_edit_task_failure(task1):
    app.register_task(task1)
    t1 = app.get_task_by_name(task1.name)
    from errors import DanglingActionsError

    with patch(
        "app.tracker.delete_task", side_effect=DanglingActionsError("cannot delete")
    ):
        with pytest.raises(DanglingActionsError):
            app.edit_task(t1, {"name": "NewName"})


def test_get_actions_for_task_filtered_start_only_and_end_only(task1, action1_t1):
    app.register_task(task1)
    t1 = app.get_task_by_name(task1.name)
    a1 = action1_t1.replace({"ref_task": t1})
    app.tracker.record_run(a1)

    # start only
    actions_start = app.get_actions_for_task_filtered(
        task1.name, start_time=datetime(2023, 1, 1, tzinfo=UTC)
    )
    assert len(actions_start) == 1

    # end only
    actions_end = app.get_actions_for_task_filtered(
        task1.name, end_time=datetime(2025, 1, 1, tzinfo=UTC)
    )
    assert len(actions_end) == 1


def test_record_run_default_timestamp(task1):
    app.register_task(task1)
    res = app.record_run(task1.name, timestamp=None)
    assert res == ActionRecordResults.SUCCESS
    assert len(app.tracker.action_list) == 1


def test_get_actions_by_time_without_task_filter(task1, action1_t1, action2_t1):
    app.register_task(task1)
    registered_task = app.get_task_by_name(task1.name)
    app.tracker.record_run(action1_t1.replace({"ref_task": registered_task}))
    app.tracker.record_run(action2_t1.replace({"ref_task": registered_task}))

    actions = app.get_actions_by_time(
        datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        datetime(2024, 1, 2, 12, 0, tzinfo=UTC),
    )

    assert len(actions) == 1
    assert actions[0].timestamp == datetime(2024, 1, 2, 6, 0, tzinfo=UTC)


def test_delete_action_with_no_matches_does_not_save(task1):
    app.register_task(task1)

    with patch("app.tracker.save") as mock_save:
        deleted = app.delete_action(task1.name, action_name="missing")

    assert deleted == 0
    mock_save.assert_not_called()


def test_get_next_runs_ignores_unknown_and_unscheduled_tasks(task1):
    app.register_task(task1)
    app.register_task(Task("one-off", start_time=None, interval=None))
    at_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)

    assert app.get_next_runs(for_task="missing", at=at_time) == []
    assert [task.name for task, _ in app.get_next_runs(at=at_time)] == [task1.name]
