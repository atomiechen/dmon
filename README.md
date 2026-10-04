# dmon

![dmon — The local process manager for developers and coding agents.](https://raw.githubusercontent.com/atomiechen/dmon/main/assets/banner.svg)


[![GitHub](https://img.shields.io/badge/github-dmon-blue?logo=github)](https://github.com/atomiechen/dmon)
[![PyPI](https://img.shields.io/pypi/v/python--dmon?logo=pypi&logoColor=white)](https://pypi.org/project/python-dmon/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/atomiechen/dmon)


A lightweight, cross-platform process manager for local services and development workflows.
Run any command as a background *task*, or supervise a stack with readiness checks
and repair failed members while healthy services keep running. Logging and log
rotation are built in.

For developers and coding agents, dmon records process identities and exposes
JSON status so later sessions can inspect and reuse existing services.
See [coding-agent setup](https://github.com/atomiechen/dmon/blob/main/docs/agent-setup.md).

Shipped as the CLI tool `dmon`.


## Features

- 🖥️ **Cross-platform:** Works on Linux, macOS, and Windows.
- ⚡ **Lightweight:** No daemon service or container runtime required.
- 🧩 **Flexible tasks:** Tasks can be configured in `pyproject.toml` or `dmon.yaml`; or run ad-hoc commands directly.
- 🔗 **Supervised stacks:** Start dependent tasks in order, wait for HTTP, TCP,
  or command readiness, and report runtime degradation.
- 🌙 **Foreground or detached:** Keep a stack attached for development, or run
  it under a recoverable background supervisor with `dmon stack up -d` and
  `dmon stack down`.
- ⏱️ **Reusable readiness:** Wait for configured tasks or direct HTTP, TCP, and
  command probes from scripts and deployment workflows.
- 🪵 **Logging & log rotation:** Keep active log files manageable, with optional archive retention limits.


## Demos

The demos below cover everyday task management and supervised stacks. Both use this `dmon.yaml` and a small [heartbeat program](https://github.com/atomiechen/dmon/blob/main/scripts/recording/service.py):

```yaml
tasks:
  api: [python, -u, service.py, api]
  worker: [python, -u, service.py, worker]
stacks:
  dev: [api, worker]
```

**Everyday tasks.** Run a command directly with `run` (no configuration needed),
then use `start`, `status`, and `stop` for a configured task. `exec` runs a
configured task in the foreground; Ctrl-C ends it. In this clip, `stop --all`
stops the sole ad-hoc task before the configured API is started.

![Run an ad-hoc command, manage a configured task, and execute a task in the foreground](https://github.com/user-attachments/assets/2b60acab-d56d-43c0-a44b-f602243c7105)


**Keep healthy services running.** Start a stack, deliberately stop its worker,
and repair that member. The API keeps the same PID and its counter continues;
`stack down` stops both members. The lower panes show real files and live logs.

![Start a stack, repair only its stopped worker, and clean up both members](https://github.com/user-attachments/assets/58d1a9f9-91d8-4096-9dca-ac53815194c8)



## Installation

`dmon` requires Python 3.8+ and is available as [`python-dmon`](https://pypi.org/project/python-dmon/) on PyPI.
Managed commands can use any language.

```sh
pip install python-dmon
```

We recommend installing into an isolated environment, e.g., with `uv` / `pipx`:

```sh
# Install globally with uv tool
uv tool install python-dmon

# Or with pipx
pipx install python-dmon

# Add as a dev dependency in your project
uv add --dev python-dmon
```

You can also run dmon without installing it permanently:

```sh
# With uvx (uv tool run)
uvx python-dmon

# Or with pipx
pipx run python-dmon
```

To get the latest features, install from source:

```sh
pip install git+https://github.com/atomiechen/dmon.git
```

For coding agents, see the [setup instructions](https://github.com/atomiechen/dmon/blob/main/docs/agent-setup.md) and the
[portable skill](https://github.com/atomiechen/dmon/blob/main/skills/dmon/SKILL.md). The skill is installed separately from the CLI.

## Getting Started

### Prepare Configuration

Create a `dmon.yaml` file:

```yaml
tasks:
  app: ["python", "-u", "server.py"]  # exec form
  # app: "python -u server.py"        # or a shell string
```

Without `--config`, dmon searches the current directory and its parents for
`dmon.yaml`, `dmon.yml`, or `pyproject.toml`. See the
[configuration reference](https://github.com/atomiechen/dmon/blob/main/docs/configuration.md)
for TOML, environments, paths, defaults, and log rotation.

### Run tasks

```sh
dmon start app      # Start in the background
dmon stop app      # Stop the recorded process tree
dmon restart app
dmon status app
dmon exec app      # Run in this terminal; Ctrl-C ends it
```

`exec` runs one configured command directly, without registering a managed
background task. Use `start` to keep it discoverable through `status` and `list`.
You can pass multiple names to the other task commands. Multi-task `start` is
best-effort: successful tasks stay running if another fails. For related
services with ordered startup and rollback, use a stack.

### Run a stack

```yaml
tasks:
  api:
    cmd: [python, api.py]
    ready:
      http: http://127.0.0.1:8000/health
  worker:
    cmd: [python, worker.py]
    depends_on: [api]
stacks:
  dev: [api, worker]
```

```sh
dmon stack up dev          # Foreground; Ctrl-C stops the stack
# Or keep it running under a background supervisor:
dmon stack up -d dev
dmon stack status dev
dmon stack logs --tail 100 dev
dmon stack repair dev worker --format json  # Replace an exited member
dmon stack down dev
```

Stack startup waits for readiness and rolls back tasks it started if startup
fails. After startup, an exited member degrades the stack while healthy peers
keep running. `repair` replaces that member through its live supervisor, so
later `down` includes the replacement. It reuses the supervisor's launch
configuration and environment; separately running `dmon start worker` does not
repair stack membership.

See [task and stack lifecycle](https://github.com/atomiechen/dmon/blob/main/docs/ownership.md)
for fail-fast behavior, detached restart, recovery, and ownership limits. Docker
Compose is still appropriate when container behavior itself must be tested.

### Wait for readiness

`dmon wait` checks readiness without starting or stopping anything. Configured
tasks need a `ready` probe and must already be managed by `start` or a stack:

```sh
dmon wait api
dmon wait api --timeout 60 --interval 0.5

# Direct probes need no configuration
dmon wait --http http://127.0.0.1:8000/health
dmon wait --tcp 127.0.0.1:5432
dmon wait --timeout 30 --command -- python healthcheck.py --verbose
```

Put dmon options before `--command`; the optional second `--` marks the child
command. See [readiness configuration](https://github.com/atomiechen/dmon/blob/main/docs/configuration.md#readiness)
for probe options, listener ownership checks, and wait results.

### Run an ad-hoc command

```sh
dmon run --name myserver python -u server.py
dmon run --name timer -- python -c 'import time; time.sleep(30)'
dmon run --shell echo "Hello World"
dmon run --cwd /path/to/script bash myscript.sh
```

No configuration is needed. Without `--name`, dmon uses the fixed name
`default_run` to prevent duplicate runs.

### List recorded tasks and their status

```sh
dmon list
dmon status app --format json
dmon list --format json
dmon stack status dev --format json
dmon stack list --format json
dmon wait api --format json
```

JSON is written only to stdout; actionable diagnostics remain on stderr. The
payload has a top-level `ok` field and a `tasks`, `stacks`, or `waits` array.
Inspection results contain `name`, `ok`, `error`, and an optional `snapshot`;
wait results contain the target, outcome, reason, elapsed time, and attempt
count. Existing exit-code semantics are unchanged. Interactive and streaming
commands do not offer JSON output.

### Python API

The same task lifecycle and inspection logic is available without parsing CLI
output:

```python
from dmon import Dmon

client = Dmon(config="dmon.yaml")
started = client.start("app")
task = client.status("app")
stacks = client.list_stacks()
client.stop("app")
```

`client.wait("app", timeout=30)` also checks readiness when `app` has a
configured `ready` probe. API calls are synchronous and silent.
`start`, `stop`, and `restart` return an immutable `BatchResult`; `status`
and `stack_status` return `TaskResult` and `StackResult`. List and wait methods
return tuples of their corresponding result types. Expected runtime states such
as missing or exited metadata are results, while invalid configuration raises
`DmonConfigError`. The initial API intentionally does not start a supervised
stack or create implicit background threads.

## Documentation

Start with the [documentation index](https://github.com/atomiechen/dmon/blob/main/docs/README.md):

- [Configuration](https://github.com/atomiechen/dmon/blob/main/docs/configuration.md): task selection, YAML/TOML, environments, readiness, and logs.
- [Task and stack lifecycle](https://github.com/atomiechen/dmon/blob/main/docs/ownership.md): startup, repair, recovery, and process ownership.
- [Coding-agent setup](https://github.com/atomiechen/dmon/blob/main/docs/agent-setup.md): install the workflow and continue across sessions.

## Development

See [CONTRIBUTING.md](https://github.com/atomiechen/dmon/blob/main/CONTRIBUTING.md) for architecture, behavioral contracts,
validation, and the release workflow. Process, signal, log-rotation, and stack
changes must also pass the reproducible [manual test lab](https://github.com/atomiechen/dmon/blob/main/tests/manual/README.md).


## License

[dmon](https://github.com/atomiechen/dmon) © 2025 by [Atomie CHEN](https://github.com/atomiechen) is licensed under the [MIT License](https://github.com/atomiechen/dmon/blob/main/LICENSE).
