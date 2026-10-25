#!/usr/bin/env python3
"""codex-context-meter — a Codex CLI statusline plugin.

Shows the current conversation's context-window usage and token consumption
as a colored dot + percentage in the Codex TUI status line, and can print a
detailed token report with `codex-context-meter report`.

Data sources (first hit wins):
  1. Session JSON piped to stdin by Codex's `tui.status_line` hook.
  2. Latest rollout file under ~/.codex/sessions/**/*.jsonl
     (token_count / turn_context events).

The script never raises: any error results in empty (statusline) or a short
message (report), so it can't break the Codex UI.
"""

import json
import os
import sys

DEFAULT_CONTEXT_WINDOW = 200_000
CODEX_DIR = os.path.expanduser(os.environ.get("CODEX_HOME", "~/.codex"))
SESSIONS_DIR = os.path.join(CODEX_DIR, "sessions")

GREEN, YELLOW, RED, RESET = "\033[32m", "\033[33m", "\033[31m", "\033[0m"

# ------------------------------------------------------------------ i18n
# 输出文案中英双语：CCM_LANG=en 强制英文，否则默认中文。
# English output: set CCM_LANG=en (default is Chinese).

_LANG = "en" if os.environ.get("CCM_LANG", "").lower().startswith("en") else "zh"

S = {
    "zh": {
        "no_data": "⚪ 暂无 token 数据",
        "no_sessions": "未找到会话记录：{dir}",
        "session_empty": "最近的会话还没有 token 数据。",
        "session_file": "会话：{name}",
        "ctx": "上下文占用：{used} / {window}（已用 {pct}%，剩余 {left}）",
        "ctx_no_window": "上下文占用：{used}（上下文窗口大小未知）",
        "cum_header": "累计消耗 token（各轮累加；每轮的输入都会重新计入完整上下文）：",
        "input": "  输入",
        "cached": "  缓存命中输入",
        "output": "  输出",
        "reasoning": "  推理输出",
        "total": "  总计",
        "turns_header": "\n共 {n} 轮（每轮累计总量）：",
        "turn_row": "  第 {i:>3} 轮：{v}",
    },
    "en": {
        "no_data": "⚪ no token data yet",
        "no_sessions": "No rollout files found in {dir}",
        "session_empty": "Latest session has no token data yet.",
        "session_file": "Session: {name}",
        "ctx": "Context usage : {used} / {window} ({pct}% used, {left} left)",
        "ctx_no_window": "Context usage : {used} (context window size unknown)",
        "cum_header": "Cumulative tokens (sum over all turns; input re-counts the context sent each turn):",
        "input": "  input",
        "cached": "  cached input",
        "output": "  output",
        "reasoning": "  reasoning output",
        "total": "  total",
        "turns_header": "\nTurns recorded: {n} (cumulative total per turn):",
        "turn_row": "  turn {i:>3}: {v}",
    },
}[_LANG]


def fmt_tokens(n):
    if n is None:
        return "?"
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "?"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def dot_for(pct):
    if pct is None:
        return "⚪"
    color = GREEN if pct < 60 else YELLOW if pct < 85 else RED
    return f"{color}●{RESET}"


# ---------------------------------------------------------------- parsing

def usage_from_stdin(data):
    """Extract token usage from the JSON Codex pipes to a status_line command.

    Field names are matched loosely because the schema has shifted across
    Codex versions.
    """
    try:
        obj = json.loads(data)
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None

    def dig(d, *path):
        for key in path:
            if not isinstance(d, dict):
                return None
            d = d.get(key)
        return d

    window = (
        dig(obj, "context_window")
        or dig(obj, "model_context_window")
        or dig(obj, "model", "context_window")
    )
    used = (
        dig(obj, "tokens_in_context")
        or dig(obj, "context_tokens")
        or dig(obj, "token_usage", "total_tokens")
        or dig(obj, "usage", "total_tokens")
        or dig(obj, "total_token_usage", "tokens_in_context_window")
    )
    totals = dig(obj, "total_token_usage") or dig(obj, "usage") or {}
    if used is None and isinstance(totals, dict):
        for k in ("total_tokens", "input_tokens"):
            if isinstance(totals.get(k), int):
                used = totals[k]
                break
    if used is None:
        return None
    return {
        "used": used,
        "window": window or DEFAULT_CONTEXT_WINDOW,
        "totals": totals if isinstance(totals, dict) else {},
    }


def iter_rollout_files(sessions_dir):
    try:
        entries = []
        for root, _dirs, files in os.walk(sessions_dir):
            for f in files:
                if f.endswith(".jsonl"):
                    p = os.path.join(root, f)
                    entries.append((os.path.getmtime(p), p))
        entries.sort()
        return [p for _, p in entries]
    except Exception:
        return []


