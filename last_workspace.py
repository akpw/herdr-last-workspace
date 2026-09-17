#!/usr/bin/env python3
"""
Herdr Last Workspace Plugin (tmux-style MRU Stack)

Maintains a Most Recently Used (MRU) stack of workspaces and tracks the
active tab (window) per workspace so switching back always lands on the
window you were previously using.
"""

import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def get_state_dir() -> Path:
    env_dir = os.environ.get("HERDR_PLUGIN_STATE_DIR")
    if env_dir:
        path = Path(env_dir)
    else:
        plugin_id = os.environ.get("HERDR_PLUGIN_ID", "akpw.last-workspace")
        path = Path.home() / ".local" / "state" / "herdr" / "plugins" / plugin_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def with_lock(state_dir: Path, fn):
    lock_path = state_dir / "state.lock"
    with open(lock_path, "w") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            return fn()
        finally:
            try:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
            except Exception:
                pass


def load_state(state_dir: Path) -> dict:
    state_file = state_dir / "state.json"
    if not state_file.exists():
        return {"stack": [], "tabs": {}}
    try:
        with open(state_file, "r") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"stack": [], "tabs": {}}
            stack = data.get("stack", [])
            tabs = data.get("tabs", {})
            return {
                "stack": stack if isinstance(stack, list) else [],
                "tabs": tabs if isinstance(tabs, dict) else {},
            }
    except Exception:
        return {"stack": [], "tabs": {}}


def save_state(state_dir: Path, state: dict):
    state_file = state_dir / "state.json"
    tmp_file = state_dir / "state.json.tmp"
    state["updated_unix_ms"] = int(time.time() * 1000)
    with open(tmp_file, "w") as f:
        json.dump(state, f, indent=2)
    tmp_file.replace(state_file)


