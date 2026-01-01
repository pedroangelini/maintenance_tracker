import pytest
from core import *
from maintenance_tracker import *
from datetime import datetime
from test_core import task1, task2, task3  # fixtures
from test_core import action1_t1, action2_t1  # fixtures


def test_listing_actions_for_task(task1, task2):
    action1_t1 = Action(
        datetime(
            2024,
            1,
            1,
        ),
        task1,
        "ran task1 on new year day",
        "me",
    )
    action2_t1 = Action(
        datetime(
            2024,
            1,
            2,
        ),
        task1,
        "ran task1 on the second of the year",
        "me",
    )
    action1_t2 = Action(
        datetime(
            2024,
            1,
            1,
        ),
        task2,
        "ran task2 on new year day",
        "me",
    )
    action2_t2 = Action(
        datetime(
            2024,
            1,
            2,
        ),
        task2,
        "ran task2 on the second of the year",
        "me",
    )

    action_lst = ActionLister([action1_t1, action1_t2, action2_t1, action2_t2])

    mtnt = MaintenanceTracker()
    mtnt.register_task(task1)
    mtnt.register_task(task2)
    for a in action_lst:
        mtnt.record_run(a)

    assert ActionLister([action1_t2, action2_t2]) == mtnt.get_actions_for_task(task2)


def test_record_run(task1):
    action1 = Action(
        datetime(2024, 1, 7, 10, 15),
        task1,
        "running the first task",
        "a description for the first run of task1",
        "Pedro",
    )

    mtnt = MaintenanceTracker()
    mtnt.record_run(action1)

    assert mtnt.task_list[0].name == "my first task"


def test_get_latest_task_run_success(task1, action1_t1, action2_t1):
    mtnt = MaintenanceTracker()
    mtnt.register_task(task1)
    mtnt.record_run(action1_t1)
    mtnt.record_run(action2_t1)

    assert mtnt.get_latest_task_run(task1) == action2_t1


def test_get_latest_task_run_no_action(task2):
    mtnt = MaintenanceTracker()
    mtnt.register_task(task2)

    assert mtnt.get_latest_task_run(task2) is None


def test_get_latest_task_run_empty(task2):
    mtnt = MaintenanceTracker()

    assert mtnt.get_latest_task_run(task2) is None


def test_check_overdue_has_action_is_overdue(task1, action1_t1, action2_t1):
    mtnt = MaintenanceTracker()
    mtnt.register_task(task1)  # every hour at 32 min, start 2023-12-24
    mtnt.record_run(action1_t1)  # new year 2024 (0h)
    mtnt.record_run(action2_t1)  # 2024-01-02, 6 AM

    when = datetime(2024, 1, 2, 6, 33, tzinfo=UTC)

    assert mtnt.check_overdue(task1, when=when) == True


def test_check_overdue_has_action_is_not_overdue(task1, action1_t1, action2_t1):
    mtnt = MaintenanceTracker()
    mtnt.register_task(task1)  # every hour at 32 min, start 2023-12-24
    mtnt.record_run(action1_t1)  # new year 2024 (0h)
    mtnt.record_run(action2_t1)  # 2024-01-02, 6 AM

    when = datetime(2024, 1, 2, 6, 31, tzinfo=UTC)

    assert mtnt.check_overdue(task1, when=when) == False


def test_check_overdue_has_no_action_is_overdue(task1):
    mtnt = MaintenanceTracker()
    mtnt.register_task(task1)  # every hour at 32 min, start 2023-12-24

    when = datetime(2024, 1, 2, 6, 31, tzinfo=UTC)

    assert mtnt.check_overdue(task1, when=when) == True


def test_check_overdue_has_no_action_is_not_overdue():
    mtnt = MaintenanceTracker()
    when = datetime(2024, 2, 21, 23, 24, tzinfo=UTC)
    future_task = Task(
        "future task",
        "starts in the future",
        datetime(2024, 2, 22, 23, 24, tzinfo=UTC),
        timedelta(days=1),
    )

    mtnt.register_task(future_task)

    assert mtnt.check_overdue(future_task, when) == False


def test_check_overdue_only_as_action_after_when(task1):
    mtnt = MaintenanceTracker()
    mtnt.register_task(task1)  # every hour at 32 min, start 2023-12-24

    when = datetime(2024, 1, 2, 6, 30, tzinfo=UTC)
    future_action = Action(
        datetime(2024, 1, 2, 6, 31, tzinfo=UTC),
        task1,
        "an action in the future",
        "...in this context",
        "test me",
    )

    mtnt.record_run(future_action)

    assert mtnt.check_overdue(task1, when=when) == True


def test_time_since_last_exec_no_runs(task1):
    mtnt = MaintenanceTracker()
    mtnt.register_task(task1)
    assert mtnt.time_since_last_exec(task1) is None


def test_time_since_last_exec_with_runs(task1, action1_t1, action2_t1):
    mtnt = MaintenanceTracker()
    mtnt.register_task(task1)
    mtnt.record_run(action1_t1)  # 2024-01-01 00:00 UTC
    mtnt.record_run(action2_t1)  # 2024-01-02 06:00 UTC

    # Test with explicit 'when' after the last action
    when_after = datetime(2024, 1, 2, 7, 0, tzinfo=UTC)
    expected_timedelta = timedelta(hours=1)
    assert mtnt.time_since_last_exec(task1, when=when_after) == expected_timedelta

    # Test with explicit 'when' before the last action (should still pick the last action before 'when')
    when_before_last_run = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    expected_timedelta_before = timedelta(hours=12) # from action1_t1 (2024-01-01 00:00 UTC)
    assert mtnt.time_since_last_exec(task1, when=when_before_last_run) == expected_timedelta_before


def test_time_since_last_exec_with_when_equal_to_last_run(task1, action2_t1):
    mtnt = MaintenanceTracker()
    mtnt.register_task(task1)
    mtnt.record_run(action2_t1)  # 2024-01-02 06:00 UTC

    when_equal = datetime(2024, 1, 2, 6, 0, tzinfo=UTC)
    expected_timedelta = timedelta(seconds=0)
    assert mtnt.time_since_last_exec(task1, when=when_equal) == expected_timedelta


def test_time_since_last_exec_empty_tracker(task1):
    mtnt = MaintenanceTracker()
    assert mtnt.time_since_last_exec(task1) is None
