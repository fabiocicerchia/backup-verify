import glob

import yaml


def test_example_plans_are_well_formed():
    paths = glob.glob("examples/*.yaml")
    assert paths, "no example plans found"
    for path in paths:
        with open(path) as fh:
            plan = yaml.safe_load(fh)
        assert "fetch" in plan
        assert "restore" in plan
        assert "image" in plan["restore"]
        assert "ready_command" in plan["restore"]
        assert "load_command" in plan["restore"]
        assert plan.get("checks"), f"{path}: expected at least one check"
