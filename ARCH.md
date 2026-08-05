# Architectural Review

## Overview
The Maintenance Tracker (`mtnt`) is a command-line application for tracking recurring tasks and their executions (actions). The codebase follows a layered architecture with clear separation of concerns: domain models, repository/persistence, business logic (service), application façade, presentation, and CLI. Recent changes introduce explicit repository interfaces, dependency injection, and a presenter layer to decouple formatting from business logic.

---

## Layer Diagram

```
+-------------------+
|      CLI          |  (cli.py, main.py)  – Typer command parsing, user interaction
+-------------------+
        |
        v
+-------------------+
|   Application     |  (app.py)             – Global tracker instance, thin façade functions
+-------------------+
        |
        v
+-------------------+
|   Service         |  (maintenance_tracker.py) – MaintenanceTracker orchestrates use-cases
+-------------------+
        |
        v
+-------------------+       +-------------------+
|   Domain          |       |   Repository      |  (repository.py)
|   (core.py)       |<----->|   (interfaces +   |
| Task, Action,     |       |    file impl.)    |
| TaskLister,       |       |  TaskRepository,  |
| ActionLister      |       |  ActionRepository |
+-------------------+       +-------------------+
        |
        v
+-------------------+
|   Persistence     |  (repository.py) – Persister, JSON encoder/decoder, file I/O
+-------------------+
```

---

## Component Responsibilities

### 1. Domain Models (`core.py`)
- **Task** – Immutable (`frozen=True`) dataclass representing a recurring task.
  - Fields: `name`, `description`, `start_time`, `interval`.
  - Behavior: `get_programmed_time`, `get_all_programmed_times`, `replace`.
- **Action** – Immutable dataclass recording a task execution.
  - Fields: `timestamp`, `ref_task` (Task), `name`, `description`, `actor`.
  - Behavior: `replace`.
- **TaskLister** – `UserList` subclass enforcing unique task names; provides query helpers (`get_task_by_name`, `get_next_tasks_due_period`, `get_all_tasks_due_period`).
- **ActionLister** – `UserList` subclass with value-based equality (order-independent, timestamp-sorted).
- **Ordering** – Enum (`ASC`, `DESC`) for sort direction.

### 2. Repository Interfaces (`repository.py`)
- **TaskRepository** (ABC) – Contract: `list()`, `get_by_name()`, `add()`, `remove()`, `save()`, `load()`.
- **ActionRepository** (ABC) – Contract: `list()`, `add()`, `remove()`, `get_for_task()`, `get_by_time()`, `save()`, `load()`.
- **FileTaskRepository** – File-backed implementation using `TaskListPersister`.
- **FileActionRepository** – File-backed implementation using `ActionListPersister`.
- Both concrete repos mutate an internal `TaskLister`/`ActionLister` and delegate serialization to persisters.

### 3. Persistence (`repository.py`)
- **Persister** – Base class handling `save()`/`load()` to a JSON file.
- **TaskListPersister** / **ActionListPersister** – Configure default paths.
- **MtnTrackerJSONEncoder** – Serializes `datetime`, `timedelta`, and dataclasses (Task, Action) with `__type__` metadata.
- **MtnTrackerJSONDecoder** – Rehydrates the above types via `object_hook`.

### 4. Service Layer (`maintenance_tracker.py`)
- **MaintenanceTracker** – Central coordinator.
  - Accepts optional `task_repo`/`action_repo` for DI (defaults to file repos).
  - Exposes backward-compatible attributes: `task_list`, `action_list`, `task_list_saver`, `action_list_saver`.
  - Business methods:
    - `register_task`, `record_run` (with `ActionRecordResults` enum).
    - `get_actions_for_task`, `get_actions_by_time`.
    - `get_latest_task_run`, `check_overdue`, `time_since_last_exec`.
    - `delete_task` (raises `DanglingActionsError`), `delete_run`.
    - `edit_task` (replace task + migrate actions), `edit_action`.
    - `save()` – persists both repos.
  - Helper methods moved from `app.py`: `get_tasks_by_time`, `get_actions_for_task_filtered`.

### 5. Application Façade (`app.py`)
- Global `tracker: MaintenanceTracker` instance.
- Thin functions delegating to tracker: `register_task`, `get_task_by_name`, `get_tasks_by_name`, `get_tasks_by_time`, `get_all_tasks`, `get_all_actions`, `edit_task`, `get_actions_for_task_filtered`, `record_run`, `get_overdue_tasks`, `get_next_runs`, `get_actions_by_time`, `delete_task`, `delete_action`, `get_action`, `edit_action`.
- Each function calls `tracker.save()` on mutating operations.

