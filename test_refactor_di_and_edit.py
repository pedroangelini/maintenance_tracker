import pytest
from maintenance_tracker import MaintenanceTracker, Action, Task, ActionRecordResults, TaskRecordResults
from core import TaskLister, ActionLister
from datetime import datetime, UTC, timedelta
import utils


def test_di_with_inmemory_repos():
    # Simple in-memory repo implementations
    class InMemoryTaskRepo:
        def __init__(self):
            self.task_list = TaskLister([])
        def list(self):
            return self.task_list
        def get_by_name(self, name):
            return self.task_list.get_task_by_name(name)
        def add(self, t):
            self.task_list.append(t)
        def remove(self, t):
            self.task_list.remove(t)
        def save(self):
            return self.task_list
        def load(self):
            return self.task_list

    class InMemoryActionRepo:
        def __init__(self):
            self.action_list = ActionLister([])
        def list(self):
            return self.action_list
        def add(self, a):
            self.action_list.append(a)
        def remove(self, a):
            self.action_list.remove(a)
        def get_for_task(self, task, start_time=None, end_time=None, ordered=False):
            return [a for a in self.action_list if a.ref_task.name == task.name]
        def get_by_time(self, start, end=None):
            return [a for a in self.action_list if start <= a.timestamp <= (end if end is not None else datetime.now(UTC))]
        def save(self):
            return self.action_list
        def load(self):
            return self.action_list

    trepo = InMemoryTaskRepo()
    arepo = InMemoryActionRepo()

    mt = MaintenanceTracker(task_repo=trepo, action_repo=arepo)

    t = Task(name="t1")
    mt.register_task(t)
    assert mt.task_list[0].name == "t1"

    a = Action(timestamp=datetime(2024,1,1, tzinfo=UTC), ref_task=t)
    res = mt.record_run(a)
    assert res in (ActionRecordResults.SUCCESS, ActionRecordResults.TASK_MISMATCH)
    assert mt.action_list[0].ref_task.name == "t1"


def test_edit_task_moves_actions(task1, action1_t1, action2_t1):
    mt = MaintenanceTracker()
    mt.register_task(task1)
    mt.record_run(action1_t1)
    mt.record_run(action2_t1)

    old_task = task1
    new_task = mt.edit_task(old_task, {"name": "my renamed task"})
    assert new_task is not None
    # all actions should now reference the new task name
    for a in mt.action_list:
        assert a.ref_task.name == "my renamed task"
    # old task should not be present
    assert mt.task_list.get_task_by_name(old_task.name) is None


def test_edit_action_by_timestamp_and_name(task1):
    mt = MaintenanceTracker()
    mt.register_task(task1)
    a = Action(timestamp=datetime(2024,2,2, tzinfo=UTC), ref_task=task1, name="do it", actor="old")
    mt.record_run(a)

    # edit by timestamp string
    ts_str = a.timestamp.isoformat()
    edited = mt.edit_action(task1.name, ts_str, new_actor="new")
    assert edited is not None
    assert edited.actor == "new"

    # edit by name
    edited2 = mt.edit_action(task1.name, "do it", new_action_name="did it")
    assert edited2 is not None
    assert edited2.name == "did it"
