# Test on Windows

Use native Windows Python and PowerShell or cmd. Start from a clean checkout.

```powershell
uv run --no-project --python 3.13 scripts/validate_checkout.py --python 3.13
uv run --no-project --python 3.8 scripts/validate_checkout.py --python 3.8
```

The runner builds the checked-out commit, verifies the wheel against its source,
and runs the suite from an isolated installation. Logs and artifacts are written
to `.local/validation/`. Keep the checkout unchanged during a run; commit any
fixes before running the clean-checkout runner again. Identify builds by commit
and artifact checksum, since development builds may share a version number.

A dependency download failure leaves validation incomplete. After a timeout,
check test-owned process identities before continuing: stopping the test runner
alone may leave child processes. Avoid killing by process name or port.
Use the generated isolated Python environment for the manual checks below.

Also run the relevant scenarios in [the manual lab](../tests/manual/README.md):
terminal close and reattachment, Ctrl+C, cross-terminal stop, paths containing
spaces or non-ASCII characters, log following, and partial repair. Use disposable
loopback services and check their recorded process identities during cleanup.

For the npm wrapper case, verify that stopping the task also stops the Node child.
Use actual Ctrl+C for foreground console behavior. Closing a terminal and opening
a new one must leave a detached stack's identities unchanged. Check log following
across rotation and confirm that stopping the log viewer leaves services running.
After each scenario, stop the recorded test processes and verify cleanup.
