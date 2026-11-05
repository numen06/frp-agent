"""Log counting must exclude discovery, upstream client failures and replayed lines."""
import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location("collector",Path(__file__).parents[1]/"scripts/collect_ssh_metrics.py")
collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)


def test_server_auth_only_and_incremental_cursor():
    at="2026-11-03T00:00:00.123456789Z"
    lines=[at+" 2026-11-03 - paramiko.transport - INFO - Auth rejected (none).\n",
        at+" 2026-11-03 - paramiko.transport - INFO - Auth rejected (password).\n",
        at+" 2026-11-03 - paramiko.transport - INFO - Auth rejected (publickey).\n",
        at+" 2026-11-03 - paramiko.transport - INFO - Auth granted (password).\n",
        at+" 2026-11-03 - paramiko.transport - INFO - Authentication (password) failed.\n"]
    state=collector.consume(lines,{})
    assert state["counts"]==dict(auth_failures=2,password_failures=1,publickey_failures=1,auth_successes=1)
    assert state["cursor_lines"]==5
    assert collector.consume(lines,state)["counts"]["auth_failures"]==2
    extended=lines+[at+" 2026-11-03 - paramiko.transport - INFO - Auth rejected (password).\n"]
    state=collector.consume(extended,state)
    assert state["counts"]["auth_failures"]==3 and state["cursor_lines"]==6
    assert collector.consume(extended,state)["counts"]["auth_failures"]==3
    later="2026-11-03T00:00:01.000000000Z"
    state=collector.consume([extended[-1],later+" normal message\n"],state)
    assert state["cursor"]==later and state["cursor_lines"]==1 and state["counts"]["auth_failures"]==3
