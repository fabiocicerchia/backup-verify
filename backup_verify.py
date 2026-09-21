#!/usr/bin/env python3
"""backup-verify — prove your backups restore, on a schedule.

Reads a plan (YAML), fetches the latest backup, boots a scratch container,
loads the dump, runs smoke checks, tears everything down. Exit 0 = your
backup is real; anything else = you found out today, not during an incident.

Omit `restore.image` and the loading and the checks happen right here instead,
for when whatever is running this is already the scratch environment — a
Kubernetes CronJob pod, a throwaway VM. Same plan, same checks, no Docker.

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
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

# The plan file, as PyYAML hands it over: a `fetch` block, a `restore` block, a
# list of `checks`, and an optional `notify`. Deliberately not modelled further
# -- the plan is the user's document, and every reader here uses .get.
Plan = dict[str, Any]
# One check's result: {name, ok, output, error}.
Result = dict[str, Any]
# Runs one of the plan's shell commands and returns its trimmed stdout. The one
# thing that differs between a scratch container and restoring in place, which
# is why it is the only thing the restore and check stages are handed.
Shell = Callable[[str], str]

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


def run_captured(args: list[str], **kwargs: Any) -> str:
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
    if "expect_min" not in check and "expect_max" not in check:
        return
    try:
        value = float(output)
    except ValueError as err:
        msg = f"expected a number, got {output!r}"
        raise CheckFailedError(msg) from err
    # Inside the branch that parsed it: the bounds are only comparable once
    # there is a number, and the two `if`s below were reachable without one.
    if "expect_min" in check and value < float(check["expect_min"]):
        raise CheckFailedError(f"{value} < min {check['expect_min']}")
    if "expect_max" in check and value > float(check["expect_max"]):
        raise CheckFailedError(f"{value} > max {check['expect_max']}")


def append_history(path: str | Path, record: dict[str, Any]) -> None:
    """Append one JSON-line record to the RTO history file (created if missing)."""
    with Path(path).open("a") as fh:
        fh.write(json.dumps(record) + "\n")


def append_run_history(notify: Plan, start: float, ok: bool, error: str | None = None) -> None:
    """Append this run's outcome to `notify.history_file`, when the plan asks for one."""
    history_file = notify.get("history_file")
    if not history_file:
        return
    record: dict[str, Any] = {
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
        # The hook reads this from the environment, where there is no such
        # thing as an unset-but-present variable: an absent error is "".
        "BACKUP_VERIFY_ERROR": error or "",
        "BACKUP_VERIFY_DURATION": f"{duration:.1f}",
    }
    try:
        # ponytail: on_failure is an arbitrary shell pipeline from the same trusted
        # plan file as fetch.command, so shell=True is intentional here too. check=False
        # keeps a failing notifier from ever changing the run's outcome.
        # One line so the match and its exemptions share it: semgrep reports
        # against the shell=True argument, not against the call's opening line.
        subprocess.run(command, shell=True, check=False, env=env)  # noqa: S602  # nosec B602  # nosemgrep
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
    env_args: list[str] = []
    for k, v in restore.get("env", {}).items():
        env_args += ["-e", f"{k}={v}"]
    limit_args: list[str] = []
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
    # Three linters, three spellings of the same exemption: ruff (S602),
    # bandit (B602) and semgrep all flag shell=True, and all three are
    # answered by the comment above rather than by a repo-wide rule.
    #
    # The env var is the only way a shell fetcher learns where to put what it
    # fetched — the native fetchers are handed `workdir` as an argument, and
    # before this a plan had to guess (a `backup-verify-*/` glob against the
    # tempdir, which matches two directories the moment two runs overlap).
    env = {**os.environ, "BACKUP_VERIFY_WORKDIR": workdir}
    subprocess.run(fetch["command"], shell=True, check=True, env=env)  # noqa: S602  # nosec B602  # nosemgrep


def docker_runner(name: str) -> Shell:
    """Run plan commands inside the scratch container."""
    return lambda command: docker(["exec", name, "sh", "-c", command])


def local_runner(workdir: str, restore: Plan) -> Shell:
    """Run plan commands here, in this process's own container.

    For `restore.image`-less plans, where whatever is already running this is
    the scratch environment — a Kubernetes CronJob pod, a throwaway VM. There is
    no bind mount and therefore no `/work`, so the workdir arrives two ways
    instead: it is the commands' working directory, and it is
    `$BACKUP_VERIFY_WORKDIR` for the plans that would rather be explicit.
    """
    env = {
        **os.environ,
        "BACKUP_VERIFY_WORKDIR": workdir,
        **{k: str(v) for k, v in restore.get("env", {}).items()},
    }

    def run(command: str) -> str:
        # ponytail: same trusted-plan argument as fetch.command and notify.on_failure
        # — the plan file is the operator's own document.
        #
        # The three exemptions sit on two different lines because the three
        # linters report in two different places: ruff and bandit against the
        # call, semgrep against the `shell=True` argument itself. The other two
        # shell=True calls here are one-liners, where that distinction does not
        # show; this call is too long to be one, so it has to be said twice.
        done = subprocess.run(  # noqa: S602  # nosec B602
            command,
            shell=True,  # nosemgrep
            check=True,
            capture_output=True,
            text=True,
            cwd=workdir,
            env=env,
        )
        return done.stdout.strip()

    return run


