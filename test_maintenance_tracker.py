import pytest
from core import *
from maintenance_tracker import *
from datetime import datetime, timedelta, UTC

# Local fixtures (each test file owns the fixtures it needs)
@pytest.fixture(scope="function")
def task1():
    return Task(
        name="my first task",
        description="a description for my task1",
        start_time=datetime(2023, 12, 24, 17, 32, tzinfo=UTC),
        interval=timedelta(minutes=60),
    )

@pytest.fixture(scope="function")
def task2():
    return Task(
        name="my second task",
        description="a description for my task2",
        start_time=datetime(2023, 12, 25, 17, 32, tzinfo=UTC),
        interval=timedelta(minutes=30),
    )

@pytest.fixture(scope="function")
def task3():
    return Task(
        name="my third task",
        description="adding this one #3",
        start_time=datetime(2023, 12, 25, 17, 5, tzinfo=UTC),
        interval=timedelta(minutes=15),
    )

@pytest.fixture(scope="function")
def action1_t1(task1: Task):
    return Action(
        datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        task1,
        "ran task1 on new year day",
        "me",
    )

@pytest.fixture(scope="function")
def action2_t1(task1: Task):
    return Action(
        datetime(2024, 1, 2, 6, 0, tzinfo=UTC),
        task1,
        "ran task1 on the second of the year, 6 AM",
        "me",
    )


def test_listing_actions_for_task(task1, task2):
    action1 = Action(datetime(2024, 1, 1), task1, "ran task1 on new year day", "me")
    action2 = Action(datetime(2024, 1, 2), task1, "ran task1 on the second of the year", "me")
    action1_t2 = Action(datetime(2024, 1, 1), task2, "ran task2 on new year day", "me")
    action2_t2 = Action(datetime(2024, 1, 2), task2, "ran task2 on the second of the year", "me")

    action_lst = ActionLister([action1, action1_t2, action2, action2_t2])

    mtnt = MaintenanceTracker()
    mtnt.register_task(task1)
    mtnt.register_task(task2)
    for a in action_lst:
        mtnt.record_run(a)

    assert ActionLister([action1_t2, action2_t2]) == mtnt.get_actions_for_task(task2)


def test_record_run(task1):
    action1 = Action(datetime(2024, 1, 7, 10, 15), task1, "running the first task", "a description for the first run of task1", "Pedro")

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


def test_check_overdue_has_action_is_overdue(task1, action1_t1, action2_t1):
    mtnt = MaintenanceTracker()
    mtnt.register_task(task1)
    mtnt.record_run(action1_t1)
    mtnt.record_run(action2_t1)

    when = datetime(2024, 1, 2, 6, 33, tzinfo=UTC)

    assert mtnt.check_overdue(task1, when=when) is True


def test_time_since_last_exec_with_runs(task1, action1_t1, action2_t1):
    mtnt = MaintenanceTracker()
    mtnt.register_task(task1)
    mtnt.record_run(action1_t1)
    mtnt.record_run(action2_t1)

    when_after = datetime(2024, 1, 2, 7, 0, tzinfo=UTC)
    expected_timedelta = timedelta(hours=1)
    assert mtnt.time_since_last_exec(task1, when=when_after) == expected_timedelta


def test_record_run_task_mismatch(task1):
    mtnt = MaintenanceTracker()
    mtnt.register_task(task1)
    
    task1_modified = task1.replace(changes={"description": "a new description"})
    action = Action(datetime.now(UTC), task1_modified)
    
    result = mtnt.record_run(action)
    assert result == ActionRecordResults.TASK_MISMATCH


def test_get_actions_for_task_ordered_desc(task1, action1_t1, action2_t1):
    mtnt = MaintenanceTracker()
    mtnt.register_task(task1)
    mtnt.record_run(action1_t1)
    mtnt.record_run(action2_t1)
    
    actions = mtnt.get_actions_for_task(task1, ordered=Ordering.DESC)
    assert actions[0] == action2_t1
    assert actions[1] == action1_t1


def test_get_latest_task_run_with_future_action(task1, action1_t1):
    mtnt = MaintenanceTracker()
    mtnt.register_task(task1)
    mtnt.record_run(action1_t1)

    future_action = Action(datetime.now(UTC) + timedelta(days=1), task1)
    mtnt.record_run(future_action)

    when = datetime.now(UTC)
    latest_run = mtnt.get_latest_task_run(task1, when=when)
    assert latest_run == action1_t1


def test_delete_task_with_dangling_actions(task1, action1_t1):
    mtnt = MaintenanceTracker()
    mtnt.register_task(task1)
    mtnt.record_run(action1_t1)

    from errors import DanglingActionsError
    with pytest.raises(DanglingActionsError):
        mtnt.delete_task(task1)

    # ensure task still present
    assert task1 in mtnt.task_list


def test_delete_run(task1, action1_t1, action2_t1):
    mtnt = MaintenanceTracker()
    mtnt.register_task(task1)
    mtnt.record_run(action1_t1)
    mtnt.record_run(action2_t1)

    result = mtnt.delete_run(action1_t1)
    assert result == ActionRecordResults.SUCCESS
    assert action1_t1 not in mtnt.action_list
    assert len(mtnt.action_list) == 1


def test_save_and_load_tracker(tmp_path, task1, action1_t1):
    save_dir = tmp_path / "tracker_data"
    save_dir.mkdir()
    
    mtnt = MaintenanceTracker(save_dir=str(save_dir))
    mtnt.register_task(task1)
    mtnt.record_run(action1_t1)
    mtnt.save()

    new_mtnt = MaintenanceTracker(load=True, save_dir=str(save_dir))
    assert len(new_mtnt.task_list) == 1
    assert len(new_mtnt.action_list) == 1
    assert new_mtnt.task_list[0] == task1
    assert new_mtnt.action_list[0] == action1_t1


def test_get_actions_by_time(task1, action1_t1, action2_t1):
    mtnt = MaintenanceTracker()
    mtnt.register_task(task1)
    mtnt.record_run(action1_t1)
    mtnt.record_run(action2_t1)

    start_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    end_time = datetime(2024, 1, 2, 12, 0, tzinfo=UTC)
    
    actions = mtnt.get_actions_by_time(start_time, end_time)
    assert len(actions) == 1
    assert actions[0] == action2_t1
    
    actions_no_end = mtnt.get_actions_by_time(start_time=datetime(2023, 1, 1, 0, 0, tzinfo=UTC))
    assert len(actions_no_end) == 2


def test_get_actions_for_task_time_filter(task1, action1_t1, action2_t1):
    mtnt = MaintenanceTracker()
    mtnt.register_task(task1)
    mtnt.record_run(action1_t1)  # 2024-01-01
    mtnt.record_run(action2_t1)  # 2024-01-02

    start_time = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    end_time = datetime(2024, 1, 2, 12, 0, tzinfo=UTC)

    actions = mtnt.get_actions_for_task(task1, start_time=start_time, end_time=end_time)
    assert len(actions) == 1
    assert actions[0] == action2_t1

