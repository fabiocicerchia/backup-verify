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
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any

import yaml

# The plan file, as PyYAML hands it over: a `fetch` block, a `restore` block, a
# list of `checks`, and an optional `notify`. Deliberately not modelled further
# -- the plan is the user's document, and every reader here uses .get.
Plan = dict[str, Any]
# One check's result: {name, ok, output, error}.
Result = dict[str, Any]

# The workdir is bind-mounted here; a plan's load_command reads the dump at
# this path, so it is part of the plan contract (docs/plan-reference.md).
CONTAINER_WORKDIR = "/work"
HEARTBEAT_TIMEOUT_SECONDS = 10
DEFAULT_READY_TIMEOUT_SECONDS = 60
READY_POLL_INTERVAL_SECONDS = 2

# sysexits(3). 0/1 are the verdict the README documents; the rest say what went
# wrong with the plan, so a bad plan is an error message and not a traceback.
EXIT_OK = 0
EXIT_CHECKS_FAILED = 1
EXIT_DATAERR = 65
EXIT_NOINPUT = 66

# Diagnostics go here; the run's own report stays on stdout.
logger = logging.getLogger("backup-verify")


class CheckFailedError(Exception):
    pass


def run_captured(args: list[str], **kwargs: object) -> str:
    """Run an argv list (no shell) and return trimmed stdout."""
    # argv is a list built by the caller, never a string, and no shell is
    # involved.
    return subprocess.run(  # noqa: S603
        args,
        check=True,
        capture_output=True,
        text=True,
        **kwargs,
    ).stdout.strip()


def _docker_quietly(args: list[str]) -> None:
    """Teardown docker call: never raises, never speaks. A failure to clean up
    must not mask the result of the run that produced it."""
    binary = shutil.which("docker")
    if binary is None:
        return
    subprocess.run([binary, *args], capture_output=True, check=False)  # noqa: S603 — resolved binary, fixed argv


def _ping_heartbeat(url: str) -> None:
    """Best-effort GET of a dead-man's-switch URL. Was a shell-out to curl,
    which meant a machine without curl silently stopped reporting success."""
    if not url.startswith(("http://", "https://")):
        logger.warning("notify.heartbeat_url is not an http(s) URL, skipping")
        return
    try:
        with urllib.request.urlopen(url, timeout=HEARTBEAT_TIMEOUT_SECONDS):  # noqa: S310 — scheme checked above
            pass
    except OSError as err:
        logger.warning("heartbeat ping failed: %s", err)


def docker(args: list[str]) -> str:
    """Run a docker subcommand. Resolved through PATH once, here, rather than
    leaving each call to whatever `docker` the environment turns up."""
    binary = shutil.which("docker")
    if binary is None:
        msg = "docker is not on PATH"
        raise RuntimeError(msg)
    return run_captured([binary, *args])


def evaluate(check: Plan, output: str) -> None:
    """Apply expect/expect_min/expect_max to a check's output."""
    if "expect" in check and output != str(check["expect"]):
        raise CheckFailedError(f"expected {check['expect']!r}, got {output!r}")
    value = None
    if "expect_min" in check or "expect_max" in check:
        try:
            value = float(output)
        except ValueError as err:
            msg = f"expected a number, got {output!r}"
            raise CheckFailedError(msg) from err
    if "expect_min" in check and value < float(check["expect_min"]):
        raise CheckFailedError(f"{value} < min {check['expect_min']}")
    if "expect_max" in check and value > float(check["expect_max"]):
        raise CheckFailedError(f"{value} > max {check['expect_max']}")


def append_history(path: str, record: dict[str, Any]) -> None:
    """Append one JSON-line record to the RTO history file (created if missing)."""
    with Path(path).open("a") as fh:
        fh.write(json.dumps(record) + "\n")


def append_run_history(notify: Plan, start: float, ok: bool, error: str | None = None) -> None:
    """Append this run's outcome to `notify.history_file`, when the plan asks for one."""
    history_file = notify.get("history_file")
    if not history_file:
        return
    record = {
        "timestamp": time.time(),
        "duration_seconds": round(time.time() - start, 1),
        "ok": ok,
    }
    if error is not None:
        record["error"] = error
    append_history(history_file, record)


def run_failure_hook(notify: Plan, status: str, failed_checks: list[str], error: str | None, duration: float) -> None:
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
        subprocess.run(  # noqa: S602 — see the comment above
            command, shell=True, check=False, env=env
        )
    except OSError as e:
        # A notifier that cannot even be spawned still must not change the
        # run's outcome — say so and carry on.
        logger.warning("could not run notify.on_failure: %s", e)


def restic_argv(fetch: Plan, workdir: str) -> list[str]:
    """argv for `fetch.type: restic`."""
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


def pgbackrest_argv(fetch: Plan, workdir: str) -> list[str]:
    """argv for `fetch.type: pgbackrest`."""
    argv = [
        "pgbackrest",
        f"--stanza={fetch['stanza']}",
        f"--pg1-path={fetch.get('pg1_path', workdir)}",
        "restore",
    ]
    return argv + list(fetch.get("extra_args", []))


# A new native fetcher is a function plus a row here, not another branch.
FETCHERS = {"restic": restic_argv, "pgbackrest": pgbackrest_argv}


def build_fetch_command(fetch: Plan, workdir: str) -> list[str] | None:
    """argv for a native fetcher (no shell), or None to fall back to `fetch.command`."""
    build_argv = FETCHERS.get(fetch.get("type", "shell"))
    return build_argv(fetch, workdir) if build_argv else None


def build_run_args(name: str, workdir: str, restore: Plan, network: str) -> list[str]:
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


