import pytest
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
