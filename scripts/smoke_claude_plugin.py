#!/usr/bin/env python3
"""Start a built Articulate Writing plugin's MCP server the way Claude Code does,
and check what it answers.

    python3 scripts/smoke_claude_plugin.py PLUGIN_DIR [--command python3]

Reads PLUGIN_DIR/.mcp.json, puts PLUGIN_DIR in place of ${CLAUDE_PLUGIN_ROOT},
adds the declared env to this environment, starts the declared command, and
exchanges initialize, tools/list, ping, UTF-8 checks, an explicit hosted-backend
refusal, doctor, and a host edit plan followed by accepted and refused submissions. It prints one line per check
and exits 1 when any check fails. --command replaces the interpreter, for a
machine where the one to test has another name. Without it, the declared command
is looked up on absolute PATH entries outside the working folder and the plugin
folder, so a file named python3 in either never runs.

Run it on each operating system the plugin supports. It needs only the Python
standard library, and the server it starts sends nothing over the network.
"""
import argparse
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from find_program import find_program  # noqa: E402  (the path is set just above)

LOCAL_TOOLS = {"check", "score", "edit_plan", "edit_submit", "judge", "fix",
               "polish", "articulate.status", "articulate.doctor"}
ORIGINAL = "We leverage 42 samples. See [the report](https://example.org/report)."
GOOD_REWRITE = "We use 42 samples. See [the report](https://example.org/report)."
BAD_REWRITE = "We use 43 samples."
# A quoted marketing line: 0.5.1 flags its patterns and must preserve the curly
# quotes and exact match offsets when it decodes UTF-8 input.
QUOTED = ("The brochure promised “By leveraging cutting-edge technology, we "
          "transform your workflow.” We doubted it.")
ACCENTED = "Our résumé service is cutting-edge."


def launch_spec(plugin_dir, command=None, drop=(), extra_env=None):
    """The argv and env Claude Code would use for the plugin's one server."""
    cfg = json.loads((plugin_dir / ".mcp.json").read_text(encoding="utf-8"))
    (entry,) = cfg["mcpServers"].values()
    root = plugin_dir.as_posix()
    args = [a.replace("${CLAUDE_PLUGIN_ROOT}", root) for a in entry["args"]]
    for flag in drop:
        at = args.index(flag)
        del args[at:at + (2 if flag == "-X" else 1)]
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=root, **entry.get("env", {}))
    env.update(extra_env or {})
    if command is None:
        command = find_program(entry["command"], avoid=[Path.cwd(), plugin_dir])
        if command is None:
            raise SystemExit(f"{entry['command']} was not found on an absolute PATH "
                             "entry outside the working folder; pass --command")
    return [command] + args, env


def _requests():
    def call(rid, name, arguments):
        return {"jsonrpc": "2.0", "id": rid, "method": "tools/call",
                "params": {"name": name, "arguments": arguments}}
    return [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                    "clientInfo": {"name": "smoke", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "ping"},
        call(4, "check", {"text": QUOTED}),
        call(5, "check", {"text": ACCENTED}),
        call(6, "fix", {"text": "A short passage.", "backend": "anthropic"}),
        call(7, "articulate.doctor", {}),
        call(8, "edit_plan", {"text": ORIGINAL}),
    ]


