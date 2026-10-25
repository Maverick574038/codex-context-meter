#!/usr/bin/env python3
"""codex-context-meter-gui — 常驻图形化用量面板（中文版）。

零依赖：Python 内置 HTTP 服务 + 浏览器页面，每 3 秒自动刷新。
数据与 CLI 版同源（~/.codex/sessions 最新 rollout 文件）。

用法：
  bin/codex-context-meter-gui [--port 8787]
然后浏览器打开 http://localhost:8787 （启动时会尝试自动打开）

英文版：bin/codex-context-meter-gui-en（CCM_LANG=en）
"""

import json
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
from importlib.machinery import SourceFileLoader

_core = os.path.join(os.path.dirname(os.path.abspath(__file__)), "windows-codex-context-meter.py")
_spec = importlib.util.spec_from_loader("ccm_core", SourceFileLoader("ccm_core", _core))
ccm = importlib.util.module_from_spec(_spec)
sys.modules["ccm_core"] = ccm
_spec.loader.exec_module(ccm)

_LANG = "en" if os.environ.get("CCM_LANG", "").lower().startswith("en") else "zh"

T = {
    "zh": {
        "title": "Codex 上下文用量",
        "session": "会话",
        "usage": "上下文占用",
        "left": "剩余",
        "cum": "累计消耗",
        "input": "输入",
        "cached": "缓存命中",
        "output": "输出",
        "reasoning": "推理输出",
        "turns": "逐轮趋势（每轮累计总量）",
        "updated": "更新于",
        "no_data": "暂无数据 — 在 Codex 里开始对话后自动出现",
        "window_unknown": "窗口大小未知",
        "refresh": "刷新",
        "latest": "最新会话",
        "expand": "▾ 展开全部（还有 {n} 条）",
        "collapse": "▴ 收起（共 {n} 条）",
    },
    "en": {
        "title": "Codex Context Meter",
        "session": "Session",
        "usage": "Context usage",
        "left": "left",
        "cum": "Cumulative tokens",
        "input": "Input",
        "cached": "Cached input",
        "output": "Output",
        "reasoning": "Reasoning output",
        "turns": "Per-turn trend (cumulative)",
        "updated": "Updated",
        "no_data": "No data yet — start chatting in Codex",
        "window_unknown": "window size unknown",
        "refresh": "Refresh",
        "latest": "Latest session",
        "expand": "▾ Show all ({n} more)",
        "collapse": "▴ Collapse ({n} total)",
    },
}[_LANG]

