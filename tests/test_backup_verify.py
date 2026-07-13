import pytest

from backup_verify import CheckFailure, evaluate


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
