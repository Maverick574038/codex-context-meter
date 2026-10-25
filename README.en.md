# codex-context-meter

[中文 README → README.md](README.md)

A Codex context-usage plugin that reflects **the current conversation's context-window occupancy** and **token consumption**. Available on macOS and Windows:

| Platform | Form | 中文 | English |
|---|---|---|---|
| macOS | Terminal CLI | `bin/macos-codex-context-meter` | `bin/macos-codex-context-meter-en` |
| macOS | Web dashboard | `bin/macos-codex-context-meter-gui` | `bin/macos-codex-context-meter-gui-en` |
| macOS | Floating widget | `bin/macos-codex-context-meter-float` | `bin/macos-codex-context-meter-float-en` |
| Windows | Terminal CLI | `bin/windows-codex-context-meter.bat` | `bin/windows-codex-context-meter-en.bat` |
| Windows | Web dashboard | `bin/windows-codex-context-meter-gui.bat` | `bin/windows-codex-context-meter-gui-en.bat` |
| Windows | Floating widget | `bin/windows-codex-context-meter-float.vbs` (double-click, no console) | `bin/windows-codex-context-meter-float-en.bat` |

Windows requires Python 3 (the official installer includes tkinter by default).

### 4. Floating desktop widget (no browser)

```bash
bin/macos-codex-context-meter-float-en      # English
bin/macos-codex-context-meter-float         # 中文
```

A borderless, always-on-top, semi-transparent widget: colored ring + percentage + usage/remaining, project→session dropdowns, ⟳ refresh, auto-updates every 3s, drag anywhere to move it. Zero dependencies (Tkinter ships with macOS).

### 3. Always-on dashboard (GUI, recommended for the desktop app)

```bash
bin/macos-codex-context-meter-gui-en        # English, opens your browser
bin/macos-codex-context-meter-gui           # 中文
```

Serves a local page at `http://localhost:8787`: colored ring (green/yellow/red) + percentage + progress bar + per-category stats + per-turn trend chart, **auto-refreshing every 3 seconds**. Keep the browser tab around; `--port` changes the port, Ctrl+C quits. Zero third-party dependencies (Python's built-in HTTP server).

## Features

### 1. Status line (terminal Codex CLI)

Shows below the chat input box: `🟢 37% · 73.5k/200k`

- 🟢 <60% / 🟡 60–85% / 🔴 >85%
- Wired in via `tui.status_line`; works with the **terminal Codex CLI** only (the desktop app does not render this area)

### 2. Detailed report (desktop app & CLI)

```bash
bin/macos-codex-context-meter-en report     # English
bin/macos-codex-context-meter report        # 中文
```

Prints: current context usage (used / total / percent / remaining), cumulative input / cached-input / output / reasoning tokens, and a per-turn trend. Desktop-app users: this is the mode for you.

## Install

```bash
git clone https://github.com/Maverick574038/codex-context-meter.git
cd codex-context-meter
./macos-install.sh            # configures the CLI status line (optional)
```

No install needed for desktop use — just run `report`. Handy alias:

```bash
echo 'alias cx="~/Codex上下文插件/bin/macos-codex-context-meter-en report"' >> ~/.zshrc
```

`install.sh` idempotently writes `tui.status_line` into `~/.codex/config.toml`; an existing entry is backed up, never silently overwritten.

## Data sources

First hit wins:
1. Session JSON piped to stdin by the `tui.status_line` hook (CLI, real-time)
2. `token_count` / `turn_context` events in the latest rollout file `~/.codex/sessions/**/*.jsonl` (written by both desktop app and CLI)

"Context usage" uses the last turn's real request size, never the cumulative total. Desktop data may lag a few minutes due to batched writes — that's normal.

## Env vars / flags

- `CODEX_HOME`: override Codex config dir (default `~/.codex`)
- `CCM_LANG=en`: force English output
- `--sessions-dir <dir>`: point `report` at a custom sessions dir (testing)

## Self-test

```bash
bin/macos-codex-context-meter-en report --sessions-dir tests/fixtures
echo '{"context_window":200000,"tokens_in_context":90000}' | bin/macos-codex-context-meter-en
```

## License

MIT
