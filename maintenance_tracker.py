import logging
import utils
from core import *
from repository import (
    TaskListPersister,
    ActionListPersister,
    FileTaskRepository,
    FileActionRepository,
)
from enum import Enum
from datetime import datetime, timedelta, UTC
from errors import DuplicateTaskError, DanglingActionsError
from typing import Optional

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
    task_list_saver: Optional[TaskListPersister]
    action_list_saver: Optional[ActionListPersister]

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
        """Register a new task.

        Raises DuplicateTaskError if a task with the same name already exists.
        Returns TaskRecordResults.SUCCESS on success.
        """
        try:
            self.task_list.append(new_task)
        except Exception as e:
            # Normalize TaskWithSameNameError from core.TaskLister to DuplicateTaskError
            raise DuplicateTaskError(str(e)) from e
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

        # check if we've seen this task before
        if self.task_repo.get_by_name(new_action.ref_task.name) is None:
            logger.info(
                f"adding an action to a task that did not exist before - {new_action.ref_task.name}"
            )
            # register the referenced task, then still record the action
            self.register_task(new_action.ref_task)
            try:
                self.action_repo.add(new_action)
                ret_code = ActionRecordResults.SUCCESS
            except Exception:
                # keep original failure semantics if add fails
                ret_code = ActionRecordResults.FAILURE
        else:
            # task is already registered, add action via repository
            self.action_repo.add(new_action)

            # warn the user if ref_task is different from the one in the repo
            registered_task = self.task_repo.get_by_name(new_action.ref_task.name)
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
        ordered: Ordering | None = None,
    ) -> ActionLister:
        """gets a list of actions for a given task within a time range"""
        # Delegate to action repository to retrieve actions for the task
        try:
            result = self.action_repo.get_for_task(target_task, start_time=start_time, end_time=end_time, ordered=ordered)
        except TypeError:
            # Some repositories might not accept keyword args; fallback to positional
            result = self.action_repo.get_for_task(target_task, start_time, end_time, ordered)

        # Ensure we return an ActionLister
        if isinstance(result, ActionLister):
            return result
        else:
            return ActionLister(list(result))

    def get_actions_by_time(
        self, start_time: datetime, end_time: datetime | None = None
    ) -> ActionLister:
        """gets a list of actions within a given time range"""
        if end_time is None:
            end_time = datetime.now(UTC)

        # Delegate to action repository
        try:
            result = self.action_repo.get_by_time(start_time, end_time)
        except TypeError:
            result = self.action_repo.get_by_time(start_time, end_time)

        if isinstance(result, ActionLister):
            return result
        else:
            return ActionLister(list(result))

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
            TaskRecordResults: SUCCESS on success

        Raises:
            DanglingActionsError: when the task has dependent actions and cannot be deleted
        """
        logger.debug(f"deleting task {task.name}")
        if dangling_actions := self.get_actions_for_task(task):
            logger.error(f"cannot delete task {task} because it has actions that depend on it")
            logger.debug(f"dangling actions: {dangling_actions}")
            raise DanglingActionsError(
                f"Task '{task.name}' has {len(dangling_actions)} action(s) and cannot be deleted"
            )

        # Remove via repository
        self.task_repo.remove(task)
        return TaskRecordResults.SUCCESS

    def delete_run(self, action: Action) -> ActionRecordResults:
        """Deletes an action from the tracker

        Args:
            action (Task): the action to be deleted

        Returns:
            TaskRecordResults: only returns SUCCESS (otherwise fails ungracefully for now)
        """
        logger.debug(f"deleting action {action.ref_task.name}: {action.timestamp}")
        
        # Delegate delete to action repository
        self.action_repo.remove(action)
        return ActionRecordResults.SUCCESS


    # --- Business helper methods moved from app.py ---
    def get_tasks_by_time(self, start_time: datetime, end_time: datetime | None = None) -> TaskLister:
        """Returns tasks that have actions in a given time range."""
        actions = self.get_actions_by_time(start_time, end_time)
        tasks = TaskLister()
        for action in actions:
            if action.ref_task not in tasks:
                tasks.append(action.ref_task)
        return tasks


    def get_actions_for_task_filtered(
        self,
        task_name: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        action_name: str | None = None,
    ) -> ActionLister:
        """Return actions for a task filtered by time range and/or action name.

        This mirrors the filtering behavior previously implemented in app.py but
        keeps the actual business logic inside the tracker domain.
        """
        task = self.task_list.get_task_by_name(task_name)
        if task is None:
            return ActionLister([])

        actions = self.get_actions_for_task(task)
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


    def edit_task(self, old_task: Task, changes: dict) -> Task | None:
        """Replace a task and move existing actions to the new task.

        Returns the new task on success, or None on failure.
        """
        logger.debug(f"replacing old task: {old_task.name} (id: {id(old_task)})")
        new_task = old_task.replace(changes)
        logger.debug(f"with new task: {new_task.name} (id: {id(new_task)})")

        # register the new task
        self.register_task(new_task)

        # move actions to the new task
        actions = self.get_actions_for_task(old_task)
        logger.debug(f"updating {len(actions)} actions to point to new task")
        for action in actions:
            new_action = action.replace({"ref_task": new_task})
            self.record_run(new_action)
            self.delete_run(action)
            logger.debug(f"updated {new_action.timestamp}")

        logger.debug("deleting old task")
        # delete_task will raise DanglingActionsError if it cannot be deleted
        try:
            self.delete_task(old_task)
        except DanglingActionsError:
            logger.fatal("error editing (replacing) task - could not move the old actions to the new task")
            raise

        return new_task


    def edit_action(
        self,
        task_name: str,
        action_ref: str,
        new_actor: str | None = None,
        new_timestamp: datetime | None = None,
        new_action_name: str | None = None,
        new_task_name: str | None = None,
    ) -> Action | None:
        """Edit an action identified by a timestamp or name. Returns the updated action or None."""
        # Find the action to edit
        actions_to_edit = []
        try:
            # Try parsing as timestamp first
            timestamp = utils.parse_date(action_ref)
            action = self.get_actions_for_task(self.task_list.get_task_by_name(task_name))
            # get_action-like behavior: find exact timestamp match
            for a in action:
                if a.timestamp == timestamp:
                    actions_to_edit.append(a)
        except Exception:
            # If timestamp parsing fails, try as action name
            action_list = self.get_actions_for_task_filtered(task_name, action_name=action_ref)
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
            new_task = self.task_list.get_task_by_name(new_task_name)
            if new_task is None:
                raise ValueError(f"Task '{new_task_name}' not found")
            updated_fields['ref_task'] = new_task

        new_action = old_action.replace(updated_fields)

        # Delete old action and add new one
        self.delete_run(old_action)
        result = self.record_run(new_action)

        if result in [ActionRecordResults.SUCCESS, ActionRecordResults.TASK_MISMATCH]:
            return new_action

        return None


    def save(self) -> None:
        self.task_list_saver.save()
        self.action_list_saver.save()