def fetch_backup(fetch: Plan, workdir: str) -> None:
    """Pull the latest backup into workdir, natively or through `fetch.command`."""
    print("backup-verify: fetching latest backup")  # noqa: T201 — run progress, on stdout
    fetch_argv = build_fetch_command(fetch, workdir)
    if fetch_argv:
        # argv built by build_fetch_command from the plan's own fields.
        subprocess.run(fetch_argv, check=True)  # noqa: S603
        return
    # ponytail: fetch.command is an arbitrary shell pipeline from the trusted
    # plan file, so shell=True is intentional. notify.on_failure is the only
    # other place we do this, and for the same reason.
    subprocess.run(fetch["command"], shell=True, check=True)  # noqa: S602 — see the comment above.subprocess-shell-true


def wait_until_ready(name: str, restore: Plan) -> None:
    """Poll `restore.ready_command` until it exits 0, or give up at ready_timeout."""
    deadline = time.time() + int(restore.get("ready_timeout", DEFAULT_READY_TIMEOUT_SECONDS))
    while True:
        try:
            docker(["exec", name, "sh", "-c", restore["ready_command"]])
        except subprocess.CalledProcessError as err:
            if time.time() > deadline:
                msg = "scratch container never became ready"
                raise CheckFailedError(msg) from err
            time.sleep(READY_POLL_INTERVAL_SECONDS)
        else:
            return


def run_checks(name: str, checks: list[Plan]) -> list[Result]:
    """Run every smoke check inside the scratch container; one result record each."""
    results = []
    for check in checks:
        output = docker(["exec", name, "sh", "-c", check["command"]])
        try:
            evaluate(check, output)
            results.append({"name": check["name"], "status": "pass", "output": output})
            print(f"  ✓ {check['name']} ({output})")  # noqa: T201 — run progress, on stdout
        except CheckFailedError as e:
            results.append({"name": check["name"], "status": "fail", "output": str(e)})
            print(f"  ✗ {check['name']}: {e}")  # noqa: T201 — run progress, on stdout
    return results


def run_plan(plan: Plan, keep: bool = False, workdir: str | None = None) -> tuple[list[Result], bool, float]:
    results = []
    name = f"backup-verify-{uuid.uuid4().hex[:8]}"
    network = f"{name}-net"
    restore = plan["restore"]
    notify = plan.get("notify", {})
    start = time.time()

    # Everything that can throw — fetch, container boot, readiness, load, checks —
    # lives inside this try so a failure is *recorded* (history + on_failure hook)
    # rather than swallowed or leaked. We re-raise afterwards so the CLI still exits
    # non-zero and run_plan() callers keep seeing the exception.
    try:
        workdir = workdir or tempfile.mkdtemp(prefix="backup-verify-")
        Path(workdir).mkdir(parents=True, exist_ok=True)
        fetch_backup(plan["fetch"], workdir)

        # Isolated (--internal, no external egress) network per run: the container
        # only needs to talk to itself over docker exec, and this keeps concurrent
        # runs from ever sharing a network namespace.
        docker(["network", "create", "--internal", network])
        print(f"backup-verify: starting scratch container ({restore['image']})")  # noqa: T201 — run progress, on stdout
        docker(build_run_args(name, workdir, restore, network))

        try:
            wait_until_ready(name, restore)
            print("backup-verify: loading dump")  # noqa: T201 — run progress, on stdout
            docker(["exec", name, "sh", "-c", restore["load_command"]])
            results = run_checks(name, plan.get("checks", []))
        finally:
            if not keep:
                # Best-effort teardown: a failure here must not mask the run's
                # own result, hence check=False.
                _docker_quietly(["rm", "-f", name])
                _docker_quietly(["network", "rm", network])
    except Exception as e:
        duration = time.time() - start
        append_run_history(notify, start, False, error=str(e))
        run_failure_hook(notify, "error", [], str(e), duration)
        raise

    duration = time.time() - start
    failed = [r for r in results if r["status"] == "fail"]
    ok = not failed
    if ok and (heartbeat_url := notify.get("heartbeat_url")):
        _ping_heartbeat(heartbeat_url)
    if not ok:
        run_failure_hook(notify, "fail", [r["name"] for r in failed], "", duration)
    append_run_history(notify, start, ok)
    return results, ok, duration


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(format="backup-verify: %(message)s", stream=sys.stderr, level=logging.INFO)
    parser = argparse.ArgumentParser(
        prog="backup-verify",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subcommands = parser.add_subparsers(dest="cmd", required=True)
    run_cmd = subcommands.add_parser("run")
    run_cmd.add_argument("plan")
    run_cmd.add_argument("--keep", action="store_true", help="keep the scratch container for inspection")
    run_cmd.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        plan = yaml.safe_load(Path(args.plan).read_text())
    except OSError:
        logger.exception("cannot read plan %s", args.plan)
        return EXIT_NOINPUT
    except yaml.YAMLError:
        logger.exception("plan %s is not valid YAML", args.plan)
        return EXIT_DATAERR

    results, ok, duration = run_plan(plan, keep=args.keep)
    if args.json:
        json.dump(
            {"ok": ok, "duration_seconds": round(duration, 1), "checks": results},
            sys.stdout,
            indent=2,
        )
    print(  # noqa: T201 — run progress, on stdout
        f"\nbackup-verify: {'PASS' if ok else 'FAIL'} "
        f"({sum(r['status'] == 'pass' for r in results)}/{len(results)} checks, {duration:.1f}s)"
    )
    return EXIT_OK if ok else EXIT_CHECKS_FAILED


if __name__ == "__main__":
    sys.exit(main())
