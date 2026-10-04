# Agent instructions

Use the smallest canonical source for the task:

- Start with `README.md` for product scope and the normal user workflow.
- Use `docs/` for detailed configuration, lifecycle/recovery, and coding-agent setup.
- Read `CONTRIBUTING.md` before changing implementation or durable behavior.
- Read `tests/manual/README.md` for lifecycle, signal, terminal, logging, or multi-service changes.

Do not duplicate durable guidance across files. Update the existing canonical
source when behavior, validation, or release procedures change.
