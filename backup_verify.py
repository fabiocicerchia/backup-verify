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

# The workdir is bind-mounted here; a plan's load_command reads the dump at
# this path, so it is part of the plan contract (docs/plan-reference.md).
CONTAINER_WORKDIR = "/work"
DEFAULT_READY_TIMEOUT_SECONDS = 60
READY_POLL_INTERVAL_SECONDS = 2


class CheckFailure(Exception):
    pass


def run_captured(args, **kwargs):
    """Run an argv list (no shell) and return trimmed stdout."""
    return subprocess.run(
        args,
        check=True,
        capture_output=True,  # nosec B603
        text=True,
        **kwargs,
    ).stdout.strip()


def docker(args):
    return run_captured(["docker", *args])


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


def run_failure_hook(notify, status, failed_checks, error, duration):
    """Best-effort `notify.on_failure` shell command; symmetric with `fetch.command`.

    Fired when checks fail (status=fail) or the run blew up (status=error). Context
    is handed to the command via env vars. Like the heartbeat ping, this is strictly
    best-effort: a broken notifier must never mask the real failure or change the
    exit code, so anything it raises is swallowed here.
    """
    command = notify.get("on_failure")
    if not command:
        return
    env = {
        **os.environ,
        "BACKUP_VERIFY_STATUS": status,
        "BACKUP_VERIFY_FAILED_CHECKS": ",".join(failed_checks),
        "BACKUP_VERIFY_ERROR": error,
        "BACKUP_VERIFY_DURATION": f"{duration:.1f}",
    }
    try:
        # ponytail: on_failure is an arbitrary shell pipeline from the same trusted
        # plan file as fetch.command, so shell=True is intentional here too. check=False
        # keeps a failing notifier from ever changing the run's outcome.
        subprocess.run(command, shell=True, check=False, env=env)  # nosec B602  # nosemgrep: python.lang.security.audit.subprocess-shell-true.subprocess-shell-true
    except OSError as e:
        # A notifier that cannot even be spawned still must not change the
        # run's outcome — say so on stderr and carry on.
        print(f"backup-verify: could not run notify.on_failure: {e}", file=sys.stderr)


def build_fetch_command(fetch, workdir):
    """argv for a native fetcher (no shell), or None to fall back to `fetch.command`."""
    kind = fetch.get("type", "shell")
    if kind == "restic":
        argv = [
            "restic",
            "-r",
            fetch["repository"],
            "restore",
            fetch.get("snapshot", "latest"),
            "--target",
            fetch.get("target", workdir),
        ]
        if password_file := fetch.get("password_file"):
            argv += ["--password-file", password_file]
        return argv
    if kind == "pgbackrest":
        argv = [
            "pgbackrest",
            f"--stanza={fetch['stanza']}",
            f"--pg1-path={fetch.get('pg1_path', workdir)}",
            "restore",
        ]
        return argv + list(fetch.get("extra_args", []))
    return None


def build_run_args(name, workdir, restore, network):
    """docker-run argv (sans leading "docker") for the scratch container."""
    env_args = []
    for k, v in restore.get("env", {}).items():
        env_args += ["-e", f"{k}={v}"]
    limit_args = []
    if mem := restore.get("memory"):
        limit_args += ["--memory", str(mem)]
    if cpus := restore.get("cpus"):
        limit_args += ["--cpus", str(cpus)]
    return [
        "run",
        "-d",
        "--name",
        name,
        "--network",
        network,
        "-v",
        f"{workdir}:{CONTAINER_WORKDIR}",
        *env_args,
        *limit_args,
        restore["image"],
    ]


