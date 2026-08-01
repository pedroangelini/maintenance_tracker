import pytest
from pathlib import Path
from datetime import datetime

from core import Task, Action, TaskLister, ActionLister
from repository import (
    TaskListPersister,
    ActionListPersister,
    Persister,
    MtnTrackerJSONDecoder,
    DEFAULT_TASK_LIST_FILE,
    DEFAULT_ACTION_LIST_FILE,
    FileTaskRepository,
    FileActionRepository,
)
from datetime import UTC, datetime
from pathlib import Path
import pytest


def test_save_load_task_list(tmp_path: Path):
    t1 = Task(name="t1")
    t2 = Task(name="t2")
    tsk_lst = TaskLister([t1, t2])

    tl_saver = TaskListPersister(tsk_lst, dirname=tmp_path)
    tl_saver._remove_file()
    tl_saver.save()

    new_tl_saver = TaskListPersister(TaskLister([]), dirname=tmp_path)
    new_task_list = new_tl_saver.load()

    tl_saver._remove_file()

    assert new_task_list == tsk_lst
    assert type(new_task_list) == type(tsk_lst)


def test_save_load_action_list(tmp_path: Path):
    a1 = Action(datetime(2024, 1, 1, tzinfo=UTC), Task(name="t"), "a1")
    a2 = Action(datetime(2024, 1, 2, tzinfo=UTC), Task(name="t"), "a2")
    act_lst = ActionLister([a1, a2])

    al_saver = ActionListPersister(act_lst, dirname=tmp_path)
    al_saver._remove_file()
    al_saver.save()

    new_al_saver = ActionListPersister(ActionLister([]), dirname=tmp_path)
    new_action_list = new_al_saver.load()

    al_saver._remove_file()

    assert (new_action_list == act_lst) and type(new_action_list) == type(act_lst)


def test_persister_remove_nonexistent_file(tmp_path):
    persister = Persister(None)
    persister.save_path = tmp_path / "non_existent_file.json"
    # should not raise
    persister._remove_file()


def test_json_decoder_unknown_and_no_type():
    decoder = MtnTrackerJSONDecoder()
    json_unknown = '{"__type__": "UnknownType", "foo": "bar"}'
    decoded_unknown = decoder.decode(json_unknown)
    assert decoded_unknown == {"__type__": "UnknownType", "foo": "bar"}

    json_no_type = '{"foo": "bar"}'
    decoded_no_type = decoder.decode(json_no_type)
    assert decoded_no_type == {"foo": "bar"}


def test_persister_constructors(tmp_path: Path):
    task_list = TaskLister([])
    action_list = ActionLister([])

    # TaskListPersister with dirname
    tlp_dirname = TaskListPersister(task_list, dirname=str(tmp_path))
    assert tlp_dirname.dirname == str(tmp_path)
    assert tlp_dirname.filename == DEFAULT_TASK_LIST_FILE
    assert tlp_dirname.save_path == Path(tmp_path) / DEFAULT_TASK_LIST_FILE

    # TaskListPersister with filename
    tlp_filename = TaskListPersister(task_list, filename="custom_tasks.json")
    assert tlp_filename.filename == "custom_tasks.json"

    # ActionListPersister with dirname
    alp_dirname = ActionListPersister(action_list, dirname=str(tmp_path))
    assert alp_dirname.dirname == str(tmp_path)
    assert alp_dirname.filename == DEFAULT_ACTION_LIST_FILE
    assert alp_dirname.save_path == Path(tmp_path) / DEFAULT_ACTION_LIST_FILE

    # ActionListPersister with filename
    alp_filename = ActionListPersister(action_list, filename="custom_actions.json")
    assert alp_filename.filename == "custom_actions.json"


def test_file_task_repository_basic_and_persistence(tmp_path: Path):
    # create repo with no initial tasks
    from core import Task, TaskLister

    repo = FileTaskRepository(dirname=str(tmp_path))
    assert repo.list() == TaskLister([])

    t = Task(name="repo_task")
    repo.add(t)
    assert repo.get_by_name("repo_task") == t
    assert t in repo.list()

    # persist and load via new repo instance
    repo.save()
    repo2 = FileTaskRepository(dirname=str(tmp_path))
    repo2.load()
    task = repo2.get_by_name("repo_task")
    assert task is not None
    assert task.name == "repo_task"

    # remove
    repo2.remove(task)
    assert repo2.get_by_name("repo_task") is None


def test_file_action_repository_basic_and_filters(tmp_path: Path):
    from core import Task, Action, ActionLister
    from datetime import datetime, timezone, timedelta

    task = Task(name="t1")
    a1 = Action(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc), ref_task=task, name="a1"
    )
    a2 = Action(
        timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc), ref_task=task, name="a2"
    )

    repo = FileActionRepository(ActionLister([a1, a2]), dirname=str(tmp_path))
    assert a1 in repo.list()
    assert a2 in repo.list()

    # get_for_task should return both for the task
    res = repo.get_for_task(task)
    assert len(res) == 2

    # time filtering
    start = datetime(2024, 2, 1, tzinfo=timezone.utc)
    res2 = repo.get_for_task(task, start_time=start)
    assert len(res2) == 1
    assert res2[0].name == "a2"

    # get_by_time across repo
    start_all = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end_all = datetime(2024, 12, 31, tzinfo=timezone.utc)
    res_all = repo.get_by_time(start_all, end_all)
    assert len(res_all) == 2

    # ordered desc
    from core import Ordering

    res_ordered = repo.get_for_task(task, ordered=Ordering.DESC)
    assert res_ordered[0].timestamp >= res_ordered[1].timestamp

    # persist and load
    repo.save()
    repo2 = FileActionRepository(dirname=str(tmp_path))
    repo2.load()
    assert any(a.name == "a1" for a in repo2.list())
    assert any(a.name == "a2" for a in repo2.list())


def test_file_task_repository_returns_lister_on_list_and_load(tmp_path):
    """Ensure FileTaskRepository.list() and load() return TaskLister types."""
    repo = FileTaskRepository(dirname=str(tmp_path))
    assert isinstance(repo.list(), TaskLister)

    t = Task(name="repo_task")
    repo.add(t)
    repo.save()

    repo2 = FileTaskRepository(dirname=str(tmp_path))
    loaded = repo2.load()
    assert isinstance(loaded, TaskLister)
    assert loaded.get_task_by_name("repo_task") is not None


def test_get_by_name_returns_none_when_missing(tmp_path):
    """get_by_name should return None for missing task names."""
    repo = FileTaskRepository(dirname=str(tmp_path))
    assert repo.get_by_name("nope") is None
