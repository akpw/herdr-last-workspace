# herdr-last-workspace

[![Herdr Plugin](https://img.shields.io/badge/herdr-plugin-blue.svg)](https://herdr.dev)
[![License: GPL v2](https://img.shields.io/badge/License-GPL_v2-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)

A Herdr plugin providing tmux-style most-recently-used (MRU) workspace toggling with per-workspace active tab restoration.

---

## Features

- **MRU Workspace Navigation:** Toggles between the current and previous workspace (A ↔ B) without losing history on repeated toggles.
- **Per-Workspace Tab Memory:** Tracks which tab was active in each workspace and restores focus to that specific tab upon switching back.
- **Zero Build Dependencies:** Written in Python 3 using only standard library modules (`fcntl`, `json`, `subprocess`, `os`, `pathlib`). No compilers or external packages required.
- **Atomic State Persistence:** Uses POSIX file locks (`fcntl.flock`) and atomic file replacement (`os.replace`) to prevent state corruption across concurrent Herdr event hooks.
- **Live State Reconciliation:** Queries `herdr workspace list` during toggle actions to validate IDs and prune closed workspaces from the stack.
- **No Background Daemon:** Executes on-demand through Herdr's native action and event hooks.

---

## Requirements

- [Herdr](https://herdr.dev) >= 0.7.0
- Python >= 3.8
- Linux or macOS

---

## Installation

Install via Herdr's plugin manager:

```bash
herdr plugin install akpw/herdr-last-workspace --yes
```

### Local Development / Linking

To link a local checkout:

```bash
git clone https://github.com/akpw/herdr-last-workspace.git
herdr plugin link ./herdr-last-workspace
```

Verify installation:

```bash
herdr plugin list
```

---

## Keybinding Setup

Add the action binding to `~/.config/herdr/config.toml`:

```toml
[[keys.command]]
key = "prefix+shift+l"
type = "plugin_action"
command = "akpw.last-workspace.toggle"
description = "Last workspace"
```

---

## How It Works

1. **Event Hooks:** Subscribes to Herdr lifecycle events:
   - `workspace.focused`: Inserts the focused workspace at the top of the MRU stack.
   - `workspace.closed`: Removes the closed workspace from history.
   - `tab.focused`: Records the active tab ID for the current workspace.
   - `tab.closed`: Clears the recorded tab reference when that tab is closed.
   - `startup`: Synchronizes initial workspace and tab state when Herdr starts or reloads.
2. **Toggle Action (`akpw.last-workspace.toggle`):**
   - Queries live workspaces via `herdr workspace list`.
   - Validates that the targets currently exist.
   - Swaps the top two entries in the MRU stack (`stack[0]` ↔ `stack[1]`).
   - Focuses the target workspace, followed by its last active tab.
3. **Storage:** Persists state to `~/.local/state/herdr/plugins/akpw.last-workspace/state.json` (or the path defined by `HERDR_PLUGIN_STATE_DIR`).

---

## Comparison with Existing Plugins

| Feature | `akpw/herdr-last-workspace` | `third774/herdr-last-workspace` | `pedrobarco/herdr-lastfocus` |
| :--- | :---: | :---: | :---: |
| **Language** | Python 3 stdlib | Rust (requires `cargo`) | Go (requires `go`) |
| **Tab Restoration** | Yes | No | No |
| **Consecutive A ↔ B Toggle** | Yes | Clears target on repeat | Yes |
| **Execution Model** | Native Hooks | Native Hooks | Background Daemon |
| **No Compilation Required** | Yes (zero build) | No (requires cargo / ~500MB toolchain) | No (requires go compiler) |

---

## License

[GPL-2.0-or-later](LICENSE) © 2026 Arseniy Kuznetsov