def run_plan(plan, keep=False, workdir=None):
    results = []
    name = f"backup-verify-{uuid.uuid4().hex[:8]}"
    network = f"{name}-net"
    restore = plan["restore"]
    notify = plan.get("notify", {})
    start = time.time()

    def append_run_history(ok, error=None):
        if history_file := notify.get("history_file"):
            record = {
                "timestamp": time.time(),
                "duration_seconds": round(time.time() - start, 1),
                "ok": ok,
            }
            if error is not None:
                record["error"] = error
            append_history(history_file, record)

    # Everything that can throw — fetch, container boot, readiness, load, checks —
    # lives inside this try so a failure is *recorded* (history + on_failure hook)
    # rather than swallowed or leaked. We re-raise afterwards so the CLI still exits
    # non-zero and run_plan() callers keep seeing the exception.
    try:
        workdir = workdir or tempfile.mkdtemp(prefix="backup-verify-")
        os.makedirs(workdir, exist_ok=True)
        print("backup-verify: fetching latest backup")
        fetch_argv = build_fetch_command(plan["fetch"], workdir)
        if fetch_argv:
            subprocess.run(fetch_argv, check=True)  # nosec B603
        else:
            # ponytail: fetch.command is an arbitrary shell pipeline from the trusted
            # plan file, so shell=True is intentional. notify.on_failure is the only
            # other place we do this, and for the same reason.
            subprocess.run(plan["fetch"]["command"], shell=True, check=True)  # nosec B602  # nosemgrep: python.lang.security.audit.subprocess-shell-true.subprocess-shell-true

        # Isolated (--internal, no external egress) network per run: the container
        # only needs to talk to itself over docker exec, and this keeps concurrent
        # runs from ever sharing a network namespace.
        docker(["network", "create", "--internal", network])
        print(f"backup-verify: starting scratch container ({restore['image']})")
        docker(build_run_args(name, workdir, restore, network))

        try:
            deadline = time.time() + int(
                restore.get("ready_timeout", DEFAULT_READY_TIMEOUT_SECONDS)
            )
            while True:
                try:
                    docker(["exec", name, "sh", "-c", restore["ready_command"]])
                    break
                except subprocess.CalledProcessError:
                    if time.time() > deadline:
                        raise CheckFailure("scratch container never became ready")
                    time.sleep(READY_POLL_INTERVAL_SECONDS)

            print("backup-verify: loading dump")
            docker(["exec", name, "sh", "-c", restore["load_command"]])

            for check in plan.get("checks", []):
                output = docker(["exec", name, "sh", "-c", check["command"]])
                try:
                    evaluate(check, output)
                    results.append({"name": check["name"], "status": "pass", "output": output})
                    print(f"  ✓ {check['name']} ({output})")
                except CheckFailure as e:
                    results.append({"name": check["name"], "status": "fail", "output": str(e)})
                    print(f"  ✗ {check['name']}: {e}")
        finally:
            if not keep:
                subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)  # nosec B603 B607
                subprocess.run(
                    ["docker", "network", "rm", network], capture_output=True, check=False
                )  # nosec B603 B607
    except Exception as e:
        duration = time.time() - start
        append_run_history(False, error=str(e))
        run_failure_hook(notify, "error", [], str(e), duration)
        raise

    duration = time.time() - start
    failed = [r for r in results if r["status"] == "fail"]
    ok = not failed
    if ok and (heartbeat_url := notify.get("heartbeat_url")):
        subprocess.run(["curl", "-fsS", "-m", "10", "-o", "/dev/null", heartbeat_url], check=False)  # nosec B603 B607
    if not ok:
        run_failure_hook(notify, "fail", [r["name"] for r in failed], "", duration)
    append_run_history(ok)
    return results, ok, duration


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="backup-verify",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subcommands = parser.add_subparsers(dest="cmd", required=True)
    run_cmd = subcommands.add_parser("run")
    run_cmd.add_argument("plan")
    run_cmd.add_argument(
        "--keep", action="store_true", help="keep the scratch container for inspection"
    )
    run_cmd.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    with open(args.plan) as fh:
        plan = yaml.safe_load(fh)
    results, ok, duration = run_plan(plan, keep=args.keep)
    if args.json:
        json.dump(
            {"ok": ok, "duration_seconds": round(duration, 1), "checks": results},
            sys.stdout,
            indent=2,
        )
    print(
        f"\nbackup-verify: {'PASS' if ok else 'FAIL'} "
        f"({sum(r['status'] == 'pass' for r in results)}/{len(results)} checks, {duration:.1f}s)"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
