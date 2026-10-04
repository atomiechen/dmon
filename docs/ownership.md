# Task and stack lifecycle

[Documentation index](README.md) · [Configuration](configuration.md)

A task name selects its current recorded instance. A stack owns the exact
instances launched by that stack run, including replacements made by its live
supervisor. This distinction matters when recovering one service while healthy
services keep running.

## Standalone tasks

`dmon start` and `dmon run` launch managed background tasks. `dmon exec` runs
one configured command directly in the current terminal for debugging; it is
not registered as a managed background task. Use `start` when later terminals
or sessions need to inspect the task through `status` and `list`.

Multi-task `start` is best-effort: dmon attempts every requested task and leaves
successful tasks running if another task cannot start. It returns nonzero and
prints a summary naming the failed tasks. It does not provide stack rollback or
automatically start dependencies. `start` alone does not wait for readiness;
use `dmon wait` afterward when readiness is needed.

## Stack startup and runtime

A foreground stack is a managed multi-task lifecycle and remains discoverable
from another terminal:

```sh
dmon stack up dev
# Omit the name when default_stack (or only one stack) is configured
dmon stack up

# Keep the supervised stack running in the background
dmon stack up -d dev
dmon stack status dev
dmon stack list
dmon stack down dev

# Optional fail-fast policy for foreground or detached stacks
dmon stack up --abort-on-exit dev
```

`dmon stack up` starts dependencies in order and waits for each task's optional
readiness probe. A startup failure or readiness timeout rolls back every task
started by that invocation, in reverse dependency order; it does not adopt or
clean unrelated existing tasks.

After startup, an exited task marks the stack as degraded while unrelated
tasks continue running, matching Docker Compose's default behavior. Use
`--abort-on-exit` when the whole stack should stop after any runtime exit.
Ctrl-C or SIGTERM cleans up a foreground stack in reverse order. `dmon stack
down` requests the same cleanup for an active foreground or detached stack
from another terminal.

