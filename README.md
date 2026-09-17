# herdr-last-workspace

[![Herdr Plugin](https://img.shields.io/badge/herdr-plugin-blue.svg)](https://herdr.dev)
[![License: GPL v2](https://img.shields.io/badge/License-GPL_v2-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)

tmux-style MRU **last workspace toggle** for [Herdr](https://herdr.dev) with automatic per-workspace active tab restoration.

Jump back and forth between your most recent workspaces with a single key combination (e.g. `prefix + shift + l`), landing on the exact tab/window you were working in.

---

## Highlights

- 🔄 **tmux-Style MRU Stack:** Toggles seamlessly between your current and previous workspace (A ↔ B) without clearing history on consecutive toggles.
- 📑 **Per-Workspace Tab Restoration:** Remembers which tab was active in each workspace. Switching back restores that tab instead of resetting to the workspace default.
- ⚡ **Zero Build / Zero Dependencies:** Pure Python 3 standard library (`fcntl`, `json`, `subprocess`, `os`, `pathlib`). No Rust/Cargo compiler, Go toolchain, or `pip` dependencies required.
- 🛡️ **Race-Condition Safe & Atomic:** Uses POSIX file locking (`fcntl.flock`) and atomic file replacement (`os.replace`) to ensure asynchronous Herdr events never corrupt state.
- 🩹 **Self-Healing State:** Reconciles against live Herdr state (`herdr workspace list`) on every toggle. Seamlessly prunes closed workspaces and auto-recovers even if an event hook is dropped.
- 🪶 **No Background Daemon:** Spawns on-demand via Herdr's native event hooks in ~70ms without persistent background processes or socket leaks.

---

## Requirements

- [Herdr](https://herdr.dev) `>= 0.7.0`
- `python3` (included by default on macOS, Ubuntu, Fedora, Debian, and Arch)
- macOS or Linux

---

## Installation

Install directly via Herdr's plugin manager:

```bash
herdr plugin install akpw/herdr-last-workspace --yes
```

### Local Development / Linking

To link a local clone for development:

```bash
git clone https://github.com/akpw/herdr-last-workspace.git
herdr plugin link ./herdr-last-workspace
```

Verify installation:

```bash
herdr plugin list
```

You should see:
```text
- akpw.last-workspace (Last Workspace) enabled [...]
```

---

## Keybinding Setup

Add the toggle command to your Herdr configuration (`~/.config/herdr/config.toml`):

```toml
[[keys.command]]
key = "prefix+shift+l"
type = "plugin_action"
command = "akpw.last-workspace.toggle"
description = "Last workspace"
```

*Feel free to adjust the `key` shortcut to your preference (e.g. `prefix+l`, `ctrl+\`, etc.).*

---

## How It Works

1. **Event Hooks:** Subscribes to Herdr's native lifecycle events:
   - `workspace.focused`: Pushes the focused workspace to the top of the Most Recently Used (MRU) stack.
   - `workspace.closed`: Prunes the closed workspace from history.
   - `tab.focused`: Caches the active tab ID for the current workspace.
   - `tab.closed`: Invalidates cached tabs when closed.
   - `startup`: Reconciles live workspaces and warms the stack on Herdr launch or live server handoff.
2. **Toggle Action (`akpw.last-workspace.toggle`):**
   - Fetches live workspaces to ensure all targets are valid.
   - Swaps the top two elements of the MRU stack (`stack[0]` ↔ `stack[1]`).
   - Focuses the previous workspace, followed by its remembered tab.
3. **Storage:** Keeps runtime state in `~/.local/state/herdr/plugins/akpw.last-workspace/state.json` (as directed by `HERDR_PLUGIN_STATE_DIR`).

---

## Why Not Existing Alternatives?

| Feature | `akpw/herdr-last-workspace` | `third774/herdr-last-workspace` | `pedrobarco/herdr-lastfocus` |
| :--- | :---: | :---: | :---: |
| **Language** | **Python 3 stdlib** | Rust (requires `cargo`) | Go (requires `go`) |
| **Tab Restoration** | ✅ Yes | ❌ No | ❌ No |
| **Consecutive A ↔ B Toggle** | ✅ Yes | ❌ Clears target on repeat | ✅ Yes |
| **Execution Model** | Native Hooks (~70ms) | Native Hooks | Background Daemon |
| **No Compilation Required** | ✅ Yes (zero build) | ❌ No (requires cargo / ~500MB toolchain) | ❌ No (requires go compiler) |

---

## License

[GPL-2.0-or-later](LICENSE) © 2026 Arseniy Kuznetsov
