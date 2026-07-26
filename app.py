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
    actions = tracker.get_actions_by_time(start_time, end_time)
    tasks = TaskLister()
    for action in actions:
        if action.ref_task not in tasks:
            tasks.append(action.ref_task)
    return tasks



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
    old_task : Task,
    changes: dict,
) -> Task:
    global tracker
    logger.debug(f"replacing old task: {old_task.name} (id: {id(old_task)})")
    new_task = old_task.replace(changes)
    logger.debug(f"with new task: {new_task.name} (id: {id(new_task)})")

    tracker.register_task(new_task)

    
    actions = tracker.get_actions_for_task(old_task)
    logger.debug(f"updating {len(actions)} actions to point to new task")
    for action in actions:
        new_action = action.replace({"ref_task":new_task})
        tracker.record_run(new_action)
        tracker.delete_run(action)
        logger.debug(f"updated {new_action.timestamp}")



    logger.debug("deleting old task")
    if tracker.delete_task(old_task) != TaskRecordResults.SUCCESS:
        logger.fatal("error editing (replacing) task - could not move the old actions to the new task")
        return None


    tracker.save()
    
    return new_task

def get_actions_for_task_filtered(
    task_name: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    action_name: str | None = None,
) -> ActionLister:
    global tracker
    task = get_task_by_name(task_name)
    if task is None:
        return ActionLister([])

    actions = tracker.get_actions_for_task(task)
    filtered_actions = ActionLister()

    if action_name:
        for action in actions:
            if action.name == action_name:
                filtered_actions.append(action)
        return filtered_actions

    start = start_time
    end = end_time

    if start and not end:
        end = datetime.now(UTC)
    
    if not start and end:
        start = datetime.min.replace(tzinfo=UTC)

    for action in actions:
        if start and action.timestamp < start:
            continue
        if end and action.timestamp > end:
            continue
        filtered_actions.append(action)

    return filtered_actions

def record_run(
    task_name: str,
    timestamp: datetime | None = None,
    action_name: str = "",
    actor: str = "",
) -> ActionRecordResults:
    """Records an action for a given task."""
    global tracker
    task = get_task_by_name(task_name)
    if task is None:
        return ActionRecordResults.FAILURE

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
    """Deletes a task."""
    global tracker
    task = get_task_by_name(task_name)
    if task is None:
        return TaskRecordResults.FAILURE
    
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
    """Edits an action. Returns the updated action or None if not found."""
    global tracker
    
    # Find the action to edit
    actions_to_edit = []
    try:
        # Try parsing as timestamp first
        timestamp = utils.parse_date(action_ref)
        action = get_action(task_name, timestamp)
        if action:
            actions_to_edit.append(action)
    except Exception:
        # If timestamp parsing fails, try as action name
        action_list = get_actions_for_task_filtered(task_name, action_name=action_ref)
        actions_to_edit = list(action_list)
    
    if len(actions_to_edit) == 0:
        return None
    elif len(actions_to_edit) > 1:
        raise ValueError(f"Multiple actions found matching '{action_ref}'. Please provide a timestamp for disambiguation.")
    
    old_action = actions_to_edit[0]
    
    # Build the updated action
    updated_fields = {}
    if new_actor is not None:
        updated_fields['actor'] = new_actor
    if new_timestamp is not None:
        updated_fields['timestamp'] = new_timestamp
    if new_action_name is not None:
        updated_fields['name'] = new_action_name
    if new_task_name is not None:
        new_task = get_task_by_name(new_task_name)
        if new_task is None:
            raise ValueError(f"Task '{new_task_name}' not found")
        updated_fields['ref_task'] = new_task
    
    new_action = old_action.replace(updated_fields)
    
    # Delete old action and add new one
    tracker.delete_run(old_action)
    result = tracker.record_run(new_action)
    
    if result in [ActionRecordResults.SUCCESS, ActionRecordResults.TASK_MISMATCH]:
        tracker.save()
        return new_action
    
    return None
