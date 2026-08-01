from pathlib import Path
from core import *
from repository import (
    TaskListPersister,
    ActionListPersister,
    Persister,
    MtnTrackerJSONDecoder,
    MtnTrackerJSONEncoder,
    DEFAULT_TASK_LIST_FILE,
    DEFAULT_ACTION_LIST_FILE,
)
import pytest
import logging
from datetime import datetime, UTC

from core import Action, Task

logging.basicConfig(level=logging.DEBUG)


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
def task4():
    """A fourth without start time or interval"""
    return Task(
        name="my fourth task",
        description="adding this one #3",
        start_time=None,
        interval=None,
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

@pytest.fixture(scope="function")
def action3_t1(task1: Task):
    return Action(
        datetime(2024, 1, 3, 0, 0, tzinfo=UTC),
        task1,
        "ran task1 on day 3",
        "me",
    )


def test_task_equality(task1: Task, task2: Task):
    task1_copy = task1.copy()
    assert task1 == task1_copy, "issue with Task equality"
    assert task1 != task2, "issue with Task inequality"
    assert task1 != "que?", "issue with equality of different types (Task)"


def test_action_list_equality(task1: Task, action1_t1: Action, action2_t1: Action):
    action_lst1 = ActionLister([action1_t1, action2_t1])
    action_lst1_copy = ActionLister([action1_t1, action2_t1])
    action_lst2 = ActionLister([action1_t1])

    assert action_lst1 == action_lst1_copy, "issue with ActionLister equality"
    assert action_lst1 != action_lst2, "issue with ActionLister inequality"
    assert (
        action_lst1 != "que?"
    ), "issue with equality of different types (ActionLister)"


# persister tests moved to test_repository.py


def test_get_task_by_name(task1, task2):
    tsk_lst = TaskLister([task1, task2])
    assert task2 == tsk_lst.get_task_by_name(
        "my second task"
    ), "did not get the right task"
    assert (
        tsk_lst.get_task_by_name("non-existing-name") is None
    ), "search for non existing task didn't return None"


def test_get_all_tasks_due_period(task1, task2):
    tsk_lst = TaskLister([task1, task2])

    when = datetime(2024, 1, 30, 10, 10, tzinfo=UTC)

    # task1 every hour at 32 min
    # task2 every 30 min at 02 min and 32 min

    period = timedelta(hours=1)
    return1 = tsk_lst.get_all_tasks_due_period(period, when)
    assert return1 == [
        (task1, (datetime(2024, 1, 30, 10, 32, tzinfo=UTC),)),
        (
            task2,
            (
                datetime(2024, 1, 30, 10, 32, tzinfo=UTC),
                datetime(2024, 1, 30, 11, 2, tzinfo=UTC),
            ),
        ),
    ]

    period = timedelta(hours=-1)
    return2 = tsk_lst.get_all_tasks_due_period(period, when)
    assert return2 == [
        (task1, (datetime(2024, 1, 30, 9, 32, tzinfo=UTC),)),
        (
            task2,
            (
                datetime(2024, 1, 30, 9, 32, tzinfo=UTC),
                datetime(2024, 1, 30, 10, 2, tzinfo=UTC),
            ),
        ),
    ]


# persister tests moved to test_repository.py


def test_task_lister_collision(task1: Task):
    t1 = task1
    t2 = task1.copy()

    # collisions with .add()
    with pytest.raises(TaskWithSameNameError):
        lst = TaskLister([t1])
        lst.add(t2)

    # collisions with .extend()
    with pytest.raises(TaskWithSameNameError):
        lst = TaskLister([t1])
        lst.extend([t2])

    # collisions in initializer
    with pytest.raises(TaskWithSameNameError):
        TaskLister([t1, t2])

    # collisions with addition
    with pytest.raises(TaskWithSameNameError):
        lst = TaskLister([])
        lst = lst + [t1]
        lst = lst + [t2]


def test_task_rejects_empty_name_and_lister_rejects_none_name():
    with pytest.raises(ValueError, match="name cannot be None"):
        Task(name=None)

    with pytest.raises(ValueError, match="name passed as None"):
        TaskLister()._check_task_name_available(None)


def test_one_off_task_programmed_times():
    start = datetime(2024, 1, 2, 10, 0, tzinfo=UTC)
    task = Task("one-off", start_time=start, interval=timedelta(0))

    assert task.get_programmed_time(1, when=datetime(2024, 1, 1, tzinfo=UTC)) == start
    assert task.get_programmed_time(-1, when=datetime(2024, 1, 3, tzinfo=UTC)) == start
    assert task.get_all_programmed_times(
        timedelta(days=2), when=datetime(2024, 1, 1, tzinfo=UTC)
    ) == [start]


@pytest.mark.parametrize(
    "task,when,n,expected_prog_time",
    [
        # see https://engineeringfordatascience.com/posts/pytest_fixtures_with_parameterize/ for fixtures in parametrized test
        (
            "task1",
            datetime(2023, 12, 24, 18, 00, tzinfo=UTC),
            +1,
            datetime(2023, 12, 24, 18, 32, tzinfo=UTC),
        ),
        (
            "task1",
            datetime(2023, 12, 24, 18, 00, tzinfo=UTC),
            -1,
            datetime(2023, 12, 24, 17, 32, tzinfo=UTC),
        ),
        (
            "task1",
            datetime(2023, 12, 24, 18, 00, tzinfo=UTC),
            +3,
            datetime(2023, 12, 24, 20, 32, tzinfo=UTC),
        ),
        (
            "task1",
            datetime(2023, 12, 24, 18, 00, tzinfo=UTC),
            -2,
            None,
        ),  # would fall before the start time
        (
            "task1",
            datetime(2024, 6, 10, 18, 00, tzinfo=UTC),
            -5,
            datetime(2024, 6, 10, 13, 32, tzinfo=UTC),
        ),
        ("task4", datetime(2023, 12, 24, 18, 00, tzinfo=UTC), 5, None),
    ],
)
def test_get_programmed_time(
    task: str,
    when: datetime,
    n: int,
    expected_prog_time: datetime | None,
    request: pytest.FixtureRequest,
):
    task_instance = request.getfixturevalue(task)
    returned_value = task_instance.get_programmed_time(n=n, when=when)
    if expected_prog_time is None:
        assert returned_value is None
    else:
        assert returned_value == expected_prog_time


def test_get_next_tasks_due_period__success(task1, task2, task3, task4):
    tsk_lst = TaskLister([task1, task2, task3, task4])

    when = datetime(2024, 1, 20, 10, 0, tzinfo=UTC)

    ret = tsk_lst.get_next_tasks_due_period(timedelta(hours=1), when)

    # task1 is programmed every hour, at 32 min
    # task2 is programmed every 30 min at 32 and 02 min
    # task3 is programmed to run every 15 min, at 05, 20, 35, 50 min of every hour
    # task4 is not programmed to run
    # fmt: off
    assert len(ret) == 3, \
         f"have more tasks than expected, got {len(ret)}, was expecting 3"
    assert ret[0][0] == task1, "issue on task1"
    assert ret[0][1] == datetime(2024, 1, 20, 10, 32, tzinfo=UTC), "issue on task1 next programmed time"
    assert ret[1][0] == task2, "issue on task2"
    assert ret[1][1] == datetime(2024, 1, 20, 10, 2, tzinfo=UTC), "issue on task2 next programmed time"
    assert ret[2][0] == task3, "issue on task3"
    assert ret[2][1] == datetime(2024, 1, 20, 10, 5, tzinfo=UTC), "issue on task3 next programmed time"
    # fmt: on


def test_get_next_tasks_due_period__none(task1, task2, task3, task4):
    tsk_lst = TaskLister([task4])

    now_tbu = datetime(2024, 1, 20, 10, 0, tzinfo=UTC)

    ret = tsk_lst.get_next_tasks_due_period(timedelta(hours=1), now_tbu)
    assert ret == []


def test_get_next_tasks_due_period__before_start(task1, task2, task3, task4):
    tsk_lst = TaskLister([task1, task2])

    now_tbu = datetime(2022, 1, 20, 10, 0, tzinfo=UTC)

    ret = tsk_lst.get_next_tasks_due_period(timedelta(hours=1), now_tbu)
    assert ret == []

def test_action_list_inequality_size_diff(task1: Task, action1_t1: Action, action2_t1: Action):
    action_lst1 = ActionLister([action1_t1, action2_t1])
    action_lst2 = ActionLister([action1_t1])

    assert action_lst1 != action_lst2, "ActionLister __eq__ not detecting inequality when 2 lists have different sizes"


def test_action_list_equality_different_content(action1_t1: Action, action2_t1: Action, action3_t1: Action):
    # Test for inequality with two lists of the same length but different content
    action_lst_a = ActionLister([action1_t1, action2_t1]) # 2024-01-01, 2024-01-02
    action_lst_b = ActionLister([action1_t1, action3_t1]) # 2024-01-01, 2024-01-03

    assert action_lst_a != action_lst_b, "ActionLister should report lists with different contents as not equal."


def test_action_list_equality_order_independent(action1_t1: Action, action2_t1: Action):
    # Test for equality with the same actions in a different order
    action_lst_c = ActionLister([action1_t1, action2_t1])
    action_lst_d = ActionLister([action2_t1, action1_t1])
    assert action_lst_c == action_lst_d, "ActionLister equality should be order-independent."


def test_task_replace_single_field(task1: Task):
    updated_task = task1.replace(changes={"description": "new description"})
    assert updated_task.description == "new description"
    assert updated_task.name == task1.name
    assert updated_task.start_time == task1.start_time
    assert updated_task.interval == task1.interval
    assert task1.description == "a description for my task1", "Original task should be immutable"


def test_task_replace_multiple_fields(task1: Task):
    new_start_time = datetime(2025, 1, 1, tzinfo=UTC)
    new_interval = timedelta(hours=2)
    updated_task = task1.replace(changes={
        "description": "another description",
        "start_time": new_start_time,
        "interval": new_interval
    })
    assert updated_task.description == "another description"
    assert updated_task.start_time == new_start_time
    assert updated_task.interval == new_interval
    assert updated_task.name == task1.name
    assert task1.description == "a description for my task1", "Original task should be immutable"


def test_task_replace_none_values(task1: Task):
    updated_task = task1.replace(changes={"start_time": None, "interval": None})
    assert updated_task.start_time is None
    assert updated_task.interval is None
    assert updated_task.name == task1.name
    assert task1.start_time is not None, "Original task should be immutable"


def test_action_replace_single_field(action1_t1: Action):
    new_name = "new action name"
    updated_action = action1_t1.replace(changes={"name": new_name})
    assert updated_action.name == new_name
    assert updated_action.description == action1_t1.description
    assert updated_action.timestamp == action1_t1.timestamp
    assert updated_action.ref_task == action1_t1.ref_task
    assert action1_t1.name == "ran task1 on new year day", "Original action should be immutable"


def test_action_replace_multiple_fields(action1_t1: Action, task2: Task):
    new_timestamp = datetime(2024, 1, 5, tzinfo=UTC)
    new_description = "a different description"
    updated_action = action1_t1.replace(changes={
        "timestamp": new_timestamp,
        "description": new_description,
        "ref_task": task2
    })
    assert updated_action.timestamp == new_timestamp
    assert updated_action.description == new_description
    assert updated_action.ref_task == task2
    assert updated_action.name == action1_t1.name
    assert action1_t1.timestamp != new_timestamp, "Original action should be immutable"


@pytest.fixture
def task_no_interval(task1: Task):
    """A task with a start time but no interval."""
    return task1.replace(changes={"interval": None})


def test_task_str(task1):
    string = str(task1)
    assert "Task: my first task" in string
    assert "a description for my task1" in string
    assert f"starting on: {utils.human_date_str(task1.start_time)}" in string
    assert f"interval: {utils.human_interval_str(task1.interval)}" in string

def test_task_get_programmed_time_negative_n_before_start(task1):
    when = task1.start_time + timedelta(minutes=30)
    assert task1.get_programmed_time(n=-2, when=when) is None

def test_task_get_all_programmed_times_no_interval(task_no_interval):
    when = task_no_interval.start_time - timedelta(days=1)
    period = timedelta(days=2)
    times = task_no_interval.get_all_programmed_times(period, when)
    assert times == [task_no_interval.start_time]

    when_after = task_no_interval.start_time + timedelta(days=1)
    times_after = task_no_interval.get_all_programmed_times(period, when_after)
    assert times_after == []

    # Also test case where it does not repeat and start_time is not in period
    when = task_no_interval.start_time - timedelta(days=2)
    period = timedelta(days=1)
    times = task_no_interval.get_all_programmed_times(period, when)
    assert times == []


def test_task_get_all_programmed_times_break(task1):
    # This test is to cover the break condition in get_all_programmed_times
    when = task1.start_time
    period = timedelta(hours=5)
    times = task1.get_all_programmed_times(period, when)
    assert len(times) == 5

# persister and JSON codec tests moved to test_repository.py

def test_task_lister_get_task_by_name_not_found(task1):
    lister = TaskLister([task1])
    assert lister.get_task_by_name("non-existent task") is None
