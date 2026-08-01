import pytest
import os
from maintenance_tracker import MaintenanceTracker, Action, Task, ActionRecordResults
from repository import FileTaskRepository, FileActionRepository, TaskListPersister, ActionListPersister
from core import TaskLister, ActionLister
from datetime import datetime, UTC
import utils


def test_init_with_provided_repos_and_load(tmp_path):
    # create file-backed repos and save initial data
    task = Task(name="r1")
    action = Action(timestamp=datetime(2024,1,1, tzinfo=UTC), ref_task=task, name="a1")
    trepo = FileTaskRepository(TaskLister([task]), dirname=str(tmp_path))
    arepo = FileActionRepository(ActionLister([action]), dirname=str(tmp_path))

    # save initial files
    trepo.save()
    arepo.save()

    # initialize tracker with provided repos and load=True
    mt = MaintenanceTracker(load=True, task_repo=trepo, action_repo=arepo)
    assert any(t.name == "r1" for t in mt.task_list)
    assert any(a.name == "a1" for a in mt.action_list)


def test_save_writes_files(tmp_path):
    mt = MaintenanceTracker(save_dir=str(tmp_path))
    t = Task(name="sv")
    mt.register_task(t)
    a = Action(timestamp=datetime(2024,2,2, tzinfo=UTC), ref_task=t, name="svact")
    mt.record_run(a)
    mt.save()

    # check files exist
    task_file = os.path.join(str(tmp_path), "task_list.json")
    action_file = os.path.join(str(tmp_path), "action_list.json")
    assert os.path.exists(task_file)
    assert os.path.exists(action_file)


def test_edit_action_name_path_with_parse_error(monkeypatch, task1):
    mt = MaintenanceTracker()
    mt.register_task(task1)
    a = Action(timestamp=datetime(2024,3,3, tzinfo=UTC), ref_task=task1, name="parseme")
    mt.record_run(a)

    # force parse_date to raise so edit_action goes into the except branch
    monkeypatch.setattr(utils, 'parse_date', lambda s: (_ for _ in ()).throw(utils.DateParseError("fail")))

    edited = mt.edit_action(task1.name, "parseme", new_actor="me")
    assert edited is not None
    assert edited.actor == "me"
