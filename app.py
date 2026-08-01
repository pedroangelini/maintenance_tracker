# instantiate a tracker, executes the operations
# (add, edit, list, etc) and saves it the tracker


import logging
from datetime import datetime, timedelta, UTC
from typing import Optional


from maintenance_tracker import Action, MaintenanceTracker, Task, TaskLister, ActionRecordResults, TaskRecordResults, ActionLister

# log config
logger = logging.getLogger(__name__)


tracker: MaintenanceTracker = MaintenanceTracker()
logger.debug(f"{tracker}")


def register_task(new_task, save=True) -> None:
    global tracker
    logger.debug(tracker)
    logger.info(f"Adding task {new_task}")
    tracker.register_task(new_task)
    logger.info(f"Saving tracker to {tracker.task_list_saver.dirname}")

    tracker.save()


def get_task_by_name(task_name: str) -> Task | None:
    global tracker
    logger.debug(tracker)
    logger.info(f"getting task named {task_name}")
    return tracker.task_list.get_task_by_name(task_name)


def get_tasks_by_name(search_string: str) -> TaskLister:
    global tracker
    ret_list = TaskLister()
    logger.info(f"getting task named {search_string}")
    for task in tracker.task_list:
        if search_string in task.name:
            ret_list.append(task)
    return ret_list


def get_tasks_by_time(
    start_time: datetime, end_time: datetime | None = None
) -> TaskLister:
    global tracker
    return tracker.get_tasks_by_time(start_time, end_time)



def get_all_tasks() -> TaskLister:
    global tracker
    logger.debug(tracker)
    logger.debug(tracker.task_list)
    logger.info(f"getting all tasks")
    logger.info(f"found {len(tracker.task_list)} tasks")
    return tracker.task_list


def get_all_actions() -> ActionLister:
    global tracker
    logger.debug(tracker)
    logger.info(f"getting all actions")
    logger.info(f"found {len(tracker.action_list)} actions")
    return tracker.action_list


def edit_task(
    old_task: Task,
    changes: dict,
) -> Task | None:
    """Delegate task replacement to the tracker and persist on success."""
    global tracker
    new_task = tracker.edit_task(old_task, changes)
    if new_task:
        tracker.save()
    return new_task
def get_actions_for_task_filtered(
    task_name: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    action_name: str | None = None,
) -> ActionLister:
    global tracker
    return tracker.get_actions_for_task_filtered(task_name, start_time, end_time, action_name)

def record_run(
    task_name: str,
    timestamp: datetime | None = None,
    action_name: str = "",
    actor: str = "",
) -> ActionRecordResults:
    """Records an action for a given task.

    Raises TaskNotFoundError when the provided task_name does not exist.
    Returns an ActionRecordResults enum indicating success or mismatch.
    """
    global tracker
    task = get_task_by_name(task_name)
    if task is None:
        # Prefer exceptions for missing resources
        from errors import TaskNotFoundError

        raise TaskNotFoundError(f"Task '{task_name}' not found")

    if timestamp is None:
        timestamp = datetime.now(UTC)

    action = Action(ref_task=task, timestamp=timestamp, name=action_name, actor=actor)
    result = tracker.record_run(action)
    if result == ActionRecordResults.SUCCESS:
        tracker.save()
    return result

def get_overdue_tasks(at: datetime | None = None) -> TaskLister:
    """Returns a list of overdue tasks at a specific time."""
    global tracker
    overdue_tasks = TaskLister()
    for task in tracker.task_list:
        if tracker.check_overdue(task, at):
            overdue_tasks.append(task)
    return overdue_tasks

def get_next_runs(for_task: str | None = None, at: datetime | None = None) -> list[tuple[Task, datetime]]:
    """Gets next runs for tasks"""
    global tracker
    next_runs = []
    
    if for_task:
        task = tracker.task_list.get_task_by_name(for_task)
        if task:
            next_run = task.get_programmed_time(n=1, when=at)
            if next_run:
                next_runs.append((task, next_run))
    else:
        for task in tracker.task_list:
            next_run = task.get_programmed_time(n=1, when=at)
            if next_run:
                next_runs.append((task, next_run))
    
    return next_runs

def get_actions_by_time(start_time: datetime, end_time: datetime, task_name: str | None = None) -> ActionLister:
    """Gets actions within a time range, optionally filtered by task"""
    global tracker
    if task_name:
        task = tracker.task_list.get_task_by_name(task_name)
        if not task:
            return ActionLister([])
        return tracker.get_actions_for_task(task, start_time, end_time)
    else:
        return tracker.get_actions_by_time(start_time, end_time)

def delete_task(task_name: str) -> TaskRecordResults:
    """Deletes a task.

    Raises TaskNotFoundError if task does not exist, or propagates DanglingActionsError from tracker.
    Returns TaskRecordResults.SUCCESS on success.
    """
    global tracker
    task = get_task_by_name(task_name)
    if task is None:
        from errors import TaskNotFoundError

        raise TaskNotFoundError(f"Task '{task_name}' not found")

    result = tracker.delete_task(task)
    if result == TaskRecordResults.SUCCESS:
        tracker.save()
    return result

def delete_action(
    task_name: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    action_name: str | None = None,
) -> int:
    global tracker
    
    actions_to_delete = get_actions_for_task_filtered(task_name, start_time, end_time, action_name)
    
    deleted_count = 0
    for action in actions_to_delete:
        tracker.delete_run(action)
        deleted_count += 1
    
    if deleted_count > 0:
        tracker.save()
            
    return deleted_count


def get_action(task_name: str, timestamp: datetime) -> Action | None:
    """Gets an action by task name and timestamp."""
    global tracker
    task = get_task_by_name(task_name)
    if task is None:
        return None
    
    actions = tracker.get_actions_for_task(task)
    for action in actions:
        if action.timestamp == timestamp:
            return action
    return None







def edit_action(
    task_name: str,
    action_ref: str,
    new_actor: str | None = None,
    new_timestamp: datetime | None = None,
    new_action_name: str | None = None,
    new_task_name: str | None = None,
) -> Action | None:
    """Delegate action editing to the tracker and persist on success."""
    global tracker
    new_action = tracker.edit_action(
        task_name,
        action_ref,
        new_actor=new_actor,
        new_timestamp=new_timestamp,
        new_action_name=new_action_name,
        new_task_name=new_task_name,
    )
    if new_action:
        tracker.save()
    return new_action
