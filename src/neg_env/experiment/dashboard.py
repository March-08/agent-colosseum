"""Local dashboard for experiment runs: config, matches, events, messages, actions."""

import webbrowser
from threading import Thread
from typing import Any

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from neg_env.experiment.runner import ExperimentConfig, ExperimentResult


def _serialize(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return obj


def _payload_from_state(state: dict[str, Any]) -> dict[str, Any]:
    config = state.get("config")
    match_results = state.get("match_results", [])
    current_match = state.get("current_match")
    status = state.get("status", "running")
    total_duration = state.get("total_duration_seconds", 0)
    game_id = state.get("game_id", "")
    num_matches = state.get("num_matches", 0)
    finished = sum(1 for m in match_results if m.get("status") == "finished")
    completion_rate = finished / len(match_results) if match_results else 0.0
    payoffs: dict[str, list[float]] = {}
    for m in match_results:
        if m.get("outcome") and "payoffs" in (m.get("outcome") or {}):
            for p in (m["outcome"] or {}).get("payoffs", []):
                aid = p.get("agent_id", "")
                payoffs.setdefault(aid, []).append(float(p.get("value", 0)))
    mean_payoffs = {aid: sum(v) / len(v) for aid, v in payoffs.items() if v}
    result_dict = {
        "game_id": game_id,
        "num_matches": num_matches,
        "match_results": match_results,
        "current_match": current_match,
        "total_duration_seconds": total_duration,
        "completion_rate": completion_rate,
        "mean_payoffs": mean_payoffs,
    }
    return {"config": _serialize(config) if config else {}, "result": result_dict, "status": status}


def _build_app_realtime(state: dict[str, Any]) -> Starlette:
    async def api_result(_request: Any) -> JSONResponse:
        return JSONResponse(_payload_from_state(state))

    async def index(_request: Any) -> HTMLResponse:
        return HTMLResponse(_HTML_POLLING)

    return Starlette(
        debug=False,
        routes=[
            Route("/", index),
            Route("/api/result", api_result),
        ],
    )


def _build_app(config: ExperimentConfig, result: ExperimentResult) -> Starlette:
    result_dict = _serialize(result)
    result_dict["completion_rate"] = result.completion_rate
    result_dict["mean_payoffs"] = result.mean_payoffs
    payload = {"config": _serialize(config), "result": result_dict, "status": "finished"}

    async def api_result(_request: Any) -> JSONResponse:
        return JSONResponse(payload)

    async def index(_request: Any) -> HTMLResponse:
        return HTMLResponse(_HTML)

    return Starlette(
        debug=False,
        routes=[
            Route("/", index),
            Route("/api/result", api_result),
        ],
    )


def serve_realtime(
    state: dict[str, Any],
    port: int = 8765,
    open_browser: bool = True,
) -> Thread:
    import uvicorn

    app = _build_app_realtime(state)
    if open_browser:
        def open_():
            webbrowser.open(f"http://127.0.0.1:{port}")

        Thread(target=open_, daemon=True).start()

    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

    t = Thread(target=run_server, daemon=False)
    t.start()
    return t


def serve(
    config: ExperimentConfig,
    result: ExperimentResult,
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    app = _build_app(config, result)
    import uvicorn

    if open_browser:
        def open_():
            webbrowser.open(f"http://127.0.0.1:{port}")

        Thread(target=open_, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Experiment Dashboard</title>
  <style>
    :root { --bg: #0f0f12; --card: #1a1a1f; --border: #2a2a32; --text: #e4e4e7; --muted: #71717a; --accent: #a78bfa; --ok: #22c55e; --err: #ef4444; }
    * { box-sizing: border-box; }
    body { font-family: 'JetBrains Mono', 'SF Mono', monospace; font-size: 13px; background: var(--bg); color: var(--text); margin: 0; padding: 1rem; line-height: 1.5; }
    h1 { font-size: 1.25rem; margin: 0 0 1rem; color: var(--accent); }
    h2 { font-size: 1rem; margin: 1.5rem 0 0.5rem; color: var(--muted); }
    section { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
    .badge { padding: 0.25rem 0.5rem; border-radius: 4px; font-weight: bold; }
    .badge-running { background: #3b82f6; color: #fff; }
    .badge-finished { background: var(--ok); color: #0f0f12; }
    .summary { display: flex; gap: 1.5rem; flex-wrap: wrap; }
    .summary span { color: var(--muted); }
    .summary strong { color: var(--text); }
    .match { margin-bottom: 1rem; }
    .match-header { cursor: pointer; padding: 0.5rem 0; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
    .match-header:hover { color: var(--accent); }
    .match-body { padding: 0.75rem 0; }
    .event { padding: 0.4rem 0; border-bottom: 1px solid var(--border); font-size: 12px; }
    .event:last-child { border-bottom: none; }
    .event-type { display: inline-block; width: 80px; color: var(--accent); }
    .event.message .event-type { color: #38bdf8; }
    .event.action .event-type { color: var(--ok); }
    .event.match_start .event-type, .event.match_end .event-type { color: var(--muted); }
    .agent { color: var(--muted); margin-right: 0.5rem; }
    .payload { color: var(--muted); margin-left: 0.5rem; }
    .outcome { margin-top: 0.5rem; padding: 0.5rem; background: var(--bg); border-radius: 4px; }
    pre { margin: 0; white-space: pre-wrap; word-break: break-all; }
    .error { color: var(--err); }
  </style>
</head>
<body>
  <h1>Experiment Dashboard</h1>
  <div id="root">Loading…</div>
  <script>
    (function() {
      fetch('/api/result').then(r => r.json()).then(data => {
        const root = document.getElementById('root');
        root.innerHTML = '<section><h2>Config</h2><pre>' + JSON.stringify(data.config || {}, null, 2) + '</pre></section>' +
          '<section><h2>Summary</h2><div class="summary"><span>Completion rate: <strong>' + ((data.result && data.result.completion_rate != null) ? (data.result.completion_rate * 100).toFixed(0) + '%' : '–') + '</strong></span><span>Total duration: <strong>' + (data.result && data.result.total_duration_seconds != null ? data.result.total_duration_seconds.toFixed(2) + 's' : '–') + '</strong></span></div></section>';
        const matches = (data.result && data.result.match_results) || [];
        const sec = document.createElement('section');
        sec.innerHTML = '<h2>Matches</h2>';
        matches.forEach((m, i) => {
          const div = document.createElement('div');
          div.className = 'match';
          const log = m.log || {};
          const events = log.events || [];
          const outcome = m.outcome || log.outcome;
          const body = document.createElement('div');
          body.className = 'match-body';
          body.style.display = 'none';
          events.forEach(ev => {
            const e = document.createElement('div');
            e.className = 'event ' + (ev.event_type || '');
            let h = '<span class="event-type">' + (ev.event_type || '') + '</span> ';
            if (ev.agent_id) h += '<span class="agent">' + ev.agent_id + '</span> ';
            if (ev.event_type === 'message' && ev.data) h += (ev.data.content || '') + (ev.data.to_agent_ids && ev.data.to_agent_ids.length ? ' <span class="payload">→ ' + ev.data.to_agent_ids.join(', ') + '</span>' : '');
            if (ev.event_type === 'action' && ev.data) h += (ev.data.action_type || '') + (ev.data.payload && Object.keys(ev.data.payload).length ? ' <span class="payload">' + JSON.stringify(ev.data.payload) + '</span>' : '') + (ev.data.ok === false ? ' <span class="error">FAILED</span>' : '');
            if (ev.event_type === 'match_end' && ev.data && ev.data.status) h += ev.data.status;
            e.innerHTML = h;
            body.appendChild(e);
          });
          if (outcome && Object.keys(outcome).length) { const o = document.createElement('div'); o.className = 'outcome'; o.innerHTML = '<strong>Outcome</strong><pre>' + JSON.stringify(outcome, null, 2) + '</pre>'; body.appendChild(o); }
          const header = document.createElement('div');
          header.className = 'match-header';
          header.innerHTML = '<span>Match ' + (i + 1) + ': ' + (m.match_id || '').slice(0, 8) + '…</span><span>' + (m.status || '') + ' · ' + (m.num_turns || 0) + ' turns · ' + (m.duration_seconds != null ? m.duration_seconds.toFixed(2) + 's' : '') + (m.error ? ' · <span class="error">' + m.error + '</span>' : '') + '</span>';
          header.onclick = () => { body.style.display = body.style.display === 'none' ? 'block' : 'none'; };
          div.appendChild(header); div.appendChild(body);
          sec.appendChild(div);
        });
        root.appendChild(sec);
      }).catch(e => { document.getElementById('root').textContent = 'Failed to load: ' + e.message; });
    })();
  </script>
</body>
</html>
"""

_HTML_POLLING = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Experiment Dashboard</title>
  <style>
    :root { --bg: #0f0f12; --card: #1a1a1f; --border: #2a2a32; --text: #e4e4e7; --muted: #71717a; --accent: #a78bfa; --ok: #22c55e; --err: #ef4444; }
    * { box-sizing: border-box; }
    body { font-family: 'JetBrains Mono', 'SF Mono', monospace; font-size: 13px; background: var(--bg); color: var(--text); margin: 0; padding: 1rem; line-height: 1.5; }
    h1 { font-size: 1.25rem; margin: 0 0 1rem; color: var(--accent); }
    h2 { font-size: 1rem; margin: 1.5rem 0 0.5rem; color: var(--muted); }
    section { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
    .badge { padding: 0.25rem 0.5rem; border-radius: 4px; font-weight: bold; }
    .badge-running { background: #3b82f6; color: #fff; }
    .badge-finished { background: var(--ok); color: #0f0f12; }
    .summary { display: flex; gap: 1.5rem; flex-wrap: wrap; }
    .summary span { color: var(--muted); }
    .summary strong { color: var(--text); }
    .match { margin-bottom: 1rem; }
    .match-header { cursor: pointer; padding: 0.5rem 0; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
    .match-header:hover { color: var(--accent); }
    .match-body { padding: 0.75rem 0; }
    .event { padding: 0.4rem 0; border-bottom: 1px solid var(--border); font-size: 12px; }
    .event-type { display: inline-block; width: 80px; color: var(--accent); }
    .event.message .event-type { color: #38bdf8; }
    .event.action .event-type { color: var(--ok); }
    .agent { color: var(--muted); margin-right: 0.5rem; }
    .payload { color: var(--muted); margin-left: 0.5rem; }
    .outcome { margin-top: 0.5rem; padding: 0.5rem; background: var(--bg); border-radius: 4px; }
    pre { margin: 0; white-space: pre-wrap; word-break: break-all; }
    .error { color: var(--err); }
    .live-section { border-left: 3px solid var(--accent); }
  </style>
</head>
<body>
  <h1>Experiment Dashboard</h1>
  <div id="root">Loading…</div>
  <script>
    function eventLine(ev) {
      var line = '<span class="event-type">' + (ev.event_type || '') + '</span> ';
      if (ev.agent_id) line += '<span class="agent">' + ev.agent_id + '</span> ';
      if (ev.event_type === 'message' && ev.data) line += (ev.data.content || '') + (ev.data.to_agent_ids && ev.data.to_agent_ids.length ? ' <span class="payload">→ ' + (ev.data.to_agent_ids || []).join(', ') + '</span>' : '');
      if (ev.event_type === 'action' && ev.data) line += (ev.data.action_type || '') + (ev.data.payload && Object.keys(ev.data.payload).length ? ' <span class="payload">' + JSON.stringify(ev.data.payload) + '</span>' : '') + (ev.data.ok === false ? ' <span class="error">FAILED</span>' : '');
      if (ev.event_type === 'match_end' && ev.data && ev.data.status) line += ev.data.status;
      return '<div class="event ' + (ev.event_type || '') + '">' + line + '</div>';
    }
    function render(data) {
      var cfg = data.config || {}, res = data.result || {}, status = data.status || 'finished';
      var matches = res.match_results || [], current = res.current_match;
      var html = '<section><h2>Status</h2><span class="badge ' + (status === 'running' ? 'badge-running' : 'badge-finished') + '">' + (status === 'running' ? 'Running…' : 'Finished') + '</span></section>';
      html += '<section><h2>Config</h2><pre>' + JSON.stringify({ game_id: cfg.game_id, num_matches: cfg.num_matches, max_turns_per_match: cfg.max_turns_per_match, max_messages_per_turn: cfg.max_messages_per_turn, log_directory: cfg.log_directory, metadata: cfg.metadata }, null, 2) + '</pre></section>';
      html += '<section><h2>Summary</h2><div class="summary"><span>Completion rate: <strong>' + (res.completion_rate != null ? (res.completion_rate * 100).toFixed(0) + '%' : '–') + '</strong></span><span>Total duration: <strong>' + (res.total_duration_seconds != null ? res.total_duration_seconds.toFixed(2) + 's' : '–') + '</strong></span>' + (res.mean_payoffs ? Object.entries(res.mean_payoffs).map(function(kv) { return '<span>' + kv[0] + ': <strong>' + (typeof kv[1] === 'number' ? kv[1].toFixed(2) : kv[1]) + '</strong></span>'; }).join('') : '') + '</div></section>';
      if (current && current.events && current.events.length >= 0) {
        html += '<section class="live-section"><h2>Current match (live)</h2><div class="match-body">';
        for (var j = 0; j < current.events.length; j++) html += eventLine(current.events[j]);
        html += '</div></section>';
      }
      html += '<section><h2>Matches</h2>';
      for (var i = 0; i < matches.length; i++) {
        var m = matches[i], log = m.log || {}, events = log.events || [], outcome = m.outcome || log.outcome;
        html += '<div class="match"><div class="match-header" data-i="' + i + '"><span>Match ' + (i + 1) + ': ' + (m.match_id || '').slice(0, 8) + '…</span><span>' + (m.status || '') + ' · ' + (m.num_turns || 0) + ' turns · ' + (m.duration_seconds != null ? m.duration_seconds.toFixed(2) + 's' : '') + (m.error ? ' · <span class="error">' + m.error + '</span>' : '') + '</span></div><div class="match-body" id="match-body-' + i + '" style="display:none">';
        for (var j = 0; j < events.length; j++) html += eventLine(events[j]);
        if (outcome && Object.keys(outcome).length) html += '<div class="outcome"><strong>Outcome</strong><pre>' + JSON.stringify(outcome, null, 2) + '</pre></div>';
        html += '</div></div>';
      }
      html += '</section>';
      return html;
    }
    var openMatches = {};
    function poll() {
      var root = document.getElementById('root');
      var prev = root.querySelectorAll('.match-body[id^="match-body-"]');
      for (var k = 0; k < prev.length; k++) {
        var el = prev[k], id = el.id, i = id.replace('match-body-', '');
        if (el.style.display !== 'none') openMatches[i] = true;
      }
      fetch('/api/result').then(function(r) { return r.json(); }).then(function(data) {
        root.innerHTML = render(data);
        document.querySelectorAll('.match-header').forEach(function(el) {
          el.onclick = function() { var b = document.getElementById('match-body-' + el.dataset.i); if (b) { b.style.display = b.style.display === 'none' ? 'block' : 'none'; openMatches[el.dataset.i] = b.style.display !== 'none'; } };
        });
        for (var i in openMatches) { if (openMatches[i]) { var b = document.getElementById('match-body-' + i); if (b) b.style.display = 'block'; } }
      }).catch(function(e) { root.textContent = 'Failed to load: ' + e.message; });
    }
    poll();
    setInterval(poll, 800);
  </script>
</body>
</html>
"""
