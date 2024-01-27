from core import *
import pytest
import logging
from datetime import datetime, UTC

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture(scope="function")
def task1():
    """A simple task for testing"""
    return Task(
        name="my first task",
        description="a description for my task1",
        start_time=datetime(2023, 12, 24, 17, 32),
        interval=timedelta(minutes=60),
    )


@pytest.fixture(scope="function")
def task2():
    """A second task for testing, different from the first"""
    return Task(
        name="my second task",
        description="a description for my task2",
        start_time=datetime(2023, 12, 25, 17, 32),
        interval=timedelta(minutes=30),
    )


@pytest.fixture(scope="function")
def task3():
    """A third task for testing, different from the first 2"""
    return Task(
        name="my third task",
        description="adding this one #3",
        start_time=datetime(2023, 12, 25, 17, 32),
        interval=timedelta(minutes=30),
    )


@pytest.fixture(scope="function")
def task4():
    """A fourth without start time or interval"""
    return Task(
        name="my third task",
        description="adding this one #3",
        start_time=None,
        interval=None,
    )


@pytest.fixture(scope="function")
def action1_t1(task1):
    return Action(
        datetime(
            2024,
            1,
            1,
        ),
        task1,
        "ran task1 on new year day",
        "me",
    )


@pytest.fixture(scope="function")
def action2_t1(task1):
    return Action(
        datetime(
            2024,
            1,
            2,
        ),
        task1,
        "ran task1 on the second of the year",
        "me",
    )


def test_save_load_task_list(tmp_path, task1, task2, task3):
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


def test_save_load_acion_list(tmp_path, action1_t1, action2_t1):
    act_lst = ActionLister([action1_t1, action2_t1])

    logging.debug(f"Temporary path for ActionListPersister {tmp_path}")
    al_saver = ActionListPersister(act_lst, dirname=tmp_path)

    al_saver._remove_file()

    al_saver.save()

    new_al_saver = ActionListPersister(ActionLister([]), dirname=tmp_path)
    new_action_list = new_al_saver.load()

    al_saver._remove_file()

    assert (new_action_list == act_lst) and type(new_action_list) == type(act_lst)


def test_task_lister_collision(task1):
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
        ("task1", datetime(2023, 12, 24, 18, 00), +1, datetime(2023, 12, 24, 18, 32)),
        ("task1", datetime(2023, 12, 24, 18, 00), -1, datetime(2023, 12, 24, 17, 32)),
        ("task1", datetime(2023, 12, 24, 18, 00), +3, datetime(2023, 12, 24, 20, 32)),
        (
            "task1",
            datetime(2023, 12, 24, 18, 00),
            -2,
            None,
        ),  # would fall before the start time
        ("task1", datetime(2024, 6, 10, 18, 00), -5, datetime(2024, 6, 10, 13, 32)),
        ("task4", datetime(2023, 12, 24, 18, 00), 5, None),
    ],
)
def test_get_programmed_time(task, now_tbu, n, expected_prog_time, request):
    task_instance = request.getfixturevalue(task)
    returned_value = task_instance.get_programmed_time(n=n, now_to_be_used=now_tbu)
    if expected_prog_time is None:
        assert returned_value is None
    else:
        assert returned_value == expected_prog_time


if __name__ == "__main__":
    pass