def exchange(argv, env, timeout=60, transcript=None):
    """Exercise a host edit in one server session, including a refused rewrite."""
    answers = {}
    events = transcript if transcript is not None else []
    incoming, errors = queue.Queue(), []
    with subprocess.Popen(argv, env=env, stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
        def read_output():
            for line in proc.stdout:
                incoming.put(line)
            incoming.put(None)

        def read_errors():
            errors.append(proc.stderr.read())

        reader = threading.Thread(target=read_output, daemon=True)
        err_reader = threading.Thread(target=read_errors, daemon=True)
        reader.start()
        err_reader.start()

        def send(request):
            events.append({"direction": "request", "message": request})
            proc.stdin.write((json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8"))
            proc.stdin.flush()

        def receive():
            line = incoming.get(timeout=timeout)
            if line is None:
                return False
            message = json.loads(line.decode("utf-8"))
            events.append({"direction": "response", "message": message})
            answers[message.get("id")] = message
            return True

        try:
            for request in _requests():
                send(request)
            while len(answers) < 8 and receive():
                pass
            if 8 in answers and "result" in answers[8]:
                plan = _payload(answers[8])
                if plan.get("plan_id"):
                    for rid, rewrite in ((9, GOOD_REWRITE), (10, BAD_REWRITE)):
                        send({"jsonrpc": "2.0", "id": rid, "method": "tools/call",
                              "params": {"name": "edit_submit", "arguments": {
                                  "text": ORIGINAL, "rewrite": rewrite,
                                  "plan_id": plan["plan_id"]}}})
                        if not receive():
                            break
            proc.stdin.close()
            code = proc.wait(timeout=timeout)
        except (queue.Empty, subprocess.TimeoutExpired):
            proc.kill()
            proc.wait()
            raise RuntimeError("plugin smoke timed out") from None
        except BrokenPipeError:
            code = proc.wait(timeout=timeout)
        finally:
            err_reader.join(timeout=timeout)
    return answers, code, b"".join(errors).decode("utf-8", "replace")


def _payload(answer):
    return json.loads(answer["result"]["content"][0]["text"])


def evaluate(answers, code, version):
    """(check, passed, detail) for each thing the plugin promises at launch."""
    missing = [rid for rid in range(1, 11) if "result" not in answers.get(rid, {})]
    if missing:
        return [("the server answered every request", False,
                 f"exit {code}; no result for request ids {missing}")]
    tools = answers[2]["result"]["tools"]
    names = [t["name"] for t in tools]
    quoted, accented = _payload(answers[4]), _payload(answers[5])
    fix, doctor = answers[6]["result"], _payload(answers[7])
    plan, good, bad = (_payload(answers[rid]) for rid in (8, 9, 10))
    snippets = " ".join(h["snippet"] for h in accented["hits"])
    return [
        ("the server exits 0 when stdin closes", code == 0, f"exit {code}"),
        ("initialize names the bundled version",
         answers[1]["result"]["serverInfo"] == {"name": "articulate", "version": version},
         json.dumps(answers[1]["result"]["serverInfo"])),
        ("tools/list holds the offline tool set", set(names) == LOCAL_TOOLS,
         ", ".join(names)),
        ("every tool has a title and four hints", all(
            t.get("title") and all(type(t["annotations"].get(h)) is bool for h in (
                "readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint"))
            for t in tools), f"{len(tools)} tools"),
        ("ping answers an empty result", answers[3].get("result") == {}, "{}"),
        ("curly quotes and match offsets survive UTF-8 input", bool(quoted["hits"]) and all(
            "“" in h["snippet"] and "”" in h["snippet"]
            and QUOTED[h["start"]:h["end"]] == h["match"] for h in quoted["hits"]),
         f"{len(quoted['hits'])} hits"),
        ("accented text round-trips", "résumé" in snippets, snippets[:60]),
        ("a hosted tool refuses by name", fix.get("isError") is True,
         fix["content"][0]["text"][:70]),
        ("doctor reports the local tool set",
         doctor.get("tool_set") == "local" and doctor.get("local_only_switch") is True,
         f"python {doctor.get('python')}, tool_set {doctor.get('tool_set')}"),
        ("host plan works with local-only on", plan.get("status") == "host_edit_required",
         str(plan.get("backend"))),
        ("good rewrite passes with a host receipt",
         good.get("text") == GOOD_REWRITE and good.get("gate") == "ok"
         and good.get("refused") == [] and good.get("receipt", {}).get("backend") == "host",
         f"gate {good.get('gate')}, receipt backend {good.get('receipt', {}).get('backend')}"),
        ("changed number and dropped link are refused",
         bad.get("text") == ORIGINAL and bool(bad.get("refused")),
         json.dumps(bad.get("refused"))),
    ]


def smoke(plugin_dir, command=None, drop=(), extra_env=None, transcript=None):
    plugin_dir = Path(plugin_dir).resolve()
    version = json.loads((plugin_dir / ".claude-plugin" / "plugin.json")
                         .read_text(encoding="utf-8"))["version"]
    argv, env = launch_spec(plugin_dir, command, drop, extra_env)
    answers, code, stderr = exchange(argv, env, transcript=transcript)
    results = evaluate(answers, code, version)
    caches = [p.relative_to(plugin_dir).as_posix() for p in plugin_dir.rglob("__pycache__")]
    results.append(("no bytecode written in the plugin folder", not caches,
                    ", ".join(caches) or "none"))
    return results, stderr


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("plugin_dir")
    parser.add_argument("--command", help="interpreter to start in place of the declared one")
    parser.add_argument("--transcript", help="write the synthetic request/response transcript as JSON")
    args = parser.parse_args(argv)
    transcript = []
    results, stderr = smoke(args.plugin_dir, args.command, transcript=transcript)
    if args.transcript:
        Path(args.transcript).write_text(json.dumps(transcript, indent=2, ensure_ascii=False) + "\n",
                                         encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"{sys.platform}, runner Python {sys.version.split()[0]}")
    for check, passed, detail in results:
        print(f"{'PASS' if passed else 'FAIL'}  {check}  ({detail})")
    if stderr.strip():
        print("server stderr:\n" + stderr.strip())
    return 0 if all(passed for _check, passed, _detail in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