PAGE = """<!doctype html>
<html lang="__LANG__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; margin: 0; }
  body { font-family: -apple-system, "PingFang SC", "Segoe UI", sans-serif;
         background: #16181d; color: #e6e6e6; min-height: 100vh;
         display: flex; flex-direction: column; align-items: center;
         padding: 28px 16px; gap: 20px; }
  h1 { font-size: 18px; font-weight: 600; color: #9aa0aa; letter-spacing: .5px; }
  .session { font-size: 15px; color: #c9cdd4; max-width: 640px;
             overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .ring-row { display: flex; align-items: center; gap: 28px; flex-wrap: wrap;
              justify-content: center; }
  .ring-wrap { position: relative; width: 200px; height: 200px; flex-shrink: 0; }
  svg { transform: rotate(-90deg); }
  .ring-bg { stroke: #2a2e36; }
  .ring { stroke-linecap: round; transition: stroke-dashoffset .6s ease, stroke .6s; }
  .pct { position: absolute; inset: 0; display: flex; align-items: center;
         justify-content: center; }
  .pct b { font-size: 42px; font-variant-numeric: tabular-nums; }
  .detail { text-align: left; min-width: 180px; }
  .detail .u { font-size: 22px; font-variant-numeric: tabular-nums; font-weight: 600; }
  .detail .l { font-size: 13px; color: #9aa0aa; margin-top: 6px; }
  .bar { width: min(640px, 92vw); height: 10px; background: #2a2e36;
         border-radius: 5px; overflow: hidden; }
  .bar i { display: block; height: 100%; border-radius: 5px;
           transition: width .6s ease, background .6s; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
           gap: 10px; width: min(640px, 92vw); }
  .card { background: #1e2128; border: 1px solid #2a2e36; border-radius: 10px;
          padding: 12px 14px; }
  .card .k { font-size: 12px; color: #9aa0aa; }
  .card .v { font-size: 20px; margin-top: 4px; font-variant-numeric: tabular-nums; }
  .trend { width: min(640px, 92vw); background: #1e2128; border: 1px solid #2a2e36;
           border-radius: 10px; padding: 14px; }
  .trend h2 { font-size: 13px; color: #9aa0aa; font-weight: 500; margin-bottom: 10px; }
  .bars { display: flex; align-items: flex-end; gap: 4px; height: 90px; }
  .bars i { flex: 1; background: #3d7bfd; border-radius: 3px 3px 0 0; min-height: 2px;
            opacity: .85; transition: height .4s; }
  .meta { font-size: 12px; color: #6b7078; }
  .controls { display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
              justify-content: center; width: min(640px, 92vw); }
  select, button { background: #1e2128; color: #e6e6e6; border: 1px solid #2a2e36;
                   border-radius: 8px; padding: 7px 12px; font-size: 13px;
                   font-family: inherit; }
  select#sess { max-width: min(420px, 60vw); }
  button { cursor: pointer; }
  button:hover, select:hover { border-color: #3d7bfd; }
</style>
</head>
<body>
<h1>__TITLE__</h1>
<div class="controls">
  <select id="proj"></select>
  <select id="sess"></select>
  <button id="btn" title="__REFRESH__">⟳</button>
  <select id="interval">
    <option value="3000">3s</option>
    <option value="5000">5s</option>
    <option value="10000">10s</option>
    <option value="30000">30s</option>
  </select>
</div>
<div class="ring-row">
  <div class="ring-wrap">
    <svg width="200" height="200">
      <circle class="ring-bg" cx="100" cy="100" r="86" fill="none" stroke-width="14"/>
      <circle class="ring" id="ring" cx="100" cy="100" r="86" fill="none" stroke-width="14"/>
    </svg>
    <div class="pct"><b id="pct">–</b></div>
  </div>
  <div class="detail">
    <div class="u" id="used"></div>
    <div class="l" id="leftline"></div>
  </div>
</div>
<div class="bar"><i id="bar"></i></div>
<div class="stats" id="stats"></div>
<div class="trend"><h2>__TURNS__</h2><div class="bars" id="bars"></div></div>
<div class="meta" id="meta"></div>
<script>
const C = 2 * Math.PI * 86;
const labels = __LABELS__;
let timer = null;
let groups = [];
const projSel = document.getElementById("proj");
const sessSel = document.getElementById("sess");
const intSel = document.getElementById("interval");

function color(p) { return p < 60 ? "#34c759" : p < 85 ? "#ffd60a" : "#ff453a"; }

function fillSess(project, keepPath) {
  const g = groups.find(g => g.project === project);
  sessSel.innerHTML = "";
  if (!g) return;
  const expanded = sessSel.dataset.expanded === project;
  const list = g.sessions;
  const shown = expanded ? list : list.slice(0, 5);
  for (const s of shown) {
    const o = document.createElement("option");
    o.value = s.path;
    o.textContent = s.name;
    sessSel.appendChild(o);
  }
  if (list.length > 5) {
    const o = document.createElement("option");
    o.value = "__expand__";
    o.textContent = expanded
      ? labels.collapse.replace("{n}", list.length)
      : labels.expand.replace("{n}", list.length - 5);
    sessSel.appendChild(o);
  }
  if (keepPath && list.some(s => s.path === keepPath)) {
    // Ensure the kept selection is visible: expand if it's beyond the first 5.
    if (!expanded && !shown.some(s => s.path === keepPath)) {
      sessSel.dataset.expanded = project;
      fillSess(project, keepPath);
      return;
    }
    sessSel.value = keepPath;
  }
}

async function loadSessions(keepPath) {
  try {
    groups = await (await fetch("/api/sessions")).json();
  } catch (e) { return; }
  const prevProj = projSel.value;
  projSel.innerHTML = "";
  for (const g of groups) {
    const o = document.createElement("option");
    o.value = g.project;
    o.textContent = g.project + " (" + g.sessions.length + ")";
    projSel.appendChild(o);
  }
  let proj = groups.length ? groups[0].project : "";
  if (keepPath) {
    const g = groups.find(g => g.sessions.some(s => s.path === keepPath));
    if (g) proj = g.project;
  } else if (prevProj && groups.some(g => g.project === prevProj)) {
    proj = prevProj;
  }
  projSel.value = proj;
  fillSess(proj, keepPath);
}

async function tick() {
  let d;
  try {
    const q = sessSel.value ? "?path=" + encodeURIComponent(sessSel.value) : "";
    d = await (await fetch("/api/usage" + q)).json();
  } catch (e) { return; }
  const ring = document.getElementById("ring");
  const bar = document.getElementById("bar");
  if (d.path && d.path !== sessSel.value &&
      ![...sessSel.options].some(o => o.value === d.path)) {
    await loadSessions(d.path);
  }
  if (d.path && !sessSel.value) sessSel.value = d.path;
  if (d.pct == null) {
    document.getElementById("pct").textContent = "–";
    document.getElementById("used").textContent = "";
    document.getElementById("leftline").textContent = d.message || "";
    ring.style.strokeDashoffset = C;
    bar.style.width = "0";
  } else {
    ring.style.strokeDasharray = C;
    ring.style.strokeDashoffset = C * (1 - Math.min(d.pct, 100) / 100);
    ring.style.stroke = color(d.pct);
    bar.style.width = Math.min(d.pct, 100) + "%";
    bar.style.background = color(d.pct);
    document.getElementById("pct").textContent = d.pct + "%";
    document.getElementById("pct").style.color = color(d.pct);
    document.getElementById("used").textContent = d.used_fmt + " / " + d.window_fmt;
    document.getElementById("leftline").textContent = d.left_fmt ? d.left_fmt + " " + labels.left : "";
  }
  const t = d.totals || {};
  document.getElementById("stats").innerHTML =
    [["input", t.input_tokens], ["cached", t.cached_input_tokens],
     ["output", t.output_tokens], ["reasoning", t.reasoning_output_tokens]]
      .filter(x => typeof x[1] === "number")
      .map(x => `<div class="card"><div class="k">${labels[x[0]]}</div><div class="v">${x[1].toLocaleString()}</div></div>`)
      .join("");
  const turns = (d.per_turn || []).slice(-30);
  const max = Math.max(...turns, 1);
  document.getElementById("bars").innerHTML =
    turns.map(v => `<i style="height:${Math.max(2, v / max * 100)}%" title="${v.toLocaleString()}"></i>`).join("");
  document.getElementById("meta").textContent = labels.updated + " " + new Date().toLocaleTimeString();
}

function restart() {
  if (timer) clearInterval(timer);
  timer = setInterval(tick, parseInt(intSel.value, 10));
}

document.getElementById("btn").onclick = () => location.reload();
projSel.onchange = () => { delete sessSel.dataset.expanded; fillSess(projSel.value, null); tick(); };
sessSel.onchange = () => {
  if (sessSel.value === "__expand__") {
    const expanded = sessSel.dataset.expanded === projSel.value;
    if (expanded) delete sessSel.dataset.expanded; else sessSel.dataset.expanded = projSel.value;
    fillSess(projSel.value, null);
    return;
  }
  tick();
};
intSel.onchange = () => { restart(); tick(); };
loadSessions(null).then(tick);
restart();
</script>
</body>
</html>
"""


