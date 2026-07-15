#!/usr/bin/env python3
"""backup-verify — prove your backups restore, on a schedule.

Reads a plan (YAML), fetches the latest backup, boots a scratch container,
loads the dump, runs smoke checks, tears everything down. Exit 0 = your
backup is real; anything else = you found out today, not during an incident.

  backup-verify run backup-verify.yaml
  backup-verify run backup-verify.yaml --keep     # leave scratch container up
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid

import yaml


class CheckFailure(Exception):
    pass


def run(args, **kwargs):
    """Run an argv list (no shell) and return trimmed stdout."""
    return subprocess.run(
        args,
        check=True,
        capture_output=True,  # nosec B603
        text=True,
        **kwargs,
    ).stdout.strip()


def docker(args):
    return run(["docker", *args])


def evaluate(check, output):
    """Apply expect/expect_min/expect_max to a check's output."""
    if "expect" in check and output != str(check["expect"]):
        raise CheckFailure(f"expected {check['expect']!r}, got {output!r}")
    value = None
    if "expect_min" in check or "expect_max" in check:
        try:
            value = float(output)
        except ValueError:
            raise CheckFailure(f"expected a number, got {output!r}")
    if "expect_min" in check and value < float(check["expect_min"]):
        raise CheckFailure(f"{value} < min {check['expect_min']}")
    if "expect_max" in check and value > float(check["expect_max"]):
        raise CheckFailure(f"{value} > max {check['expect_max']}")


def append_history(path, record):
    """Append one JSON-line record to the RTO history file (created if missing)."""
    with open(path, "a") as fh:
        fh.write(json.dumps(record) + "\n")


def run_plan(plan, keep=False, workdir=None):
    results = []
    name = f"backup-verify-{uuid.uuid4().hex[:8]}"
    restore = plan["restore"]
    start = time.time()

    workdir = workdir or tempfile.mkdtemp(prefix="backup-verify-")
    os.makedirs(workdir, exist_ok=True)
    print("backup-verify: fetching latest backup")
    # ponytail: fetch is an arbitrary shell pipeline from the trusted plan file,
    # so shell=True is intentional here (and only here).
    subprocess.run(plan["fetch"]["command"], shell=True, check=True)  # nosec B602  # nosemgrep: python.lang.security.audit.subprocess-shell-true.subprocess-shell-true

    env_args = []
    for k, v in restore.get("env", {}).items():
        env_args += ["-e", f"{k}={v}"]
    print(f"backup-verify: starting scratch container ({restore['image']})")
    docker(["run", "-d", "--name", name, "-v", f"{workdir}:/work", *env_args, restore["image"]])

    try:
        deadline = time.time() + int(restore.get("ready_timeout", 60))
        while True:
            try:
                docker(["exec", name, "sh", "-c", restore["ready_command"]])
                break
            except subprocess.CalledProcessError:
                if time.time() > deadline:
                    raise CheckFailure("scratch container never became ready")
                time.sleep(2)

        print("backup-verify: loading dump")
        docker(["exec", name, "sh", "-c", restore["load_command"]])

        for check in plan.get("checks", []):
            out = docker(["exec", name, "sh", "-c", check["command"]])
            try:
                evaluate(check, out)
                results.append({"name": check["name"], "status": "pass", "output": out})
                print(f"  ✓ {check['name']} ({out})")
            except CheckFailure as e:
                results.append({"name": check["name"], "status": "fail", "output": str(e)})
                print(f"  ✗ {check['name']}: {e}")
    finally:
        if not keep:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True)  # nosec B603 B607

    duration = time.time() - start
    failed = [r for r in results if r["status"] == "fail"]
    ok = not failed
    notify = plan.get("notify", {})
    if ok and (hb := notify.get("heartbeat_url")):
        subprocess.run(["curl", "-fsS", "-m", "10", "-o", "/dev/null", hb], check=False)  # nosec B603 B607
    if history_file := notify.get("history_file"):
        append_history(
            history_file,
            {"timestamp": time.time(), "duration_seconds": round(duration, 1), "ok": ok},
        )
    return results, ok, duration


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="backup-verify",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("plan")
    r.add_argument("--keep", action="store_true", help="keep the scratch container for inspection")
    r.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    with open(args.plan) as fh:
        plan = yaml.safe_load(fh)
    results, ok, duration = run_plan(plan, keep=args.keep)
    if args.json:
        json.dump({"ok": ok, "duration_seconds": round(duration, 1), "checks": results}, sys.stdout, indent=2)
    print(
        f"\nbackup-verify: {'PASS' if ok else 'FAIL'} "
        f"({sum(r['status'] == 'pass' for r in results)}/{len(results)} checks, {duration:.1f}s)"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
