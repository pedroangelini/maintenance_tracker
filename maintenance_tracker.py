import logging
from core import *
from repository import TaskListPersister, ActionListPersister, FileTaskRepository, FileActionRepository
from enum import Enum
from datetime import datetime, timedelta, UTC

logger = logging.getLogger(__name__)


class ActionRecordResults(Enum):
    SUCCESS = 1  # all good, and task of this action matches the task already registered
    TASK_MISMATCH = 2  # action was recorded, but the task referenced in the action is not equals to the one already registered
    FAILURE = (
        0  # for some reason we couldn't add the task, but did not raise an exception
    )

class TaskRecordResults(Enum):
    SUCCESS = 1  # all good, and task of this action matches the task already registered
    FAILURE = 0  # for some reason we couldn't add the task, but did not raise an exception


class MaintenanceTracker:
    """maintenance_tracker sets up lists of tasks and actions related to those tasks.

    Supports dependency injection of task and action repositories while preserving
    backward-compatible attributes (task_list, action_list, task_list_saver, action_list_saver).
    """

    task_list: TaskLister
    action_list: ActionLister
    task_list_saver: TaskListPersister
    action_list_saver: ActionListPersister

    def __init__(
        self,
        load=False,
        save_dir=None,
        save_actions_file=None,
        save_task_file=None,
        task_repo=None,
        action_repo=None,
    ):
        logger.debug(
            f"Initializing tracker: {load =}, {save_dir = }, {save_actions_file = }, {save_task_file = }, {task_repo = }, {action_repo = }"
        )

        # If repositories were provided, use them; otherwise create file-backed repos.
        if task_repo is None:
            task_repo = FileTaskRepository(task_list=TaskLister([]), dirname=save_dir, filename=save_task_file)
        if action_repo is None:
            action_repo = FileActionRepository(action_list=ActionLister([]), dirname=save_dir, filename=save_actions_file)

        # expose repo objects
        self.task_repo = task_repo
        self.action_repo = action_repo

        # keep compatibility with old attribute names
        self.task_list = self.task_repo.list()
        self.action_list = self.action_repo.list()

        # expose persisters for backward compatibility/tests that reference them
        self.task_list_saver = getattr(self.task_repo, 'persister', None)
        self.action_list_saver = getattr(self.action_repo, 'persister', None)

        if load:
            # load via repositories
            if hasattr(self.task_repo, 'load'):
                self.task_repo.load()
            if hasattr(self.action_repo, 'load'):
                self.action_repo.load()

            logger.debug(
                f"loaded tasks from : {Path(self.task_list_saver.dirname) / Path(self.task_list_saver.filename)}"
            )
            logger.debug(
                f"num tasks: {len(self.task_list)}, num actions: {len(self.action_list)}"
            )

    def register_task(self, new_task: Task) -> TaskRecordResults:
        self.task_list.append(new_task)
        return TaskRecordResults.SUCCESS

    def record_run(self, new_action: Action) -> ActionRecordResults:
        """Records that an action was performed,
        Ensures the referenced task is in the task_list, and checks if the task in the
        task_list matches the one passed in the action

        Args:
            new_action (action): new action to be recorded

        Returns:
            ActionRecordResults: code with information about the registration result
              - FAILURE if could not add the action
              - TASK_MISMATCH if the action was added, but the task referenced in the
              action is not equals to the one in the task_list
              - SUCCESS if the action was added successfully with a matching task

        """
        ret_code = ActionRecordResults.FAILURE

        # check if we've seen this task before, if not, register it
        if self.task_list._check_task_name_available(new_action.ref_task.name):
            logger.info(
                f"adding an action to a task that did not exist before - {new_action.ref_task.name}"
            )
            self.register_task(new_action.ref_task)
        else:
            self.action_list.append(new_action)

            # warn the user if ref_task is different from the one in the list
            registered_task = self.task_list.get_task_by_name(new_action.ref_task.name)
            if registered_task == new_action.ref_task:
                ret_code = ActionRecordResults.SUCCESS
            else:
                ret_code = ActionRecordResults.TASK_MISMATCH

        return ret_code

    def get_actions_for_task(
        self, 
        target_task: Task, 
        start_time: datetime | None = None, 
        end_time: datetime | None = None,
        ordered: Ordering | bool = False
    ) -> ActionLister:
        """gets a list of actions for a given task within a time range"""
        result_list = [
            action
            for action in self.action_list
            if action.ref_task.name == target_task.name
        ]
        
        # Filter by time range if provided
        if start_time or end_time:
            if start_time is None:
                start_time = datetime.min.replace(tzinfo=UTC)
            if end_time is None:
                end_time = datetime.now(UTC)
                
            result_list = [
                action
                for action in result_list
                if start_time <= action.timestamp <= end_time
            ]
        
        # Order if requested
        if ordered:
            result_list = sorted(
                result_list,
                key=lambda a: a.timestamp,
                reverse=(ordered == Ordering.DESC),
            )

        return ActionLister(result_list)

    def get_actions_by_time(
        self, start_time: datetime, end_time: datetime | None = None
    ) -> ActionLister:
        """gets a list of actions within a given time range"""
        if end_time is None:
            end_time = datetime.now(UTC)

        result_list = [
            action
            for action in self.action_list
            if start_time <= action.timestamp <= end_time
        ]

        return ActionLister(result_list)

    def get_latest_task_run(
        self, tgt_task: Task, when: datetime | None = None
    ) -> Action | None:
        """Returns the most recent run of a task

        Args:
            tgt_task (task): the task we are looking for
            when (datetime): the time considered as "now" for this return

        Returns:
            action: the latest action of the the reference task
        """
        if when is None:
            when = datetime.now(UTC)

        actions = self.get_actions_for_task(tgt_task, ordered=Ordering.DESC)
        if len(actions) > 0:
            for a in actions:
                if a.timestamp > when:
                    continue
                return a

        return None

    def check_overdue(self, task: Task, when: datetime | None = None) -> bool:
        """Checks if a task is overdue.
        A task is overdue if we have not had an action run between the latest time the
        task was programmed before today
        Args:
            task (Task): the task to check for

        Returns:
            bool: whether the task is overdue
        """
        if when is None:
            when = datetime.now(UTC)

        last_programmed_time = task.get_programmed_time(-1, when)

        if last_programmed_time is None:
            # tasks without programmed time are never overdue
            return False

        last_run = self.get_latest_task_run(task, when)
        if last_run is None:
            return last_programmed_time < when

        return last_programmed_time < when and last_run.timestamp < last_programmed_time

    def time_since_last_exec(
        self, task: Task, when: datetime | None = None
    ) -> timedelta | None:
        """Gets a timedelta between "when" and the last action for this task

        Args:
            task (Task): target task
            when (datetime | None, optional): a timestamp to be used as now. Defaults to None.

        Returns:
            timedelta | None: timedelta since the last recorded task run. Returns None if no run has happened
        """
        if when is None:
            when = datetime.now(UTC)

        last_run = self.get_latest_task_run(task, when=when)

        if last_run is None:
            return None
        else:
            return when - last_run.timestamp

    def delete_task(self, task: Task) -> TaskRecordResults:
        """Deletes a task from the tracker, checking first to see if it has any actions depending on it

        Args:
            task (Task): the task to be deleted

        Returns:
            TaskRecordResults: SUCCESS or FAILURE depending on wether the task had actions attached to it
        """
        logger.debug(f"deleting task {task.name}")
        if dangling_actions := self.get_actions_for_task(task):
            logger.error(f"cannot delete task {task} because it has actions that depend on it")
            logger.debug(f"dangling actions: {dangling_actions}")
            return TaskRecordResults.FAILURE
        
        self.task_list.remove(task)
        return TaskRecordResults.SUCCESS

    def delete_run(self, action: Action) -> ActionRecordResults:
        """Deletes an action from the tracker

        Args:
            action (Task): the action to be deleted

        Returns:
            TaskRecordResults: only returns SUCCESS (otherwise fails ungracefully for now)
        """
        logger.debug(f"deleting action {action.ref_task.name}: {action.timestamp}")
        
        self.action_list.remove(action)
        return ActionRecordResults.SUCCESS


    def save(self) -> None:
        self.task_list_saver.save()
        self.action_list_saver.save()
