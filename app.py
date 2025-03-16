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
    pass


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

