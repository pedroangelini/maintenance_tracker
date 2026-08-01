# Architecture Refactoring

## Current Architecture

### Initial Analysis

based on the file summaries, here's a simplified architecture diagram of the system:

```
CLI Interface (cli.py)
│
├─ User Commands
│  ├─ add [task|action]
│  ├─ list [tasks|actions]
│  ├─ get [task|tasks|action|actions]
│  ├─ edit [task|action]
│  ├─ delete [task|action]
│  ├─ report [overdue|next|tasks|actions]
│  └─ dashboard
│
└─ Core Application (app.py)
   │
   ├─ Task Management
   │  ├─ register_task()
   │  ├─ get_task_by_name()
   │  ├─ get_tasks_by_name()
   │  ├─ get_tasks_by_time()
   │  ├─ edit_task()
   │  └─ delete_task()
   │
   ├─ Action Management
   │  ├─ record_run()
   │  ├─ get_actions_for_task_filtered()
   │  ├─ get_action()
   │  ├─ edit_action()
   │  └─ delete_action()
   │
   ├─ Reporting
   │  ├─ get_overdue_tasks()
   │  ├─ get_next_runs()
   │  └─ get_actions_by_time()
   │
   └─ Data Access
      └─ MaintenanceTracker (maintenance_tracker.py)
         ├─ Task/Action persistence
         └─ Business logic
```

**Key Components:**
1. **CLI Layer** (cli.py): 
   - Handles user interactions via Typer commands
   - Formats output (tables/JSON/CSV)
   - Parses command arguments

2. **Application Layer** (app.py):
   - Public API for task/action operations
   - Coordinates between CLI and core logic
   - Handles request validation/translation

3. **Domain Model** (core.py):
   - `Task` and `Action` data classes
   - `TaskLister`/`ActionLister` containers
   - Persistence logic (`Persister` classes)
   - JSON serialization/deserialization

4. **Business Logic** (maintenance_tracker.py):
   - Implements core operations
   - Validation rules
   - Scheduling calculations
   - Overdue detection

5. **Supporting Modules**:
   - `config.py`: Manages application configuration
   - `utils.py`: Date/time parsing utilities
   - Tests: Comprehensive test coverage per component

**Data Flow:**
`CLI → app.py → MaintenanceTracker → Persister → JSON files`

The system follows a layered architecture with clear separation between presentation (CLI), application logic (app.py), and domain/business logic (core.py + maintenance_tracker.py).

### Full File Content Analysis

Based on the full contents of the files you've added, here's a simplified architecture diagram showing the key components and their relationships:

```
┌──────────────────────┐       ┌──────────────────────┐
│      CLI Layer       │       │     Utilities         │
│   (cli.py)           │       │   (utils.py)          │
│ - Typer commands     │       │ - Date parsing       │
│ - Output formatting  │───────▶ - Interval parsing    │
│ - User interaction   │       │ - Human formatting    │
└──────────────────────┘       └──────────────────────┘
         │                              ▲
         │                              │
         ▼                              │
┌──────────────────────┐       ┌──────────────────────┐
│   App Layer          │       │   Configuration      │
│   (app.py)           │       │   (config.py)         │
│ - Task operations    │───────▶ - App settings       │
│ - Action operations  │       │ - Data directory     │
│ - Reporting logic    │       └──────────────────────┘
└──────────────────────┘                 ▲
         │                                │
         ▼                                │
┌──────────────────────┐       ┌─────────┴──────────┐
│  Core Domain         │       │  Persistence Layer  │
│  (core.py)           │       │  (core.py)          │
│ - Task model         │◀──────│ - JSON serialization│
│ - Action model       │       │ - File I/O          │
│ - Validation logic   │       └─────────────────────┘
└──────────────────────┘
         │
         ▼
┌──────────────────────┐
│ Business Logic       │
│ (maintenance_tracker.py)
│ - Scheduling         │
│ - Overdue detection  │
│ - Run calculations   │
└──────────────────────┘
```

**Key Relationships:**

1. **CLI Layer**:
   - Depends on App Layer for operations
   - Uses Utilities for date/interval parsing
   - Formats output using Rich tables

2. **App Layer**:
   - Mediates between CLI and Core/Business Logic
   - Uses Configuration for settings
   - Depends on Utilities for date handling

3. **Core Domain**:
   - Contains fundamental data models (Task, Action)
   - Handles validation and business rules
   - Provides persistence through Persister classes

4. **Business Logic**:
   - Implements scheduling algorithms
   - Handles overdue detection
   - Calculates next runs

5. **Persistence**:
   - Handles JSON serialization/deserialization
   - Manages file I/O operations
   - Uses Configuration for storage paths

6. **Configuration**:
   - Centralized app settings
   - Manages data directory path
   - Initialized early in app lifecycle

