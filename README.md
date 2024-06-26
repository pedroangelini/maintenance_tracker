# Maintenance Tracker

Tracker for maintenance of any sort of repetitive task
The initial use case is to track when we last vacuumed the house, change the car oil, washed the dog's bed, etc, but it should

## General Naming and models

### Tasks

Tasks are things you need to do with a certain recurrence, for example: _clean the inside of your PC every 6 months_. They have:

- **Name**: Name of the task. Is unique to the task at hand (no two tasks with the same name), can be a string of any length, but it is recommended to use short strings as they are typed frequently. The app trims (str.strip()) whitespace at start and end of the name.
- **Start Time**: Time of the first expected run of this task
- **Periodicity**: How often the task needs to be repeated (ie: every 5 days, every 10 seconds, etc). Periodicity is optional: if it's empty or zero, it means the task is executed only once.
- **Description**: String describing the task

### Action

The record of a task being executed. It has:

- **Task**: reference of the task that has been executed (will be unique per task)
- **Timestamp**: the time of the execution
- **Name**: Optional name/description of the run. Can be used to refer to this run later, but does not have to be unique. In case you try to do something with a run referring by a non-unique action name, the app will prompt you to clarify which one you mean.
- **Actor**: a free string with the name of the person who executed the task.

## Storage

Data and configurations are stored in the default app folder for your platform (in windows it defaults to `C:\Users\<username>\AppData\Roaming\mtnt`), as JSON files. These files can be directly edited, although the app will not check for consistency and weird behavior can happen if the files are corrupted. To back up the files, simply copy or synchronize the folder to your backup location.

A different configuration folder can be passed using the option --config_dir

## Configuration

Configurations are saved in the file `mtnt_config.json`

Available configurations
| Config Entry | Default Value | Description |
|---------------|:-------------:|-------------|
| data_dir | '.' | The directory to save data. If this is a relative directory, it will be based on the config_dir |
| debug_logging | false | If true, enables even more console messages than the --verbose option |

### Date & time formats

Even though all date times are stored as UTC internally, anytime the app interacts with the user it converts the date and time to the local timezone (as defined by the local machine timezone).

Date and time's default format is `YYYY-MM-DDThh:mm` and local timezone is assumed.

Periodicity can be specified in multiple units, such as 10min, 10days. If no unit is defined (ie, a single number is passed) the app assumes days. The complete list of units can be found below (they are **case sensitive**):

- min, mins, minute, minutes
- h, hour, hours
- D, Day, Days, d, day, days
- M, Month, Months, month, months
- Y, Year, Years, year, years

If the app cannot determine the periodicity of a specific part, it will still try to parse the rest of the string, and get the periodicity from there. It will print an error to stderr and exit with error. If it cannot find any periodicity, it will not register the task, and exit with error code 30, and if it gets a partial match, will register the task and exit with error code 31.

## CLI Usage

