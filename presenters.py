"""Presentation helpers for CLI output (tables, JSON, CSV, rich formatting).

This module centralizes formatting so business logic and app code remain presentation-free.
"""

from __future__ import annotations

import csv
import json
import sys
from typing import Optional

from rich.table import Table
from rich.console import Console

import utils
from core import *


def _rich_task(t: Task) -> str:
    ret_str = f"Task: [bold]{t.name}[/bold]\n"
    if t.description:
        ret_str += f"[italic]{t.description}[/italic]\n"
    ret_str += f"starting on: {utils.human_date_str(t.start_time)}\n"
    ret_str += f"interval:    {utils.human_interval_str(t.interval)}\n"
    return ret_str


def _print_task_list_table(task_list: TaskLister, title: str = "Task List") -> None:
    table = Table(title=title)

    table.add_column("Name", justify="left", no_wrap=True)
    table.add_column("Description")
    table.add_column("Start Time", justify="right", style="green")
    table.add_column("Interval", justify="right", style="green")

    for t in task_list:
        table.add_row(
            t.name,
            t.description,
            utils.human_date_str(t.start_time),
            utils.human_interval_str(t.interval),
        )

    console = Console()
    console.print(table)


def _print_action_list_table(action_list: ActionLister) -> None:
    table = Table(title="Action List")

    table.add_column("Task", justify="left", no_wrap=True)
    table.add_column("Actor", justify="left", style="blue")
    table.add_column("Timestamp", justify="right", style="green")
    table.add_column("Action Name")

    for a in action_list:
        table.add_row(
            a.ref_task.name,
            a.actor,
            utils.human_date_str(a.timestamp),
            a.name,
        )

    console = Console()
    console.print(table)


def _output_task_list_json(task_list: TaskLister) -> None:
    """Output task list in JSON format"""
    tasks_data = []
    for t in task_list:
        tasks_data.append(
            {
                "name": t.name,
                "description": t.description,
                "start_time": t.start_time.isoformat() if t.start_time else None,
                "interval": str(t.interval) if t.interval else None,
            }
        )
    sys.stdout.write(json.dumps(tasks_data, indent=2) + "\n")


def _output_task_list_csv(task_list: TaskLister) -> None:
    """Output task list in CSV format"""
    writer = csv.writer(sys.stdout)
    writer.writerow(["Name", "Description", "Start Time", "Interval"])
    for t in task_list:
        writer.writerow(
            [
                t.name,
                t.description,
                t.start_time.isoformat() if t.start_time else "",
                str(t.interval) if t.interval else "",
            ]
        )


def _output_action_list_json(action_list: ActionLister) -> None:
    """Output action list in JSON format"""
    actions_data = []
    for a in action_list:
        actions_data.append(
            {
                "task": a.ref_task.name,
                "actor": a.actor,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                "action_name": a.name,
            }
        )
    sys.stdout.write(json.dumps(actions_data, indent=2) + "\n")


def _output_action_list_csv(action_list: ActionLister) -> None:
    """Output action list in CSV format"""
    writer = csv.writer(sys.stdout)
    writer.writerow(["Task", "Actor", "Timestamp", "Action Name"])
    for a in action_list:
        writer.writerow(
            [
                a.ref_task.name,
                a.actor,
                a.timestamp.isoformat() if a.timestamp else "",
                a.name,
            ]
        )
