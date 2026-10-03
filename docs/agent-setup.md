# Use dmon with a coding agent

The CLI runs services. The [skill](../skills/dmon/SKILL.md) teaches an agent
when to use it and how to inspect, repair, and stop existing services.

## Install the CLI

From the dmon source checkout:

```sh
uv tool install .
dmon stack repair --help
```

Use this checkout for the commands in this example. Python 3.8+ and uv are required.
For an existing project installation, keep its chosen version and environment.

## Give the workflow to your agent

You can ask your agent to install the skill for you:

> Install the dmon skill from https://github.com/atomiechen/dmon, directory
> `skills/dmon`, into this project's skill directory. Use the same source revision
> as the CLI, and preserve any existing customized copy.

In Codex, you can give that request to `$skill-installer`. Specify project scope
explicitly: its default destination is personal (`$CODEX_HOME/skills`), and the
installer supports a custom `--dest` for `.agents/skills`. Installation makes the
workflow available; then ask the agent to use it for your project. If you already
have a checkout, no download is needed. Send this request, replacing the two paths:

> Read DMON_CHECKOUT/skills/dmon/SKILL.md and set up suitable local services in
> TARGET_PROJECT with dmon. Preserve existing running services and container
> management. Verify the application and leave its start, inspect, and stop commands.

An agent with local command access can read that file directly. To make the
skill discoverable in a project, copy the **whole** `skills/dmon` folder from
the same source version as your CLI into one of these locations:

| Agent | Destination inside the target project | Explicit invocation |
| --- | --- | --- |
| Codex | `.agents/skills/dmon/` | `$dmon` |
| Claude Code | `.claude/skills/dmon/` | `/dmon` |

For personal use across projects, the documented locations are
`~/.agents/skills/dmon/` for Codex and `~/.claude/skills/dmon/` for Claude Code.
Choose project or personal scope; avoid installing duplicate copies at both.
If the destination already exists, inspect it before replacing it. To update,
replace the installed folder with the one from the CLI's source version; to
uninstall, remove that skill folder. CLI installation is independent.

Use an explicit revision when installing from Git. Restart Codex if a newly
installed skill does not appear. Other agents can read `SKILL.md` directly.

See the official [Codex skills](https://learn.chatgpt.com/docs/build-skills) and
[Claude Code skills](https://code.claude.com/docs/en/skills) instructions for
native installation behavior. The skill uses the
[Agent Skills format](https://agentskills.io/specification).

## Continue in another session

Ask the next agent to inspect the existing services and verify the application.
Project instructions should identify the CLI installation, config path, service
endpoints, and inspect/log/stop commands. Healthy services can be reused.
Request cleanup when you want those services stopped.

## Run the recovery example

From the dmon checkout:

```sh
uv sync --locked --dev
uv run python scripts/demo_repair.py
```

The example creates two temporary local HTTP services, stops the worker, repairs
it, and checks that the API keeps its process identity and in-memory value. It
then stops the stack and prints the directory containing its logs and results.
