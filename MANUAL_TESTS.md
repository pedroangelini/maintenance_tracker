# Manual test script

This script checks the CLI end to end using an isolated data directory, so it
does not affect your normal tracker. Run commands from the project root. If
the `mtnt` command is not installed, use `uv run python main.py` in place of
`mtnt` below.

```sh
export MTNT_TEST_DIR="$(mktemp -d)"
alias mtnt='uv run python main.py --config-dir "$MTNT_TEST_DIR"'
mtnt --help
```

Expected: help lists `add`, `record`, `list`, `get`, `edit`, `delete`, and
`report`.

## Create and inspect tasks

```sh
mtnt add task "Water plants" "2024-01-01 09:00" "7 days" "Water indoor plants"
mtnt add task "Replace filter" "2030-01-01 09:00" "0" "One-time task"
mtnt list tasks
mtnt get task "Water plants"
mtnt get tasks --name Water
mtnt list tasks --overdue
```

Expected: both tasks appear in the list; exact and partial lookup show the
expected task details. The one-time task reports no repeating interval.

To check the interactive flow, create a disposable task and answer the four
prompts with `Interactive task`, `now`, `1 day`, and `Created interactively`:

```sh
mtnt add task -i
mtnt edit task "Interactive task" -i
```

Expected: each command prompts only for missing values, and the edited task is
shown as successfully updated.

## Record, list, query, and delete actions

```sh
mtnt record run "Water plants" "Alex" --timestamp "2024-01-08 09:15" --action-name "weekly watering"
mtnt add action "Water plants" "Sam" --timestamp "2024-01-15 09:00" --action-name "second watering"
mtnt list actions
mtnt list actions "Water plants"
mtnt report actions --at 2024-01 --for "Water plants"
mtnt delete action "Water plants" --action-name "weekly watering"
mtnt list actions "Water plants"
```

Expected: both actions initially appear with their timestamps, names, and
actors. The monthly report contains both. After deletion, only `second
watering` remains.

Also delete by a time range, then confirm the filtered list is empty:

```sh
mtnt delete action "Water plants" --start-time "2024-01-15 00:00" --end-time "2024-01-15 23:59"
mtnt list actions "Water plants"
mtnt record run "Water plants" "Sam" --timestamp "2024-01-15 09:00" --action-name "second watering"
```

## Edit, reporting, and validation

```sh
mtnt edit task "Water plants" --rename "Water houseplants"
mtnt get task "Water houseplants"
mtnt report next --for "Water houseplants" --at "2024-01-16"
mtnt report tasks --between "2024-01-01" "2024-01-31"
mtnt report overdue --at "2024-02-01"
mtnt delete task "Water houseplants"
mtnt delete action "Water houseplants" --action-name "second watering"
mtnt delete task "Water houseplants"
```

Expected: renaming preserves the remaining action. `report next` shows the
next scheduled run, and the reports return matching data. The first task
deletion should fail because an action remains; after deleting that action,
the task deletion succeeds.

Also check errors deliberately:

```sh
mtnt add task "" now "1 day"
mtnt record run "does not exist"
mtnt delete action "Replace filter"
```

Expected: each command explains the failure without corrupting previously
saved tasks or actions. Finally, rerun `list tasks` and `list actions` to
confirm persistence and the expected final state.

## Test coverage

Run `uv run pytest --cov --cov-report=xml --cov-report=term-missing` to get both a nice terminal output and a xml file that works well with the "coverage gutters" vscode extension

see about reporting here 
[https://pytest-cov.readthedocs.io/en/latest/reporting.html]
