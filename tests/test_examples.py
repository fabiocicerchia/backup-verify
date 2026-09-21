from pathlib import Path

import yaml


def test_example_plans_are_well_formed() -> None:
    paths = sorted(Path("examples").glob("*.yaml"))
    assert paths, "no example plans found"
    for path in paths:
        plan = yaml.safe_load(path.read_text())
        assert "fetch" in plan
        assert "restore" in plan
        assert "load_command" in plan["restore"]
        assert plan.get("checks"), f"{path}: expected at least one check"
        # A container needs something to wait for; restoring in place has
        # nothing booting, so `ready_command` is only required alongside an image.
        if "image" in plan["restore"]:
            assert "ready_command" in plan["restore"], f"{path}: an image wants a ready_command"
