# Recording the demos

On a Mac with Homebrew and [uv](https://docs.astral.sh/uv/getting-started/installation/)
installed, run from the repository root:

```sh
brew install vhs tmux ffmpeg ttyd
uv sync --dev
uv run python scripts/record_demo.py
```

Record just one with `uv run python scripts/record_demo.py --demo everyday`
or `--demo stack`. Each recording prints its temporary output directory,
containing `demo.gif`, `demo.mp4`, the CLI transcript, and cleanup results.
Copy the selected media to `.local/demo-media/` for review; GIF/MP4 are local
generated files and must not be committed to Git or placed in Python `dist/`.

- `everyday.tape` / `stack.tape`: commands, typing, and pauses.
- `appearance.tape`: shared dimensions, font, padding, and ANSI palette.
- `config.yaml`: shared tasks and stack; keep the README example aligned.
- `panels.py`: read-only file and log columns.
- `service.py`: heartbeat output; `../record_demo.py`: pane layout and recording checks.

Review both GIFs for readable colors and unclipped content. The recorder checks
CLI errors, ANSI output, stack API identity preservation, worker replacement,
and tracked-process cleanup. Recording tools are maintainer-only dependencies;
recording does not run in CI.
