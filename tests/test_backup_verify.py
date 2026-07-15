import json

import pytest

from backup_verify import CheckFailure, append_history, evaluate


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


def test_append_history_writes_one_json_line_per_call(tmp_path):
    path = tmp_path / "history.jsonl"
    append_history(path, {"duration_seconds": 12.3, "ok": True})
    append_history(path, {"duration_seconds": 9.8, "ok": False})
    lines = path.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"duration_seconds": 12.3, "ok": True}
    assert json.loads(lines[1])["ok"] is False