def session_names(codex_dir=CODEX_DIR):
    """Map session id -> thread name from ~/.codex/session_index.jsonl."""
    names = {}
    try:
        with open(os.path.join(codex_dir, "session_index.jsonl"),
                  "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                sid, name = rec.get("id"), rec.get("thread_name")
                if sid and name:
                    names[sid] = name
    except Exception:
        pass
    return names


def session_info(path, names):
    """Return (title, project, session_id) for a rollout file.

    title: thread_name from session_index.jsonl, else the first user message,
           else None (never a directory name — callers group by project).
    project: cwd basename from session_meta.
    Sessions whose thread_source marks them as background agent runs (e.g.
    guardian_review) get title None so callers can filter them out.
    """
    stem = os.path.basename(path)
    title = next((n for sid, n in names.items() if sid in stem), None)
    cwd = first_msg = None
    background = False
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if cwd is None and '"session_meta"' in line:
                    try:
                        p = json.loads(line).get("payload") or {}
                        cwd = p.get("cwd")
                        if p.get("thread_source") not in (None, "user"):
                            background = True
                    except Exception:
                        pass
                if title is None and first_msg is None and '"user_message"' in line:
                    try:
                        msg = (json.loads(line).get("payload") or {}).get("message", "")
                        msg = " ".join(str(msg).split())
                        if msg:
                            first_msg = msg[:40] + ("…" if len(msg) > 40 else "")
                    except Exception:
                        pass
                if cwd and (title or first_msg):
                    break
    except Exception:
        pass
    if background:
        return None, None
    project = (os.path.basename(cwd.rstrip("/")) or cwd) if cwd else ""
    return title or first_msg, project


def name_for(path, names):
    """Display name for the CLI report: title, else project, else file stem."""
    title, project = session_info(path, names)
    return title or project or os.path.basename(path)


def usage_from_rollout(path):
    """Scan a rollout JSONL file; return latest token stats found."""
    used = window = None
    totals = {}
    per_turn = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if not isinstance(rec, dict):
                    continue
                payload = rec.get("payload", rec)
                if not isinstance(payload, dict):
                    continue
                ptype = payload.get("type", "")
                info = payload.get("info") or {}
                if ptype in ("token_count", "turn_context"):
                    tu = info.get("total_token_usage") or payload.get("total_token_usage") or {}
                    if isinstance(tu, dict) and tu:
                        totals = tu
                        per_turn.append(tu)
                    cw = info.get("model_context_window") or payload.get("model_context_window")
                    if isinstance(cw, int):
                        window = cw
                    # Current context occupancy: prefer the explicit field,
                    # else the last turn's full request size (total_tokens of
                    # last_token_usage). NEVER use cumulative total_token_usage
                    # — that sums every turn and can exceed the window.
                    ctx = info.get("tokens_in_context_window")
                    last = info.get("last_token_usage") or payload.get("last_token_usage") or {}
                    if isinstance(ctx, int):
                        used = ctx
                    elif isinstance(last.get("total_tokens"), int):
                        used = last["total_tokens"]
    except Exception:
        return None
    if used is None:
        return None
    if isinstance(window, int) and used > window:
        # Recorded window is stale/suspect; don't show nonsense percentages.
        window = None
    return {
        "used": used,
        "window": window or DEFAULT_CONTEXT_WINDOW,
        "totals": totals,
        "per_turn": per_turn,
    }


def get_usage():
    """Try stdin first (statusline invocation), then latest rollout file."""
    if not sys.stdin.isatty():
        try:
            data = sys.stdin.read()
        except Exception:
            data = ""
        if data.strip():
            u = usage_from_stdin(data)
            if u:
                return u
    files = iter_rollout_files(SESSIONS_DIR)
    if files:
        return usage_from_rollout(files[-1])
    return None


# ------------------------------------------------------------------ output

def statusline():
    try:
        u = get_usage()
        if not u or u.get("used") is None:
            print(S["no_data"])
            return
        used, window = u["used"], u.get("window") or DEFAULT_CONTEXT_WINDOW
        pct = round(100 * used / window) if window else None
        print(f"{dot_for(pct)} {pct}% · {fmt_tokens(used)}/{fmt_tokens(window)}")
    except Exception:
        print("")


def report(sessions_dir=SESSIONS_DIR):
    files = iter_rollout_files(sessions_dir)
    if not files:
        print(S["no_sessions"].format(dir=sessions_dir))
        return
    u = usage_from_rollout(files[-1])
    if not u:
        print(S["session_empty"])
        return
    used, window = u["used"], u.get("window")
    t = u["totals"]
    pct = round(100 * used / window) if (used and window) else None
    print(S["session_file"].format(name=name_for(files[-1], session_names())))
    if window and pct is not None:
        print(S["ctx"].format(used=fmt_tokens(used), window=fmt_tokens(window),
                              pct=pct, left=fmt_tokens(max(0, window - used))))
    else:
        print(S["ctx_no_window"].format(used=fmt_tokens(used)))
    print(S["cum_header"])
    for label, key in [("input", "input_tokens"), ("cached", "cached_input_tokens"),
                       ("output", "output_tokens"), ("reasoning", "reasoning_output_tokens"),
                       ("total", "total_tokens")]:
        v = t.get(key)
        if isinstance(v, int):
            print(f"{S[label]:16s} {v:,}")
    per_turn = u.get("per_turn") or []
    if per_turn:
        print(S["turns_header"].format(n=len(per_turn)))
        for i, tu in enumerate(per_turn[-20:], start=max(1, len(per_turn) - 19)):
            tt = tu.get("total_tokens")
            v = f"{tt:,}" if isinstance(tt, int) else "?"
            print(S["turn_row"].format(i=i, v=v))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    flags = {a for a in sys.argv[1:] if a.startswith("-")}
    sessions_dir = SESSIONS_DIR
    for i, a in enumerate(sys.argv):
        if a == "--sessions-dir" and i + 1 < len(sys.argv):
            sessions_dir = sys.argv[i + 1]
    if args and args[0] == "report":
        report(sessions_dir)
    else:
        statusline()


if __name__ == "__main__":
    main()
