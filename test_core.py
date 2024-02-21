from pathlib import Path
from core import *
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


def test_save_load_task_list(tmp_path: Path, task1: Task, task2: Task, task3: Task):
    tsk_lst = TaskLister([task1, task2])
    tsk_lst.add(task3)

    logging.debug(f"Temporary path for TaskListPersister {tmp_path}")
    tl_saver = TaskListPersister(tsk_lst, dirname=tmp_path)

    tl_saver._remove_file()

    tl_saver.save()

    new_tl_saver = TaskListPersister(TaskLister([]), dirname=tmp_path)
    new_task_list = new_tl_saver.load()

    tl_saver._remove_file()

    assert new_task_list == tsk_lst
    assert type(new_task_list) == type(tsk_lst)


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


def test_save_load_action_list(tmp_path: Path, action1_t1: Action, action2_t1: Action):
    act_lst = ActionLister([action1_t1, action2_t1])

    logging.debug(f"Temporary path for ActionListPersister {tmp_path}")
    al_saver = ActionListPersister(act_lst, dirname=tmp_path)

    al_saver._remove_file()

    al_saver.save()

    new_al_saver = ActionListPersister(ActionLister([]), dirname=tmp_path)
    new_action_list = new_al_saver.load()

    al_saver._remove_file()

    assert (new_action_list == act_lst) and type(new_action_list) == type(act_lst)


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


@pytest.mark.parametrize(
    "task,now_tbu,n,expected_prog_time",
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
    now_tbu: datetime,
    n: int,
    expected_prog_time: datetime | None,
    request: pytest.FixtureRequest,
):
    task_instance = request.getfixturevalue(task)
    returned_value = task_instance.get_programmed_time(n=n, when=now_tbu)
    if expected_prog_time is None:
        assert returned_value is None
    else:
        assert returned_value == expected_prog_time


def test_get_next_tasks_due_period__success(task1, task2, task3, task4):
    tsk_lst = TaskLister([task1, task2, task3, task4])

    when = datetime(2024, 1, 20, 10, 0, tzinfo=UTC)

    ret = tsk_lst.get_next_tasks_due_period(timedelta(hours=1), now_tbu)

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


if __name__ == "__main__":
    pass
