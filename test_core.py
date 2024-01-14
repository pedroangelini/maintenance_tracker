from core import *
import pytest
import logging
from datetime import datetime

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


if __name__ == "__main__":
    pass