_inspired by [timetrace, by Dominik Braun](https://github.com/dominikbraun/timetrace)_

_using Typer library_

### Summary of commands & Subcommands

```
mtnt [--verbose] [--config_dir <non-default-dir>]
 |-- add
 |    |-- task
 |    |-- action           # (same as mtnt record)
 |-- record [run]
 |-- list
 |    |-- tasks
 |    |-- actions
 |-- get
 |    |-- tasks
 |    |-- task
 |    |-- actions
 |    |-- action
 |-- edit
 |    |-- task
 |    |-- action
 |-- delete
 |    |-- task
 |    |-- action
 |-- report
      |-- overdue
      |-- next [run]
      |-- tasks
      |-- actions
```

### Global Options

- `--verbose` - show info logs
- `--config_dir` - sets a different configuration directory

### Add a task to the list:

`mtnt add task [-i| --interactive | <task_name> <start_time> <periodicity> <description>]`

| Argument              | Description                                                                                                   |
| --------------------- | ------------------------------------------------------------------------------------------------------------- |
| `-i`, `--interactive` | CLI will prompt for the parameters that were not passed. If no other arguments are passed, CLI will assume -i |
| `task_name`           | The name of the task                                                                                          |
| `start_time`          | Date time of the start                                                                                        |
| `periodicity`         | How often should the task repeat                                                                              |
| `description`         | A free text description for the task                                                                          |

### Record the run of a task

`mtnt record [run] <task_name> [now|<action_timestamp>] <action_name> <actor>`

or

`mtnt add action <task_name> [now|<action_timestamp>] <action_name> <actor>`

| Argument           | Description                           |
| ------------------ | ------------------------------------- |
| `run`              | optional, doesn't do anything         |
| `task_name`        | The name of the task                  |
| `action_timestamp` | The time the action was executed      |
| `action_name`      | A name for the action (optional)      |
| `actor`            | name of the person who did the action |

### List tasks

`mtnt list tasks`

No arguments

### List actions optionally for a single task

`mtnt list actions [<task_name>]`

| Argument    | Description          |
| ----------- | -------------------- |
| `task_name` | The name of the task |

### See details of a task

`mtnt get task <task_name>`

| Argument    | Description          |
| ----------- | -------------------- |
| `task_name` | The name of the task |

### See details of an action

Prints the action information. If a name or timestamp is provided and there are 2 or more actions that fit the criteria, prints actions and returns error code -10.

`mtnt get action <task_name> [<action_timestamp>|<action_name>]`

| Argument           | Description                                                                                   |
| ------------------ | --------------------------------------------------------------------------------------------- |
| `task_name`        | The name of the task                                                                          |
| `action_timestamp` | The timestamp of the action. A partial timestamp cam be provided (ie: YYYY-MM, or YYYY-MM-DD) |
| `action_name`      | Name of the action to search for                                                              |

### Edit a task details

ie: name, start_time, periodicity, description
To edit a task name (rename), use the --interactive feature (it will ask for a new name), or the --rename keyword
If neither --interactive or --rename options are given, expects at least a <start_time>, if <periodicity> or description are not give, the command will not change these values. To set `periodicity` to empty, set it to `0` (zero) and to clear the description, set it to `""` (empty string)
If a name or timestamp is provided and there are 2 or more actions that fit the criteria, asks the user which one to edit.

`mtnt edit task <task_name> [-i| --interactive | <new_start_time> <new_periodicity> <new_description> | --rename <new_name>]`

| Argument              | Description                                                                                                   |
| --------------------- | ------------------------------------------------------------------------------------------------------------- |
| `-i`, `--interactive` | CLI will prompt for the parameters that were not passed. If no other arguments are passed, CLI will assume -i |
| `task_name`           | The name of the task you want to edit                                                                         |
| `new_start_time`      | Date time of the start                                                                                        |
| `new_periodicity`     | How often should the task repeat                                                                              |
| `new_description`     | A free text description for the task                                                                          |
| `--rename <new_name>` | option to rename a task                                                                                       |

### Edit a action details

ie: task, timestamp, name, actor

`mtnt edit action <task_name> [<action_timestamp>|<action_name>] [-i| --interactive | <new_task_name> <new_action_timestamp> <new_actor>]`

| Argument               | Description                                                                                                    |
| ---------------------- | -------------------------------------------------------------------------------------------------------------- |
| `task_name`            | The name of the task of the action you want to edit                                                            |
| `action_timestamp`     | The timestamp of the action you want to edit. A partial timestamp cam be provided (ie: YYYY-MM, or YYYY-MM-DD) |
| `action_name`          | Name of the action to search for                                                                               |
| `-i`, `--interactive`  | CLI will prompt for the parameters that were not passed. If no other arguments are passed, CLI will assume -i  |
| `new_task_name`        | Date time of the start                                                                                         |
| `new_action_timestamp` | How often should the task repeat                                                                               |
| `new_actor`            | A free text description for the task                                                                           |

### Delete task

`mtnt delete task <task_name>`

| Argument    | Description                             |
| ----------- | --------------------------------------- |
| `task_name` | The name of the task you want to delete |

### Delete actions

Deletes one action at a time. If the name or timestamp can be associated to multiple actions, asks the user which one before proceding.

`mtnt delete action <task_name> [<action_timestamp>|<action_name>]`

| Argument           | Description                                                                |
| ------------------ | -------------------------------------------------------------------------- |
| `task_name`        | The name of the task of the action you want to delete                      |
| <action_timestamp> | the timestamp of the action you want to delete. Can be a partial timestamp |
| <action_name>      | the name of the action you want to delete                                  |

### See overdue tasks

Check for overdue tasks. A task is considered overdue if between it's last programmed run and now (or optional `at` parameter) there has been no recorded actions

`mtnt report overdue [--at <timestamp>]`

| Argument           | Description                                                                    |
| ------------------ | ------------------------------------------------------------------------------ |
| `--at <timestamp>` | Instead of using now as the base, checks for overdues at a the given timestamp |

### See the next run for all tasks

`mtnt report next [run] [--for <task>] [--at <when>]`

| Argument           | Description                                                                    |
| ------------------ | ------------------------------------------------------------------------------ |
| `run`              | optional, doesn't do anything                                                  |
| `--at <timestamp>` | Instead of using now as the base, checks for overdues at a the given timestamp |

### See all tasks based on criteria

prints the list of tasks that have programmed runs with the criteria given. Also shows how many runs they have had in the time period and if they are overdue or not at the end of the period

`mtnt report tasks [--at <partial_timestamp>] [--between <timestamp1> <timestamp2>]`

| Argument                              | Description                                                                                      |
| ------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `run`                                 | optional, doesn't do anything                                                                    |
| `--at <partial_timestamp>`            | a timestamp without minutes, hours, days or months (ie: 2024-05 for the whole month of May 2024) |
| `--between <timestamp1> <timestamp2>` | list actions between 2 timestamps                                                                |

### See all actions based on criteria

prints the list of runs that are valid for all criteria passed. If no criteria, prints the list of all runs.

`mtnt report actions [--at <partial_timestamp>] [--between <timestamp1> <timestamp2>] [--for <task_name>]`

| Argument                              | Description                                                                                      |
| ------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `run`                                 | optional, doesn't do anything                                                                    |
| `--at <partial_timestamp>`            | a timestamp without minutes, hours, days or months (ie: 2024-05 for the whole month of May 2024) |
| `--between <timestamp1> <timestamp2>` | list actions between 2 timestamps                                                                |
| `--for <task_name>`                   | name of task to filter the output                                                                |

## Error (Return) Codes

- -1: multiple actions selected where expecting only one

## Future Improvements

### Tags for tasks

- allow Tasks to have tags to them
- list tags
- filter tasks based on tasks

### tab completion for bash

### CLI

- edit list oƒ actions by opening an editor
- natural language time instead of timestamps (ie: 5 min ago, or yesterday at 5)

### Web app

The idea is to create a web page where the can interact using an old tablet and mark items done, see overdue items, etc .

The main use case would be to have this running in an old tablet in the kitchen to remind people of my house of their chores and long-term tasks.

### Export task

- as iCalendar tasks or events

### Technical

- explore rrule from dateutil for recurrence
