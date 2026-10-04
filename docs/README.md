# dmon documentation

The [project README](../README.md) is the quick start: installation, everyday
task commands, a minimal stack, readiness, JSON output, and the Python API.
Use these guides for the details behind those commands.

## Use dmon

- [Configuration reference](configuration.md): configuration discovery and
  selection, YAML/TOML, environment precedence, dependencies, readiness, and
  logging/rotation options.
- [Task and stack lifecycle](ownership.md): best-effort tasks, stack startup
  rollback, runtime degradation, detached supervision, repair, crash recovery,
  and the limits of process ownership.
- [Coding-agent setup](agent-setup.md): install the CLI and portable skill,
  preserve existing services, and continue work across agent sessions.

## Develop and validate dmon

- [Contributing](../CONTRIBUTING.md): architecture, behavioral contracts, tests,
  packaging, and the release workflow.
- [Manual lifecycle test lab](../tests/manual/README.md): reproducible terminal,
  process, readiness, logging, and recovery scenarios.
- [Recording guide](../scripts/recording/README.md): regenerate the terminal demos.

See the [changelog](../CHANGELOG.md) for changes between versions.