def wait_until_ready(restore: Plan, run_sh: Shell) -> None:
    """Poll `restore.ready_command` until it exits 0, or give up at ready_timeout."""
    deadline = time.time() + int(restore.get("ready_timeout", DEFAULT_READY_TIMEOUT_SECONDS))
    while True:
        try:
            run_sh(restore["ready_command"])
        except subprocess.CalledProcessError as err:
            if time.time() > deadline:
                # Not "the scratch container never became ready": in-place plans
                # can have a ready_command too (a sidecar, a database already in
                # the pod), and this string is what reaches history_file and
                # $BACKUP_VERIFY_ERROR.
                msg = "restore.ready_command never succeeded within ready_timeout"
                raise CheckFailedError(msg) from err
            time.sleep(READY_POLL_INTERVAL_SECONDS)
        else:
            return


def run_checks(checks: list[Plan], run_sh: Shell) -> list[Result]:
    """Run every smoke check in the scratch environment; one result record each."""
    results: list[Result] = []
    for check in checks:
        output = run_sh(check["command"])
        try:
            evaluate(check, output)
            results.append({"name": check["name"], "status": "pass", "output": output})
            print(f"  ✓ {check['name']} ({output})")  # noqa: T201 — run progress, on stdout
        except CheckFailedError as e:
            results.append({"name": check["name"], "status": "fail", "output": str(e)})
            print(f"  ✗ {check['name']}: {e}")  # noqa: T201 — run progress, on stdout
    return results


def validate_restore(restore: Plan) -> None:
    """Reject the two `restore` shapes that would otherwise fail quietly, or pass.

    Both are about which environment the plan's commands end up in, which is the
    one thing a plan cannot afford to get wrong by accident.
    """
    # Restoring in place is chosen by leaving `image` out, so a present but empty
    # one is a plan defect rather than consent: `image: {{ .Values.scratch }}`
    # with nothing to substitute would move the load and every check out of the
    # scratch container and into this process, quietly, and still pass.
    if "image" in restore and not restore["image"]:
        msg = "restore.image is empty; omit the key entirely to restore in place"
        raise ValueError(msg)
    # A container that has just started needs something to wait for: skipping the
    # poll fires `load_command` at a database that is still booting, which fails
    # intermittently or, worse, passes. In place there is nothing booting, which
    # is the only reason `ready_command` is ever optional.
    if restore.get("image") and not restore.get("ready_command"):
        msg = "restore.ready_command is required alongside restore.image"
        raise ValueError(msg)


def restore_and_check(plan: Plan, restore: Plan, run_sh: Shell) -> list[Result]:
    """Wait for the environment, load the dump into it, ask it the questions."""
    if restore.get("ready_command"):
        wait_until_ready(restore, run_sh)
    print("backup-verify: loading dump")  # noqa: T201 — run progress, on stdout
    run_sh(restore["load_command"])
    return run_checks(plan.get("checks", []), run_sh)


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
        # Ahead of the fetch: a plan defect should cost nothing to find.
        validate_restore(restore)

        # Absolute, always: docker reads a relative `-v` source as a *named
        # volume*, so `--workdir work` would bind an empty volume over /work and
        # the load would fail with "no such file" pointing nowhere near the
        # cause. In place, a relative $BACKUP_VERIFY_WORKDIR would break any
        # command that cd's away from the workdir it is already sitting in.
        workdir = str(Path(workdir or tempfile.mkdtemp(prefix="backup-verify-")).resolve())
        Path(workdir).mkdir(parents=True, exist_ok=True)
        fetch_backup(plan["fetch"], workdir)

        if restore.get("image"):
            # Isolated (--internal, no external egress) network per run: the container
            # only needs to talk to itself over docker exec, and this keeps concurrent
            # runs from ever sharing a network namespace.
            docker(["network", "create", "--internal", network])
            print(f"backup-verify: starting scratch container ({restore['image']})")  # noqa: T201 — run progress, on stdout
            docker(build_run_args(name, workdir, restore, network))
            try:
                results = restore_and_check(plan, restore, docker_runner(name))
            finally:
                if not keep:
                    # Best-effort teardown: a failure here must not mask the run's
                    # own result, hence check=False.
                    _docker_quietly(["rm", "-f", name])
                    _docker_quietly(["network", "rm", network])
        else:
            # No image: this process is already the scratch environment. Nothing
            # to boot, nothing to tear down — so `--keep` has nothing to keep.
            for ignored in ("memory", "cpus"):
                if restore.get(ignored):
                    logger.warning("restore.%s needs a scratch container; ignored without restore.image", ignored)
            print(f"backup-verify: restoring in place ({workdir})")  # noqa: T201 — run progress, on stdout
            results = restore_and_check(plan, restore, local_runner(workdir, restore))
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
    run_cmd.add_argument(
        "--workdir",
        help="where the backup is fetched to (default: a fresh temporary directory). "
        "With restore.image it is bind-mounted at /work; without one it is the "
        "commands' working directory. Either way it is $BACKUP_VERIFY_WORKDIR.",
    )
    args = parser.parse_args(argv)

    try:
        plan = yaml.safe_load(Path(args.plan).read_text())
    except OSError:
        logger.exception("cannot read plan %s", args.plan)
        return EXIT_NOINPUT
    except yaml.YAMLError:
        logger.exception("plan %s is not valid YAML", args.plan)
        return EXIT_DATAERR

    results, ok, duration = run_plan(plan, keep=args.keep, workdir=args.workdir)
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
