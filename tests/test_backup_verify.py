import json

import pytest

from backup_verify import CheckFailure, append_history, build_run_args, evaluate


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
