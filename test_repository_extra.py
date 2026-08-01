from repository import FileTaskRepository
from core import Task, TaskLister
from datetime import UTC, datetime


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
