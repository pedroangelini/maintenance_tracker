# instantiate a tracker, executes the operations
# (add, edit, list, etc) and saves it the tracker


from maintenance_tracker import MaintenanceTracker, Task, Action, TaskLister
import logging

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


def get_all_tasks() -> TaskLister:
    global tracker
    logger.debug(tracker)
    logger.debug(tracker.task_list)
    logger.info(f"getting all tasks")
    logger.info(f"found {len(tracker.task_list)} tasks")
    return tracker.task_list