def render_page():
    labels = {k: T[k] for k in ("left", "input", "cached", "output", "reasoning", "updated", "expand", "collapse")}
    return (PAGE.replace("__LANG__", _LANG)
                .replace("__TITLE__", T["title"])
                .replace("__TURNS__", T["turns"])
                .replace("__REFRESH__", T["refresh"])
                .replace("__LABELS__", json.dumps(labels, ensure_ascii=False)))


def sessions_payload():
    """Rollout files grouped by project (cwd), newest project first.

    Only real conversations are listed: a session must have at least one
    user message. Background sessions (e.g. Codex's automated "Guardian
    review" runs) have none and are filtered out.
    """
    names = ccm.session_names()
    groups = {}
    order = []
    for p in reversed(ccm.iter_rollout_files(ccm.SESSIONS_DIR)):
        title, project = ccm.session_info(p, names)
        if not title:
            continue
        proj = project or "?"
        if proj not in groups:
            groups[proj] = []
            order.append(proj)
        groups[proj].append({"path": p, "name": title})
    return [{"project": proj, "sessions": groups[proj]} for proj in order
            if groups[proj]]


def usage_payload(path=None):
    files = ccm.iter_rollout_files(ccm.SESSIONS_DIR)
    if not files:
        return {"pct": None, "message": T["no_data"]}
    target = path if (path and os.path.isfile(path) and path.endswith(".jsonl")) else files[-1]
    u = ccm.usage_from_rollout(target)
    if not u or u.get("used") is None:
        return {"pct": None, "message": T["no_data"], "path": target}
    used, window = u["used"], u.get("window")
    pct = round(100 * used / window) if (used and window) else None
    return {
        "session": ccm.name_for(target, ccm.session_names()),
        "path": target,
        "pct": pct,
        "used_fmt": ccm.fmt_tokens(used),
        "window_fmt": ccm.fmt_tokens(window) if window else T["window_unknown"],
        "left_fmt": ccm.fmt_tokens(max(0, window - used)) if (window and pct is not None) else None,
        "totals": u.get("totals") or {},
        "per_turn": [t.get("total_tokens") for t in (u.get("per_turn") or [])
                     if isinstance(t.get("total_tokens"), int)],
        "message": T["no_data"] if pct is None else None,
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        url = urlparse(self.path)
        if url.path == "/api/sessions":
            body = json.dumps(sessions_payload(), ensure_ascii=False).encode()
            ctype = "application/json; charset=utf-8"
        elif url.path == "/api/usage":
            path = (parse_qs(url.query).get("path") or [None])[0]
            body = json.dumps(usage_payload(path), ensure_ascii=False).encode()
            ctype = "application/json; charset=utf-8"
        else:
            body = render_page().encode()
            ctype = "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def main():
    port = 8787
    if "--port" in sys.argv:
        i = sys.argv.index("--port")
        if i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
    url = f"http://localhost:{port}"
    print(f"{T['title']} → {url}  (Ctrl+C 退出 / to quit)")
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError:
        print(f"端口 {port} 已被占用 — 可能已有一个实例在运行，直接打开 {url} 即可；"
              f"或换个端口：--port 8788 / Port {port} busy — already running? Open {url} or use --port 8788")
        return
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
