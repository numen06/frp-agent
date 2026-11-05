"""Incrementally count native SSH gateway logs; never retain log contents or credentials.

Run on the Docker host (Python 3.6+) every minute. Does not attach to or restart a gateway.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time

AUTH = re.compile(r" - paramiko\.transport - INFO - Auth (rejected|granted) \((password|publickey)\)\.$")


def consume(lines, state):
    counts = Counter(state.get("counts", {}))
    cursor, skip = state.get("cursor", ""), state.get("cursor_lines", 0)
    same = 0
    last, last_count = cursor, skip
    for line in lines:
        at, sep, message = line.rstrip("\r\n").partition(" ")
        if not sep or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T[0-9:.]+Z", at):
            continue
        if not state.get("first_log_at"):
            state["first_log_at"] = at
        if at < cursor:
            continue
        if at == cursor:
            same += 1
            if same <= skip:
                continue
        if at == last:
            last_count += 1
        else:
            last, last_count = at, 1
        match = AUTH.search(message)
        if match:
            outcome, method = match.groups()
            counts["auth_failures" if outcome == "rejected" else "auth_successes"] += 1
            if outcome == "rejected":
                counts[method + "_failures"] += 1
        elif " - app.services.ssh_gateway_service - WARNING - SSH 网关临时封禁来源 " in message:
            counts["bans"] += 1
        elif " - app.services.ssh_gateway_service - WARNING - SSH 网关连接失败 (" in message:
            counts["connection_errors"] += 1
    state.update(cursor=last, cursor_lines=last_count, counts=dict(counts))
    return state


def collect(container, output):
    import fcntl
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(str(output)+".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        info = json.loads(subprocess.check_output(["docker", "inspect", container], timeout=10))[0]
        if not info["State"]["Running"]:
            raise RuntimeError("SSH gateway container is not running")
        identity = info["Id"] + ":" + info["State"]["StartedAt"]
        state = json.loads(output.read_text()) if output.exists() else {}
        if state.get("identity") != identity:
            state = dict(version=1, identity=identity, started_at=info["State"]["StartedAt"], counts={})
        until = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        process = subprocess.Popen(["docker", "logs", "--timestamps", "--since", state.get("cursor") or state["started_at"], "--until", until, container],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding="utf-8", errors="replace")
        timer = threading.Timer(45, process.kill)
        timer.start()
        try:
            consume(process.stdout, state)
            if process.wait() != 0:
                raise RuntimeError("SSH log collection failed; previous counters retained")
        finally:
            timer.cancel()
            process.stdout.close()
            if process.poll() is None:
                process.kill()
                process.wait()
        state["collected_at"] = time.time()
        temporary = str(output) + ".next"
        fd = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(state, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, str(output))
        return {key: state[key] for key in ["version", "collected_at", "started_at", "first_log_at", "counts"] if key in state}


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--container",default="tools-frp-agent-1")
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    print(json.dumps(collect(args.container,args.output)))