To replace an exited member while preserving stack membership, use
[stack repair](#repair-an-exited-stack-member). Starting it separately with
`dmon start worker` creates a standalone replacement; it does not repair the
original stack, and `stack down` will not stop that replacement. See
[standalone recovery](#recover-one-failed-member-without-restarting-healthy-services)
when an independent replacement is intentional.

## Detached stacks and failed startup

Detached mode waits for the same startup and readiness checks before returning.
A lightweight background supervisor keeps monitoring the stack; `dmon stack
down` requests the same graceful reverse-order cleanup on every platform.
Supervisor diagnostics are written to `logs/<stack>.stack.log`. Status includes
every owned task and its process tree; `stack list` summarizes all recorded
foreground and detached stacks.

`dmon stack restart dev` applies to detached stacks: it performs a clean `down`
followed by a detached `up` and preserves the stack's exit policy. It stops
healthy members too. Cross-terminal restart of a foreground stack is rejected
rather than converting it to detached mode.

A detached startup failure preserves the failing task and cause in both startup
output and subsequent JSON status. The stack's `log_path` points to supervisor
diagnostics; `stack logs` only shows task output and may be empty when no task
launched. Correct the cause, then use `stack down` to clear the failed run
before starting again. Environment-file details stay in the diagnostic log
rather than persisted status.

If the supervisor is killed, its persisted ownership metadata lets `down`
recover and clean the tasks it started. Read
[supervisor-crash recovery](#recover-a-stack-after-a-supervisor-crash) and
[ownership limits](#what-is-and-is-not-guaranteed) before acting on orphaned runs.

## Logs and foreground output

```sh
dmon stack logs --tail 100 dev
dmon stack logs -f dev
```

Foreground `stack up` displays new task output with task-name prefixes, while
retaining it in each task's configured `log_path`. Detached mode does not attach
output. `stack logs` reads the latest 100 lines per task by default; `--tail`
changes that count and `-f` follows new output. Viewing logs never modifies the
underlying files or controls running processes.

The log viewer opens files only while reading and closes them before waiting
for more output. File identity lets it reopen a replacement after rotation.
Stopping `stack logs -f` cannot stop or restart a task or stack. The same
read-only component powers foreground attachment; a display failure does not
change stack lifecycle. See [logging configuration](configuration.md#task-fields-environments-and-logging)
for rotation and retention.

## Metadata and process identity

dmon grew out of the [handy-backend shell scripts](https://github.com/atomiechen/handy-backend).

Each task has `.dmon/<task>.meta.json`, which records its command, PID, process
creation time, and log paths. An active foreground or detached stack also has
`.dmon/<stack>.stack.json`, which records its mode, supervisor, and the exact
task processes it owns. Metadata paths are reserved exclusively and subsequent
updates replace the JSON atomically; a per-run ID isolates stop requests, while
PID plus creation time prevents a recycled PID from being mistaken for the
original process. Environment values are used only to launch and probe the task;
they are never written to metadata. Normal foreground cleanup removes its stack
metadata.

`dmon stack down` normally asks the foreground or detached supervisor to stop
tasks in reverse order.
If the supervisor has crashed, it uses the persisted process identities to
recover the orphaned stack without inferring ownership from current
configuration. Existing or unreadable stack metadata is preserved rather than
overwritten; use `dmon stack down` for stale, readable state. **Do not** edit or
delete `.dmon` files manually.

`dmon status` returns a non-zero status if a recorded task has exited. Starting
that task again removes its stale metadata automatically. `dmon stop` terminates
the complete process tree and also cleans stale metadata left by an exited task.

## Verify the service you started

A successful HTTP/TCP request proves that an endpoint responds. By itself it
does not prove that the newly started task serves that endpoint. This matters
when another application already owns the port while your application is still
initializing.

For a task that should own its readiness endpoint, opt in explicitly:

```yaml
tasks:
  api:
    cmd: [uv, run, uvicorn, app:app, --host, 127.0.0.1, --port, "8000"]
    ready:
      http: http://127.0.0.1:8000/health
      require_owned: true
      timeout: 30
stacks:
  dev: [api]
```

The same option works with `tcp: {host: 127.0.0.1, port: 8000}`. It requires a
literal loopback address, such as `127.0.0.1` or `::1`; hostnames, remote
addresses, and command probes are rejected. It is used by stack startup,
configured `dmon wait`, and `Dmon.wait()`.

Before and after a successful probe, dmon looks for a matching listening socket
in the identified task or its descendants. If it cannot verify that listener by
the deadline, the result is `listener-unverified`. This includes permissions that
prevent socket inspection. The result does not assert that a foreign process
exists, and never authorizes reuse, adoption, or termination of another service.
An HTTP failure on a verified listener remains an ordinary readiness timeout.

Leave this option disabled for a task that intentionally probes an external
dependency. Direct `dmon wait --http ...` and `--tcp ...` remain external probes.
Shared listening sockets, forwarded connections, and hostile processes are not
covered by this identity check; it is not cryptographic response authentication.

## Recover a stack after a supervisor crash

Use finite status and logs first:

```sh
dmon stack status dev --format json
dmon stack logs --tail 100 dev
```

An orphaned supervisor does not mean that the application processes have exited.
Stack snapshots include `live_descendant_pids` for descendants whose recorded
PID and creation time still match. Once stopping the stack is appropriate, run:

```sh
dmon stack down dev
```

Down uses the identities recorded by that stack invocation, including observed
descendants whose parent has since exited. It does not search by command name
or terminate whatever currently occupies a port. To restart, stop successfully
before starting the stack again. Stop running stacks before switching between
versions that write different ownership metadata; do not downgrade while a new
version's stack is active.

## Repair an exited stack member

A live foreground or detached supervisor can repair one exited member without
restarting healthy peers:

```sh
dmon stack repair dev worker --format json
dmon stack status dev --format json
```

The replacement becomes part of the same stack, and subsequent `stack down dev`
stops it along with the other owned instances. Repair cleans the old member's
observed residual processes first and refuses to proceed if cleanup is incomplete.
A different current task record is a conflict, not permission to adopt it. A member
that is still running is left unchanged; the result says readiness was not rechecked.
Repair does not replace a live but unhealthy service or automatically repair dependencies.
Dependencies must still be running before their dependent is repaired.

The supervisor keeps each task's initial launch definition and resolved environment
in memory. Repairs reuse those values; later edits to configuration or dotenv files
are not applied. Environment values are never written to repair or ownership records.
This does not snapshot application code or other files the process reads. Review
working-tree changes before deciding that the same launch command is still suitable.
If config syntax is broken, supply `-c /absolute/project/directory` to locate the
saved stack without parsing that file. A full restart applies new configuration
but also stops healthy members.

`--timeout` (default 30 seconds) bounds how long the client waits, not how long
readiness runs. An interrupted or timed-out client does not cancel the repair.
The finite JSON result contains `operation_id`, `task`, `state`, `exit_code`, and
`message`. An `unconfirmed` result is nonzero. Inspect the stack, then recheck
with the returned ID rather than creating a new operation:

```sh
dmon stack repair dev worker --operation-id RETURNED_ID --format json
```

The ID is scoped to this stack run. While that run's record exists, rechecking a
completed ID returns its recorded result without launching another process; this
is a historical operation result, not a fresh health check. Concurrent requests
are serialized by the supervisor; a request for an identity that has since changed
fails rather than replacing it again. Run `status` and check real endpoints afterward.

If startup or readiness fails, only the replacement is rolled back. The stack
remains degraded and its healthy peers continue. A `down` request prevents further
repairs and interrupts readiness; normal stack shutdown then cleans all owned
members. `abort-on-exit` stacks, exited supervisors, and older supervisors without
repair support reject new repairs. Repair is not an orphan-supervisor takeover.

Repair journals live under `.dmon/STACK.stack.json.repair/`, keyed by stack run and
operation IDs. Keep them with the runtime records, never in Git. They record
pending/starting/waiting/done phases, not environment values. Once the new identity
is saved in stack metadata, recovery after a supervisor crash uses that identity.
There remains a spawn-to-record crash window: a journal stuck in `starting` cannot
prove whether a replacement was created. `down` refuses to claim successful cleanup
and preserves evidence in that case. Inspect the task and journal from the original
project; do not erase or relabel records to make the error disappear. This is not
an exactly-once guarantee under arbitrary machine/process crashes.

## Recover one failed member without restarting healthy services

Use this standalone fallback for older supervisors, or when an independent task
is intentional. Prefer stack repair above when membership must continue.

A task name selects its current recorded instance. A stack owns the specific
instances started by that stack invocation. Starting a replacement with
`dmon start worker` does not enroll it into the existing stack.

If the API must keep its process and in-memory state, inspect both views first:

```sh
dmon stack status dev --format json
dmon status api worker --format json
```

After confirming that the worker exited, its old descendants do not need
recovery, and the current worker configuration is suitable, restore that task:

```sh
dmon start worker
dmon wait worker
dmon status api worker --format json
dmon stack status dev --format json
```

`start` alone does not wait for configured readiness. Use a configured readiness
probe with `wait`, then check the application's real behavior. The task view can
show both tasks running while the original stack remains degraded: it still owns
the exited worker instance. Do not edit metadata or restart the entire stack just
to make that status green. Stack repair refuses to adopt a replacement that was
already started independently; it only owns replacements it starts itself.

Record the replacement in the handoff. When stopping these services is intended,
inspect their identities again and stop the replacement explicitly:

```sh
dmon stop worker
dmon stack down dev
```

The first command targets the current task record; verify it is still the
replacement you intend to stop. The second stops the original stack's instances,
including the API. `stack down` alone deliberately leaves the replacement alone.
Check both task and stack records and actual endpoints before claiming cleanup.
A normal full `stack restart` stops healthy members too, so it is unsuitable when
their in-memory state must survive.

## Copied or moved projects

Stop running services before copying runtime records or moving a project. A
record whose saved location differs from the file being read is rejected with
`metadata-location-mismatch`; status, start, wait, and stop must not silently
adopt that record. The record stays available for diagnosis and the original
processes stay untouched. Resolve the original run from its original location;
do not edit the stored paths simply to bypass the check.

New stack records save their metadata location explicitly. Published legacy
stacks derive it from their saved configuration path and the fixed `.dmon`
layout. Task records already contain their metadata path. Symlink aliases that
resolve to the same location are accepted. Records without any location
evidence retain legacy behavior; the check is not protection against edited
records, cross-machine copies at identical paths, or hostile local processes.
Moving a live project is deliberately not an automatic ownership transfer.

## What is and is not guaranteed

The supervisor observes ancestry during readiness and runtime polling, persisting
changes to its stack record. It can clean those identified descendants after a
parent exit or supervisor crash. If it sees unverified residual members of a
former task process group on POSIX, it leaves them untouched, returns failure,
and retains metadata. Starting over must not silently discard that evidence.

Polling is not an OS containment primitive. A child that forks and escapes before
observation may remain unknown; Windows and self-daemonizing programs have no
portable equivalent of this POSIX group diagnostic. Prefer foreground commands
under a supervised stack. Standalone `start`/`run` do not continuously observe
descendants. A machine crash, edited metadata, privileged adversaries, and total
cleanup of arbitrary daemonized descendants are outside this contract.

Readiness and status are point-in-time observations. They cannot guarantee the
service stays alive after the command returns. A PID plus its creation time
protects against ordinary PID reuse, but is not an authorization boundary
between processes running as the same OS user. No environment contents are
added to the ownership records.

## Record compatibility and scope

A saved identity needs both a numeric PID and a finite creation time. Missing or invalid
process identities and unrecognized fields cause a read error; control leaves that record
and its processes untouched. The explicit `-1/-1` reservation is allowed before
a process is launched. Legacy records without newly added optional descendant or
stack-location fields remain readable. This is an additive, unversioned format;
unknown fields are rejected rather than silently ignored. Stop active services
before downgrading to a reader that does not know the newer fields.

Records are local to one machine and runtime directory. dmon does not record a
machine or boot identifier. Do not synchronize `.dmon/`, restore it from a backup
onto another machine, or use a shared runtime directory between machines. The
path check cannot distinguish two machines with identical absolute paths.
Creation time rejects ordinary stale identities after restart, but is not a
cross-machine guarantee. A machine restart is outside recoverable run continuity.

Changing valid configuration does not change the identities owned by an existing
stack: stopping it uses its saved ownership. Status describes the saved run, not
proof that it matches the edited configuration. There is no config-drift
reconciler or automatic restart. If configuration becomes invalid or its stack is
removed, name the saved run and supply the original project directory explicitly:

```sh
dmon stack status dev -c /absolute/project/directory --format json
# When stopping that saved run is intended:
dmon stack down dev -c /absolute/project/directory
```

Named `status`, `down`, and `repair` can locate saved stack metadata this way
without parsing the edited configuration. `up`, `restart`, and `logs` still need
valid configuration. Keep config changes separate from active-run recovery.
