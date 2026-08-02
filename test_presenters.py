import csv
import json
import datetime
from datetime import UTC

from core import Task, Action, TaskLister, ActionLister
import presenters


def test_rich_task_contains_fields():
    t = Task(
        "TName",
        description="Desc",
        start_time=datetime.datetime(2024, 1, 2, 10, 0, tzinfo=UTC),
        interval=datetime.timedelta(days=7),
    )
    out = presenters._rich_task(t)
    assert "TName" in out
    assert "Desc" in out
    assert "2024" in out


def test_output_task_list_json_and_csv(capsys):
    t = Task(
        "TaskJson",
        description="d",
        start_time=datetime.datetime(2024, 1, 1, tzinfo=UTC),
        interval=datetime.timedelta(days=1),
    )
    tl = TaskLister([t])
    presenters._output_task_list_json(tl)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert data[0]["name"] == "TaskJson"

    # CSV
    presenters._output_task_list_csv(tl)
    out_csv = capsys.readouterr().out
    rows = list(csv.reader(out_csv.splitlines()))
    assert rows[0] == ["Name", "Description", "Start Time", "Interval"]
    assert rows[1][0] == "TaskJson"


def test_output_action_list_json_and_csv(capsys):
    t = Task("Task1")
    a = Action(
        timestamp=datetime.datetime(2024, 1, 1, tzinfo=UTC),
        ref_task=t,
        name="act",
        actor="me",
    )
    al = ActionLister([a])

    presenters._output_action_list_json(al)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data[0]["task"] == "Task1"
    assert data[0]["action_name"] == "act"

    presenters._output_action_list_csv(al)
    out_csv = capsys.readouterr().out
    rows = list(csv.reader(out_csv.splitlines()))
    assert rows[0] == ["Task", "Actor", "Timestamp", "Action Name"]
    assert rows[1][0] == "Task1"


def test_print_task_and_action_tables(capsys):
    t = Task("TableTask", description="d")
    tl = TaskLister([t])
    presenters._print_task_list_table(tl, title="TList")
    out = capsys.readouterr().out
    assert "TableTask" in out

    a = Action(
        timestamp=datetime.datetime(2024, 1, 2, tzinfo=UTC),
        ref_task=t,
        name="doit",
        actor="me",
    )
    al = ActionLister([a])
    presenters._print_action_list_table(al)
    out2 = capsys.readouterr().out
    assert "doit" in out2
    assert "TableTask" in out2
