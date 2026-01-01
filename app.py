# instantiate a tracker, executes the operations
# (add, edit, list, etc) and saves it the tracker


import logging
from datetime import datetime, timedelta
from typing import Optional


from maintenance_tracker import Action, MaintenanceTracker, Task, TaskLister, ActionRecordResults, TaskRecordResults

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
        end = datetime.now()
    
    if not start and end:
        start = datetime.min

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
        timestamp = datetime.now()

    action = Action(ref_task=task, timestamp=timestamp, name=action_name, actor=actor)
    result = tracker.record_run(action)
    if result == ActionRecordResults.SUCCESS:
        tracker.save()
    return result

def get_overdue_tasks() -> TaskLister:
    """Returns a list of overdue tasks."""
    global tracker
    overdue_tasks = TaskLister()
    for task in tracker.task_list:
        if tracker.check_overdue(task):
            overdue_tasks.append(task)
    return overdue_tasks

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