def run_herdr(*args) -> dict | None:
    bin_path = os.environ.get("HERDR_BIN_PATH", "herdr")
    try:
        res = subprocess.run([bin_path, *args], capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip():
            return json.loads(res.stdout)
    except Exception:
        pass
    return None


def get_live_workspaces() -> tuple[str | None, dict[str, dict]]:
    data = run_herdr("workspace", "list")
    workspaces = {}
    focused_id = None
    if data and isinstance(data, dict):
        result = data.get("result", {})
        ws_list = result.get("workspaces", [])
        for ws in ws_list:
            ws_id = ws.get("workspace_id")
            if ws_id:
                workspaces[ws_id] = ws
                if ws.get("focused"):
                    focused_id = ws_id
    if not focused_id:
        ctx_raw = os.environ.get("HERDR_PLUGIN_CONTEXT_JSON")
        if ctx_raw:
            try:
                ctx = json.loads(ctx_raw)
                focused_id = ctx.get("workspace_id") or ctx.get("context", {}).get("workspace_id")
            except Exception:
                pass
        if not focused_id:
            focused_id = os.environ.get("HERDR_WORKSPACE_ID")
    return focused_id, workspaces


def parse_event() -> dict:
    raw = os.environ.get("HERDR_PLUGIN_EVENT_JSON")
    if not raw:
        return {}
    try:
        val = json.loads(raw)
        if isinstance(val, dict):
            if "data" in val and isinstance(val["data"], dict):
                return val["data"]
            return val
    except Exception:
        pass
    return {}


def handle_focused(state_dir: Path):
    event_data = parse_event()
    ws_id = event_data.get("workspace_id") or os.environ.get("HERDR_WORKSPACE_ID")
    if not ws_id:
        return

    def _update():
        state = load_state(state_dir)
        stack = state["stack"]
        if ws_id in stack:
            stack.remove(ws_id)
        stack.insert(0, ws_id)
        save_state(state_dir, state)

    with_lock(state_dir, _update)


def handle_tab_focused(state_dir: Path):
    event_data = parse_event()
    ws_id = event_data.get("workspace_id") or os.environ.get("HERDR_WORKSPACE_ID")
    tab_id = event_data.get("tab_id") or os.environ.get("HERDR_TAB_ID")
    if not ws_id or not tab_id:
        return

    def _update():
        state = load_state(state_dir)
        state["tabs"][ws_id] = tab_id
        save_state(state_dir, state)

    with_lock(state_dir, _update)


def handle_tab_closed(state_dir: Path):
    event_data = parse_event()
    ws_id = event_data.get("workspace_id") or os.environ.get("HERDR_WORKSPACE_ID")
    tab_id = event_data.get("tab_id") or os.environ.get("HERDR_TAB_ID")
    if not ws_id or not tab_id:
        return

    def _update():
        state = load_state(state_dir)
        if state["tabs"].get(ws_id) == tab_id:
            state["tabs"].pop(ws_id, None)
            save_state(state_dir, state)

    with_lock(state_dir, _update)


def handle_closed(state_dir: Path):
    event_data = parse_event()
    ws_id = event_data.get("workspace_id") or os.environ.get("HERDR_WORKSPACE_ID")
    if not ws_id:
        return

    def _update():
        state = load_state(state_dir)
        state["stack"] = [w for w in state["stack"] if w != ws_id]
        state["tabs"].pop(ws_id, None)
        save_state(state_dir, state)

    with_lock(state_dir, _update)


def handle_startup(state_dir: Path):
    focused_id, workspaces = get_live_workspaces()
    if not workspaces:
        return

    valid_ids = set(workspaces.keys())

    def _update():
        state = load_state(state_dir)
        stack = [w for w in state["stack"] if w in valid_ids]
        tabs = {w: tid for w, tid in state["tabs"].items() if w in valid_ids}

        for wid, winfo in workspaces.items():
            active_tab = winfo.get("active_tab_id")
            if active_tab:
                tabs[wid] = active_tab

        if focused_id and focused_id in valid_ids:
            if focused_id in stack:
                stack.remove(focused_id)
            stack.insert(0, focused_id)

        state["stack"] = stack
        state["tabs"] = tabs
        save_state(state_dir, state)

    with_lock(state_dir, _update)


def handle_toggle(state_dir: Path):
    focused_id, workspaces = get_live_workspaces()
    if not workspaces:
        return

    valid_ids = set(workspaces.keys())

    def _update():
        state = load_state(state_dir)
        stack = [w for w in state["stack"] if w in valid_ids]
        tabs = state["tabs"]

        # Cache active_tab_id reported by live workspace list
        for wid, winfo in workspaces.items():
            active_tab = winfo.get("active_tab_id")
            if active_tab:
                tabs[wid] = active_tab

        # Self-heal current workspace position
        if focused_id and focused_id in valid_ids:
            if not stack or stack[0] != focused_id:
                if focused_id in stack:
                    stack.remove(focused_id)
                stack.insert(0, focused_id)

        target_ws = None
        target_tab = None

        if len(stack) >= 2:
            target_ws = stack[1]
            # Swap top 2 elements (MRU flip-flop like tmux last-window)
            stack[0], stack[1] = stack[1], stack[0]
            target_tab = tabs.get(target_ws) or workspaces.get(target_ws, {}).get("active_tab_id")
        elif len(stack) == 1 and len(valid_ids) >= 2:
            # Fallback for empty history: pick first alternative workspace
            alternatives = [w for w in valid_ids if w != stack[0]]
            if alternatives:
                target_ws = alternatives[0]
                stack.insert(0, target_ws)
                target_tab = tabs.get(target_ws) or workspaces.get(target_ws, {}).get("active_tab_id")

        state["stack"] = stack
        state["tabs"] = tabs
        save_state(state_dir, state)

        return target_ws, target_tab

    res = with_lock(state_dir, _update)
    if not res:
        return

    target_ws, target_tab = res
    if target_ws:
        run_herdr("workspace", "focus", target_ws)
        if target_tab:
            run_herdr("tab", "focus", target_tab)


def main():
    if len(sys.argv) < 2:
        return

    subcommand = sys.argv[1]
    state_dir = get_state_dir()

    if subcommand == "toggle":
        handle_toggle(state_dir)
    elif subcommand == "focused":
        handle_focused(state_dir)
    elif subcommand == "tab_focused":
        handle_tab_focused(state_dir)
    elif subcommand == "tab_closed":
        handle_tab_closed(state_dir)
    elif subcommand == "closed":
        handle_closed(state_dir)
    elif subcommand == "startup":
        handle_startup(state_dir)


if __name__ == "__main__":
    main()