### 6. Presentation (`presenters.py`)
- **Rich formatting**: `_rich_task`, `_print_task_list_table`, `_print_action_list_table`.
- **JSON output**: `_output_task_list_json`, `_output_action_list_json`.
- **CSV output**: `_output_task_list_csv`, `_output_action_list_csv`.
- All functions accept `TaskLister`/`ActionLister` and write to `stdout`; no business logic.

### 7. CLI (`cli.py`, `main.py`)
- **main.py** – Typer app entry point, config initialization, tracker instantiation, default dashboard.
- **cli.py** – Command groups: `add`, `record`, `list`, `get`, `edit`, `delete`, `report`.
  - Each command parses args, calls `app.*` functions, uses presenters for output.
  - Interactive prompts via Typer for missing args.
  - Error handling maps domain exceptions to user-friendly messages and exit codes.

### 8. Configuration (`config.py`)
- **Configuration** class – Loads `mtnt_config.json` from app dir (or `--config_dir`).
- Manages `data_dir` (relative paths resolved against config dir), `debug_logging`.
- Singleton `config` instance used by `main.py`.

### 9. Utilities (`utils.py`, `errors.py`)
- **utils.py** – Date/interval parsing (`parse_date`, `parse_interval`, `parse_partial_timestamp`), rounding, human-readable formatting.
- **errors.py** – Domain exceptions: `MaintenanceTrackerError`, `TaskNotFoundError`, `DuplicateTaskError`, `ActionNotFoundError`, `DanglingActionsError`.

---

## Data Flow Example: Recording a Run
1. User runs `mtnt record run "vacuum" "Alice" --timestamp "2024-05-15T10:00"`.
2. `cli.record_run` parses args → calls `app.record_run(task_name, timestamp, action_name, actor)`.
3. `app.record_run` fetches `Task` via `tracker.task_list.get_task_by_name`.
4. Creates `Action(ref_task=task, timestamp=..., name=..., actor=...)`.
5. Calls `tracker.record_run(action)` → `MaintenanceTracker.record_run`:
   - If task unknown, registers it via `task_repo.add`.
   - Adds action via `action_repo.add`.
   - Returns `ActionRecordResults`.
6. On success, `app.record_run` calls `tracker.save()` → repos persist to JSON.
7. CLI prints success message via Rich.

---

## Strengths
- **Clear layering** – Domain, persistence, service, app, presentation, CLI are distinct.
- **Dependency injection** – `MaintenanceTracker` accepts repo implementations, enabling testing and future back-ends.
- **Immutable domain models** – `frozen=True` dataclasses prevent accidental mutation; changes via `replace`.
- **Repository pattern** – Abstracts storage, making it trivial to swap JSON for SQLite/PostgreSQL.
- **Presenter isolation** – Output formatting is completely separate from business logic.
- **Comprehensive test suite** – Unit tests for domain, repositories, tracker, presenters, CLI, utils, config.

---

## Areas for Improvement
| Area | Recommendation |
|------|----------------|
| **Global tracker instance** | `app.tracker` is a module-level singleton; consider passing tracker explicitly or using a context object for better testability. |
| **Error handling granularity** | Current exceptions are good; add `ValidationError` and `PersistenceError` subclasses for caller differentiation. |
| **Input validation** | Validation lives in CLI (Typer) and `utils.parse_*`; move core validation into service layer to support non-CLI consumers. |
| **Concurrency** | File persisters are not thread-safe; add file locking or migrate to a DB backend for multi-process safety. |
| **Configuration overrides** | `Configuration.init_config` writes defaults to disk; provide a programmatic override path without file I/O. |
| **Type hints** | Some `Any` and `Optional` usages could be tightened (e.g., `TaskLister` vs `Sequence[Task]`). |
| **Documentation** | Auto-generate API docs (Sphinx/pdoc) from docstrings; keep README in sync with CLI help. |

---

## Future Extensibility
- **Alternative storage** – Implement `TaskRepository`/`ActionRepository` for SQL, Redis, etc.
- **Web UI** – Reuse `MaintenanceTracker` and presenters (JSON) behind a FastAPI/Flask layer.
- **Recurrence rules** – Replace custom interval logic with `dateutil.rrule` for complex schedules.
- **Tags/filters** – Extend `Task` with `tags: list[str]` and add query methods to `TaskRepository`.
- **Export** – Add iCalendar export via new presenter functions.

---

## Conclusion
The codebase exhibits a mature, well-structured architecture with strong separation of concerns. The introduction of repository interfaces and a presenter layer significantly improves maintainability and testability. Addressing the highlighted improvement areas will further harden the system for production use and future growth.

--- 

*Generated from source code review of the `mtnt` codebase.*
