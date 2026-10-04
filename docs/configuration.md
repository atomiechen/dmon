# Configuration reference

[Documentation index](README.md) · [Quick start](../README.md#getting-started)

## Files and paths

Define tasks in `dmon.yaml` or `dmon.yml`, or under `[tool.dmon.tasks]` in
`pyproject.toml`. Without `-c` / `--config`, dmon searches the current directory
and then its parents. In each directory it checks `dmon.yaml`, `dmon.yml`, then
`pyproject.toml`, and uses the first file it finds. An explicit directory is
searched only in that directory.

Commands run from the configuration file's directory unless `cwd` is set.
Configured paths, including `cwd`, logs, metadata, and `env_file`, resolve
relative to the configuration file, not the terminal's current directory.
Ad-hoc `dmon run` commands do not require a configuration file.

## Task selection and defaults

Use `--all` to operate on all tasks:

```sh
# All configured tasks
dmon start --all
dmon restart --all

# All recorded task metadata in the project
dmon status --all
dmon stop --all
```

If you have defined `default_task`, or only one task is defined in the config file, you can omit the task name:

```sh
dmon start
dmon stop
dmon restart
dmon status
dmon exec
```

You can use `-c` / `--config` to specify a custom config file or the directory containing it:

```sh
dmon start --config /path/to/dmon.yaml app  # YAML
dmon start --config /path/to/pyproject.toml app  # or TOML
dmon start -c /path/to/dir app  # shorter, dir with `dmon.y(a)ml` or `pyproject.toml`
```

The same config discovery and selection rules apply to stacks. A stack name can
be omitted when `default_stack` is set or only one stack is configured. Options
belonging to a stack operation go after that operation and may appear before or
after the stack name; for example, `dmon stack up -d dev` and `dmon stack up dev
-d` are equivalent.

Tasks can also invoke `dmon` commands, including commands defined in another project:

```yaml
tasks:
  app: ["python", "-u", "server.py"]
  nested: pwd && dmon exec app  # nest `dmon exec`
  subdir_task1:
    cwd: /path/to/dir
    cmd: ["dmon", "exec", "app"]  # run task defined in another folder
  subdir_task2: dmon exec app --config /path/to/dir/dmon.yaml  # like above
```

## Task fields, environments, and logging

A task can be a **string**, **list**, or **dictionary**.

When rotation is enabled, dmon keeps timestamped archives such as
`app.log.20260807-142106`. Both task and runner logs use this cross-platform
format; a same-second collision adds `.1`, `.2`, and so on. Archives are never
deleted by default. Set a backup count explicitly to enable retention cleanup.
`log_path` contains task output; `rotate_log_path` contains diagnostics from the
dmon process that captures and rotates that output. They are independent log
streams and use independent retention settings.
The size limit is checked at line boundaries, so a single long line may exceed
the configured limit.

Here is a more complete example. Comments identify defaults; the paths,
environment files, commands, and dependency are placeholders for your project:

```yaml
tasks:
  another_task: ["python", "dependency.py"]
  your_task_name:
    # Command to run; can be a string (run in shell) or list of strings (exec form)
    cmd: ["python", "server.py"]  # required
    cwd: "/path/to/working/dir"  # default: configuration file directory
    env_file: [".env", ".env.local"]  # optional; later files override earlier files
    env:  # (default: inherit from parent process)
      PYTHONUNBUFFERED: "1"
    override_env: false  # true omits parent env; use env_file and env only
    log_path: "logs/<task>.log" # path to log file
    log_rotate: false  # enable log rotation
    log_max_size: 5  # max log file size before rotation in MB
    # log_backup_count: 10  # optional; omit to retain all task log archives
    rotate_log_path: "logs/<task>.rotate.log"  # path to rotation log
    rotate_log_max_size: 5  # max rotation log file size in MB
    # rotate_log_backup_count: 10  # optional; omit to retain all runner log archives
    meta_path: ".dmon/<task>.meta.json"  # path to meta file
    depends_on: [another_task]  # dependency order used by `dmon stack up`
    ready:  # optional; exactly one of http, tcp, or command
      command: [python, healthcheck.py]
      timeout: 30  # total seconds to wait (default: 30)
      interval: 0.2  # seconds between attempts (default: 0.2)
default_task: your_task_name  # the default task name
stacks:
  dev: [your_task_name]
default_stack: dev
```

`env_file` accepts one path or an ordered list of dotenv files. Paths are
relative to the dmon configuration file. Later files override earlier files,
the existing process environment overrides file values, and the explicit `env`
table has highest priority. Set `override_env: true` to omit the existing
process environment. Standard dotenv `${NAME}` expansion can refer to earlier
values in the same file or any earlier file in the list. Missing files and keys
without assigned values fail startup without creating task metadata.
Environment values and environment-file paths are never written to metadata or
JSON inspection output.

In TOML, write like this:

```toml
[tool.dmon]
default_task = "app"
default_stack = "dev"

[tool.dmon.tasks]
app = { cmd = ["python", "-u", "server.py"], log_rotate = true }
worker = { cmd = ["python", "worker.py"], depends_on = ["app"] }

[tool.dmon.stacks]
dev = ["app", "worker"]
```

All paths, including `env_file`, can be absolute or relative to the **config
file location**.

YAML anchors and merge keys can reuse task fragments within one configuration
file. Task dependencies are resolved transitively and cycles are rejected.
dmon intentionally does not recursively include or merge other configuration
files; keeping one path owner makes command, environment, log, and metadata
paths unambiguous.

## Dependencies and stacks

`depends_on` determines startup order for `dmon stack up`; standalone `start`
does not automatically start dependencies. A stack is a non-empty list of task
names. Dependencies are included transitively even when they are not listed in
the stack itself. Missing dependencies and cycles are rejected before startup.

For example, `dev` below also starts `database` before `api` and `worker`:

```yaml
tasks:
  database:
    cmd: [python, database.py]
    ready:
      tcp: {host: 127.0.0.1, port: 5432}
      timeout: 20
  api:
    cmd: [python, api.py]
    depends_on: [database]
    ready:
      http: http://127.0.0.1:8000/health
  worker:
    cmd: [python, worker.py]
    depends_on: [api]
stacks:
  dev: [api, worker]
default_stack: dev
```

See [stack startup and runtime behavior](ownership.md#stack-startup-and-runtime)
for rollback, degradation, and shutdown semantics.

## Readiness

A task's optional `ready` table has exactly one probe:

- `http`: an HTTP or HTTPS URL that must return a successful response,
  following redirects.
- `tcp`: a `host` and a `port` from 1 to 65535 that must accept a connection.
- `command`: a shell string or exec-form list that must exit successfully.

`timeout` defaults to 30 seconds and `interval` to 0.2 seconds. Both must be
finite positive numbers. A task exiting before readiness is a startup failure.
During stack startup, a task without a probe only needs to remain running
through a brief stabilization period. A configured `dmon wait` requires a
readiness probe; it returns an invalid result when none is configured.

An ordinary HTTP/TCP probe can target an external dependency. Set
`require_owned: true` only when the task or its descendants must own the
listener. This requires HTTP/TCP with a literal loopback IP address and socket
inspection access; it does not support command probes. See
[verify the service you started](ownership.md#verify-the-service-you-started)
for examples, failure results, and limits.

`dmon wait` observes readiness without starting or stopping anything. A
configured wait uses the task's probe, working directory, environment, and
recorded process identity. Omit the name when `default_task` is set or only one
task is configured. Positive `--timeout` and `--interval` values override the
configured values:

```sh
dmon wait api
dmon wait database api --timeout 60 --interval 0.5
```

Direct probes need neither a configuration nor managed task metadata:

```sh
dmon wait --http http://127.0.0.1:8000/health
dmon wait --tcp 127.0.0.1:5432
dmon wait --timeout 30 --command -- python healthcheck.py --verbose
```

For command probes, dmon options must precede `--command`; the optional second
`--` marks the child-command boundary. The command returns zero only when every
target is ready, one for a completed unsuccessful wait, and 130 when interrupted.
Use `--format json` for finite machine-readable results.
