---
name: dmon
description: "Set up, inspect, recover, or stop local development services with dmon when they need to survive terminals or coding-agent sessions. Useful for host services managed by handwritten background scripts or PID files. Do not replace a working container or production service manager merely to use dmon."
metadata:
  author: Atomie CHEN
  source: https://github.com/atomiechen/dmon
---

# dmon

Help the user leave local services understandable and manageable in the next
session. Installing this skill does not install the CLI. It requires an agent
that can execute commands on the machine running those services.

## Choose an appropriate scope

Read the project's instructions and existing start/stop commands. Identify which
services run on the host, their working directories, dependencies, ports, and
readiness checks. Inspect existing runtime records and listeners before starting
anything. Record what was already running separately from what this operation
creates.

Keep working Docker Compose, systemd, and other established lifecycle managers.
A container database can remain under Compose while dmon manages a host API and
frontend. A single foreground command may need no new tool. If dmon adds no clear
benefit, explain that and use the existing workflow. Assessment alone does not
authorize migration; an explicit setup request does.

## Select the CLI

Use the project's chosen installation and version. Listener ownership checks and
stack repair require 0.5.0. For a source checkout, install with
`uv tool install /path/to/dmon-checkout` and check `dmon stack repair --help`.
For a supplied wheel, use `uv tool run --from /path/to/package.whl dmon`
consistently. Preserve the supplied version or source revision; check the CLI
before relying on version-specific commands.
Python is dmon's runtime; managed programs can use any language.
Confirm the project's required executables exist before starting services.

## Configure and verify

Prefer a small `dmon.yaml` using the project's actual foreground commands. Do not
put `nohup`, trailing `&`, or a self-daemonizing wrapper inside a managed command.
Paths resolve relative to the config. Keep runtime `.dmon/` records and service
logs out of version control. Keep secrets in the project's existing env mechanism.
Use `env` for task-specific additions; it already takes precedence over inherited
values. `override_env: true` replaces the whole inherited environment, including
PATH, and is usually inappropriate for ordinary setup.

Example shape; replace the command, endpoint, and timeout with verified values:

```yaml
tasks:
  api:
    cmd: [node, server.js]
    ready:
      http: http://127.0.0.1:8000/health
      require_owned: true
      timeout: 30
stacks:
  dev: [api]
```

Use `depends_on: [api]` on tasks that actually require API readiness. Enable
`require_owned` when a task should serve its own literal-loopback
HTTP/TCP endpoint. It verifies a listening socket belongs to the identified task
or its descendants. It is not response authentication or proof of exclusive
socket ownership. Leave it off for external dependency checks; command probes
cannot use it. Never remove this check just to make an unexplained failure pass.

For a new stack in an authorized setup:

```sh
dmon stack up -d dev
dmon stack status dev --format json
dmon wait api --format json
dmon stack logs --tail 100 dev
```

Use `--config /absolute/path/to/dmon.yaml` after the operation if discovery is
ambiguous. Verify an application-specific response as well as process status.
Use finite logs and bounded readiness checks. JSON goes to stdout; diagnostics
go to stderr. Nonzero status can describe an exited or degraded service and must
not be discarded as malformed output.
If startup fails before any task starts, `stack logs` may be empty. Read the
stack status `error` first; its `log_path` points to supervisor diagnostics when
more detail is needed. Correct the cause, then use `stack down` for this failed
run before retrying. Preserve any services that predated the operation.

An existing stack needs inspection, not unconditional `up` or `restart`.
Duplicate `up` is rejected; that alone does not mean the existing stack is broken.
Startup rollback applies only to tasks created by that invocation. Do not stop
pre-existing services merely to complete a demonstration.

## Resume, diagnose, and clean up

In a later session, read the saved project instructions, inspect finite status
and logs, then check the real endpoint. Reuse only when the identified running
instance and configuration meet the user's task. A responding port alone is
insufficient evidence to adopt or kill a process.

`listener-unverified` means ownership could not be verified, including insufficient
inspection permissions; it does not prove a foreign service exists. Diagnose the
configured address, command, logs, and listener. Offer a different port when
appropriate; do not terminate whatever occupies the old one.

For a failed member with healthy peers that must keep running, use
`dmon stack repair STACK TASK --format json`. Verify the
installed CLI supports it. Repair needs the original live supervisor; it reuses
that supervisor's initial launch definition/environment and does not apply later
config or dotenv edits. Check whether working-tree changes make reuse appropriate.
An independently started replacement is a conflict and is not adopted. A still-live
member is left unchanged, without a new readiness assertion.

After repair, verify real endpoints and stack status. Later `stack down` includes
that replacement. If the result is `unconfirmed`, inspect and recheck using its
`--operation-id`; timeout or client interruption does not cancel the operation.
Do not erase a stuck `starting` journal or reinterpret it as a failed spawn.
For older supervisors, standalone `start TASK` plus configured `wait TASK` may
restore the service, but the old stack stays degraded and does not own that new
instance. Record the extra `stop TASK` requirement in the handoff; inspect the
current identity before stopping. Never restart healthy peers merely to get green
stack status.

An orphaned supervisor can leave live tasks. Once stopping those owned services
is authorized, use `dmon stack down dev`. For an individual task, use
`dmon stop TASK`. Inspect the result and remaining identities before claiming
cleanup succeeded. Do not use broad `pkill`, kill-by-port, or erase records to
conceal incomplete cleanup. Polling can only recover observed descendants;
standalone `start` does not continuously observe ancestry.

For `metadata-location-mismatch`, preserve the record and resolve the run from
its original location. Do not edit saved paths to bypass the check. Stop services
before moving a project or downgrading the CLI. Copied records do not authorize
control of the original project's processes.

Leave a short project handoff when setup was requested: exact CLI source/prefix,
config location, service endpoints, inspect/log/stop commands, and services kept
running. Do not record secrets or commit runtime metadata. Verify a subsequent
CLI invocation can inspect the same process identities.
