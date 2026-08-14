import json
import subprocess

import pytest

import backup_verify
from backup_verify import (
    CheckFailure,
    append_history,
    build_fetch_command,
    build_run_args,
    evaluate,
    run_plan,
)


def test_exact_expectation():
    evaluate({"expect": "3"}, "3")
    with pytest.raises(CheckFailure):
        evaluate({"expect": "3"}, "2")


def test_min_max_bounds():
    evaluate({"expect_min": 1000}, "1500")
    evaluate({"expect_max": 48}, "12.5")
    with pytest.raises(CheckFailure):
        evaluate({"expect_min": 1000}, "999")
    with pytest.raises(CheckFailure):
        evaluate({"expect_max": 48}, "72")


def test_non_numeric_output_for_numeric_check():
    with pytest.raises(CheckFailure, match="expected a number"):
        evaluate({"expect_min": 1}, "ERROR: relation does not exist")


def test_build_fetch_command_defaults_to_shell_fallback():
    assert build_fetch_command({"command": "cp x y"}, "/work") is None


def test_build_fetch_command_restic():
    fetch = {
        "type": "restic",
        "repository": "s3:s3.amazonaws.com/bucket",
        "snapshot": "abc123",
    }
    argv = build_fetch_command(fetch, "/work")
    assert argv == [
        "restic",
        "-r",
        "s3:s3.amazonaws.com/bucket",
        "restore",
        "abc123",
        "--target",
        "/work",
    ]


def test_build_fetch_command_pgbackrest():
    fetch = {"type": "pgbackrest", "stanza": "main", "extra_args": ["--delta"]}
    argv = build_fetch_command(fetch, "/work")
    assert argv == [
        "pgbackrest",
        "--stanza=main",
        "--pg1-path=/work",
        "restore",
        "--delta",
    ]


def test_build_run_args_attaches_network_and_no_limits_by_default():
    args = build_run_args("bv-1", "/work", {"image": "postgres:16-alpine"}, "bv-1-net")
    assert "--network" in args and args[args.index("--network") + 1] == "bv-1-net"
    assert "--memory" not in args
    assert "--cpus" not in args
    assert args[-1] == "postgres:16-alpine"


def test_build_run_args_applies_resource_limits():
    restore = {"image": "postgres:16-alpine", "memory": "512m", "cpus": "1.5"}
    args = build_run_args("bv-1", "/work", restore, "bv-1-net")
    assert args[args.index("--memory") + 1] == "512m"
    assert args[args.index("--cpus") + 1] == "1.5"


def test_append_history_writes_one_json_line_per_call(tmp_path):
    path = tmp_path / "history.jsonl"
    append_history(path, {"duration_seconds": 12.3, "ok": True})
    append_history(path, {"duration_seconds": 9.8, "ok": False})
    lines = path.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"duration_seconds": 12.3, "ok": True}
    assert json.loads(lines[1])["ok"] is False


# --- run_plan failure reporting -------------------------------------------
#
# run_plan shells out constantly (fetch, docker, curl), so these tests replace
# subprocess.run with a fake that returns canned output and records every call.
# Shell pipelines (fetch.command, notify.on_failure) arrive as a bare string;
# docker/curl argv arrive as a list — that split is how the fake tells them apart.


class FakeProc:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.returncode = returncode


def make_fake_run(calls, *, fetch_fails=False, check_output="1"):
    def fake_run(args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        if isinstance(args, str):
            if "FETCH_CMD" in args:
                if fetch_fails:
                    raise subprocess.CalledProcessError(1, args)
                return FakeProc()
            if "ON_FAILURE_CMD" in args:
                # A notifier that exits non-zero: under check=True subprocess would
                # raise, so this asserts run_plan invokes on_failure with check=False.
                if kwargs.get("check"):
                    raise subprocess.CalledProcessError(3, args)
                return FakeProc(returncode=3)
            return FakeProc()
        # docker/curl argv; only the check command carries a real output.
        if "CHECK_CMD" in " ".join(str(a) for a in args):
            return FakeProc(stdout=check_output)
        return FakeProc()

    return fake_run


def make_plan(checks, notify):
    return {
        "fetch": {"command": "FETCH_CMD"},
        "restore": {
            "image": "postgres:16-alpine",
            "ready_command": "READY",
            "load_command": "LOAD",
        },
        "checks": checks,
        "notify": notify,
    }


def on_failure_calls(calls):
    return [c for c in calls if isinstance(c["args"], str) and "ON_FAILURE_CMD" in c["args"]]


def test_fetch_failure_records_history_and_runs_on_failure(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(backup_verify.subprocess, "run", make_fake_run(calls, fetch_fails=True))
    history = tmp_path / "history.jsonl"
    plan = make_plan([], {"history_file": str(history), "on_failure": "ON_FAILURE_CMD"})

    with pytest.raises(subprocess.CalledProcessError):
        run_plan(plan, workdir=str(tmp_path / "work"))

    row = json.loads(history.read_text().splitlines()[-1])
    assert row["ok"] is False
    assert row["error"]  # exception string recorded, not swallowed

    hook = on_failure_calls(calls)
    assert len(hook) == 1
    env = hook[0]["kwargs"]["env"]
    assert env["BACKUP_VERIFY_STATUS"] == "error"
    assert env["BACKUP_VERIFY_ERROR"]
    assert env["BACKUP_VERIFY_FAILED_CHECKS"] == ""


def test_failed_check_runs_on_failure_with_check_name(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(backup_verify.subprocess, "run", make_fake_run(calls, check_output="5"))
    plan = make_plan(
        [{"name": "row count", "command": "CHECK_CMD", "expect": "2"}],
        {"on_failure": "ON_FAILURE_CMD"},
    )

    _results, ok, _ = run_plan(plan, workdir=str(tmp_path / "work"))

    assert ok is False
    hook = on_failure_calls(calls)
    assert len(hook) == 1
    env = hook[0]["kwargs"]["env"]
    assert env["BACKUP_VERIFY_STATUS"] == "fail"
    assert env["BACKUP_VERIFY_FAILED_CHECKS"] == "row count"
    assert env["BACKUP_VERIFY_ERROR"] == ""


def test_success_pings_heartbeat_and_skips_on_failure(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(backup_verify.subprocess, "run", make_fake_run(calls, check_output="2"))
    plan = make_plan(
        [{"name": "row count", "command": "CHECK_CMD", "expect": "2"}],
        {"heartbeat_url": "https://hc-ping.com/x", "on_failure": "ON_FAILURE_CMD"},
    )

    _, ok, _ = run_plan(plan, workdir=str(tmp_path / "work"))

    assert ok is True
    heartbeats = [c for c in calls if isinstance(c["args"], list) and c["args"][0] == "curl"]
    assert len(heartbeats) == 1
    assert on_failure_calls(calls) == []


def test_on_failure_nonzero_exit_does_not_change_outcome(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(backup_verify.subprocess, "run", make_fake_run(calls, check_output="5"))
    plan = make_plan(
        [{"name": "row count", "command": "CHECK_CMD", "expect": "2"}],
        {"on_failure": "ON_FAILURE_CMD"},
    )

    results, ok, _ = run_plan(plan, workdir=str(tmp_path / "work"))

    assert ok is False
    assert results[0]["status"] == "fail"
    assert len(on_failure_calls(calls)) == 1
