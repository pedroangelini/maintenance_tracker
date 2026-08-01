# Refactoring for architectural niceties

Based on the architecture diagram and the actual file contents, I've identified several architectural inconsistencies:

### 1. **Business Logic in App Layer** (app.py)
The app layer should only coordinate between CLI and business logic, but it contains significant business logic:
- `get_tasks_by_time()` implements task filtering logic
- `get_actions_for_task_filtered()` implements complex action filtering
- `edit_action()` contains action editing logic

**Expected**: These should be in `maintenance_tracker.py`

### 2. **Persistence Logic in Business Layer** (maintenance_tracker.py)
The business layer handles persistence directly:
- `save()` method calls persister directly
- `__init__()` handles persistence initialization

**Expected**: Persistence should be abstracted in core.py

### 3. **Domain Model Concerns in CLI** (cli.py)
The CLI layer contains domain-specific logic:
- `_rich_task()` formats domain objects
- `_output_task_list_json()` handles domain object serialization

**Expected**: Domain presentation should be in app layer

### 4. **Missing Abstraction Boundaries**
- `app.py` directly accesses `MaintenanceTracker` internals (e.g., `tracker.task_list`)
- `main.py` configures `MaintenanceTracker` directly

### 5. **Inconsistent Error Handling**
- `core.py` uses custom exceptions (`TaskWithSameNameError`)
- `app.py` uses enum-based results (`ActionRecordResults`)
- `cli.py` uses ad-hoc string errors

### 6. **Data Access in Business Logic** (maintenance_tracker.py)
Business logic directly accesses data structures:
```python
def get_actions_for_task(...):
    return [action for action in self.action_list ...]  # Direct list access
```

**Expected**: Should use repository pattern from core.py

### 7. **Cross-Layer Dependencies**
- `app.py` imports from both `core.py` and `maintenance_tracker.py`
- `maintenance_tracker.py` imports from `core.py`
- `cli.py` imports from `app.py` and `core.py`

### Recommended Refactoring:
1. Move business logic from `app.py` to `maintenance_tracker.py`
2. Extract persistence operations to `core.py` Persister classes
3. Create presenter classes in `app.py` for CLI output formatting
4. Use dependency injection for `MaintenanceTracker`
5. Standardize error handling with custom exceptions
6. Implement proper repository pattern for data access

The most significant violation is the placement of business logic in the app layer, which should only serve as an orchestrator. The persistence handling in the business layer is also a major architectural concern.
