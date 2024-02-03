import pytest
from core import *
from maintenance_tracker import *
from datetime import datetime
from test_core import task1, task2, task3  # fixtures


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


if __name__ == "__main__":
    pass