7. **Utilities**:
   - Shared date/time functions
   - Human-readable formatting
   - Used by all other layers

The architecture follows a layered design with clear separation of concerns. The CLI handles user interaction, the App layer coordinates operations, the Core defines domain models, and the Business Logic contains specialized algorithms. Configuration and Utilities provide cross-cutting concerns used throughout the system.

## Architectural Review

Your architecture demonstrates a strong foundation in Separation of Concerns by properly decoupling user interaction (CLI Layer) from application coordination (App Layer). However, it deviates from ideal software design principles in two specific areas:

    Coupling Domain and Infrastructure: Placing both the Core Domain (data models/validation) and the Persistence Layer (JSON/File I/O) within the same core.py module violates the Single Responsibility Principle. Domain models should be completely agnostic to how they are saved or loaded. Persistence should be extracted into a dedicated infrastructure module (e.g., repository.py or storage.py).

    Inverted Dependency Flow: Your diagram indicates that the Core Domain points down to the Business Logic. In standard layered or Clean Architectures, the Core Domain must sit at the absolute center with zero outward dependencies. Business Logic (maintenance_tracker.py) should depend on and manipulate the Core models, not the other way around.

## Actions to improve Arch

Summary

The project generally follows layered design, but several practical issues reduce maintainability and testability. The recommendations below keep the existing structure but clarify responsibilities, remove direct coupling between domain and IO, and make behavior easier to test.

High-level goals
- Keep domain models (core.py) pure and independent from storage or presentation.
- Make MaintenanceTracker the canonical place for business rules and task/action operations.
- Move persistence to an infrastructure/repository layer and inject it into the tracker.
- Keep presentation (formatting/output) in the CLI or a dedicated presenter module — do not move it into the app orchestration layer.
- Standardize error/reporting using exceptions for control flow and reserve enums for status introspection only when needed.

Concrete recommendations (prioritized)

1) Move business logic out of app.py into MaintenanceTracker
- Methods in app.py that implement filtering, editing, or complex state mutation (get_tasks_by_time, get_actions_for_task_filtered, edit_action, edit_task logic that moves actions) should become methods on MaintenanceTracker (or small helper modules it uses).
- app.py should become a thin adapter that calls tracker methods and handles persistence triggers (save) and argument translation.

2) Extract persistence to an explicit repository/adapter layer (infrastructure)
- The persisters currently implemented in core.py should be moved to a dedicated module (e.g., storage.py or repository.py). Core domain objects remain in core.py; JSON encoder/decoder and file I/O belong to infra.
- Define interfaces (TaskRepository, ActionRepository) and make MaintenanceTracker accept repository instances (dependency injection). Provide a default factory for simple CLI use.

3) Use dependency injection for MaintenanceTracker initialization
- Do not hard-wire persisters inside MaintenanceTracker.__init__(). Accept optional repository/persister objects or factory callables so tests can inject in-memory doubles.
- Keep a small bootstrap in main.py (or app factory) that wires DI for the CLI run.

4) Keep presentation in cli.py or move to a dedicated presenter module
- _rich_task, JSON/CSV output helpers and table rendering belong to CLI/presenter code. If multiple frontends are expected, add presenters.py and have app.py call presenters when asked, but avoid business formatting in app.py.

5) Standardize error handling and result reporting
- Prefer custom exceptions for control-flow errors (e.g., DuplicateTaskError, TaskNotFoundError, ActionNotFoundError). Use exceptions to signal failures and let CLI map them to exit codes/messages.
- Optionally keep enums for non-exceptional return codes where callers need fine-grained result inspection.

6) Introduce repository pattern / read-model accessors
- Replace direct list iteration scattered across business code with repository method calls (e.g., repository.get_actions_for_task(task, start, end, ordered=True)). This centralizes filtering and allows optimized implementations later.

7) Tests and migration plan
- Add unit tests for tracker methods as they are moved. Use injected in-memory repositories to avoid file I/O during tests.
- Migrate incrementally: (a) add repository interfaces and adapters, (b) add tracker methods duplicating current app.py behavior, (c) switch app.py to call tracker methods, (d) remove old app.py implementations, (e) refactor persisters into infra.

Estimated effort
- Small incremental refactor: 1–3 days of focused work depending on desired thoroughness and test coverage. Can be broken into 3 small PRs: repository+DI; move tracker methods; cleanups & tests.

Next step
- If this plan looks good, proceed to implement the repository interfaces and move a small number of methods from app.py into MaintenanceTracker (record_run/get_actions_for_task_filtered) so behavior remains stable while enabling DI.

Notes
- Current code already contains JSON encoders/decoders and Persister classes in core.py; moving them to an infra module clarifies responsibilities (core.py then only defines domain types and listers).
- Do not move presentation formatting into app.py — keep the CLI as the presenter or add a presenters module.

