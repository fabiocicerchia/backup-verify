# Plan Reference

A plan is one YAML file with four sections: `fetch`, `restore`, `checks`,
`notify`. Each stage feeds the next — see [Architecture](architecture.md) for
the data flow.

## Annotated example

```yaml
fetch:
  type: restic                       # or "pgbackrest", or omit for a raw shell command
  repository: s3:s3.amazonaws.com/backups/db
  snapshot: latest                   # optional, default: latest
  password_file: /run/secrets/restic-password   # optional, else RESTIC_PASSWORD env

restore:
  image: postgres:16-alpine          # scratch container image
  env:
    POSTGRES_PASSWORD: scratch
  ready_command: pg_isready -U postgres   # polled until it exits 0
  ready_timeout: 60                  # seconds to wait before giving up
  load_command: gunzip -c /work/dump.sql.gz | psql -U postgres
  # memory: 512m                     # optional, passed to `docker run --memory`
  # cpus: "1"                        # optional, passed to `docker run --cpus`

checks:
  - name: users table is populated
    command: psql -U postgres -tAc "SELECT count(*) FROM users"
    expect_min: 1000                 # numeric floor

  - name: schema contains critical tables
    command: psql -U postgres -tAc "SELECT count(*) FROM information_schema.tables WHERE table_name IN ('users','orders')"
    expect: "2"                      # exact string match

notify:
  heartbeat_url: https://hc-ping.com/your-uuid   # pinged only if all checks pass
  history_file: /var/lib/backup-verify/history.jsonl  # one JSON line appended per run
  on_failure: 'curl -fsS -m 10 "https://alert.example/notify?msg=$BACKUP_VERIFY_STATUS"'  # shell command run on any failure
```

## `fetch`

Pulls the latest backup onto the host, into a workdir that gets bind-mounted
into the scratch container at `/work` (when restoring in place there is no
mount — see below).

The workdir is a fresh temporary directory unless `--workdir` names one, and a
relative `--workdir` is resolved to an absolute path before anything uses it. A
`restic`/`pgbackrest` fetch is handed it as an argument; a shell `command` gets
it as **`$BACKUP_VERIFY_WORKDIR`**, which is the only way it can know where to
put what it fetched.

`fetch` always runs on the host, never in the container, so a shell `command`
that writes to `/work` is writing to a host path that usually does not exist —
use `$BACKUP_VERIFY_WORKDIR`. `/work` is the container's name for that same
directory, which is what `load_command` and the checks see.

| `type`       | Fields                                                                 |
| ------------ | ---------------------------------------------------------------------- |
| *(omitted)*  | `command` — an arbitrary shell pipeline (runs with `shell=True`)       |
| `restic`     | `repository`, `snapshot` (default `latest`), `target`, `password_file` |
| `pgbackrest` | `stanza`, `pg1_path`, `extra_args` (list)                              |

`restic`/`pgbackrest` run as argv (no shell); a bare `command` is your
responsibility to keep injection-safe since it runs through `sh -c`.

## `restore`

Boots the scratch container that the dump gets loaded into.

| Field            | Meaning                                                                        |
| ---------------- | ------------------------------------------------------------------------------ |
| `image`          | Docker image for the scratch database. **Omit to restore in place**            |
| `env`            | Environment variables passed to the container                                  |
| `ready_command`  | Polled (every 2s) until it exits 0. Required with `image`                      |
| `ready_timeout`  | Seconds to wait for `ready_command` before failing (default 60)                |
| `load_command`   | Loads the fetched dump: from `/work` in a container, from the workdir in place |
| `memory`, `cpus` | Optional resource limits (`docker run --memory`/`--cpus`)                      |

The container runs on its own `--internal` (no external egress) Docker
network and is removed afterward unless `--keep` is passed.

### Restoring in place

Leave `image` out and the `load_command` and every check run in this process
instead of in a container — for when whatever runs backup-verify is *already*
the scratch environment: a Kubernetes CronJob pod, a throwaway VM, a CI job.
The isolation that the scratch container provides is the pod's, and there is no
Docker daemon to need.

What changes:

- The workdir is not bind-mounted, so there is no `/work`. It is the commands'
  working directory instead (so `rows.txt` and `./restored/` just work), and it
  is `$BACKUP_VERIFY_WORKDIR`. Pass `--workdir /work` to keep a plan's paths
  identical in both modes.
- `env` is applied to the commands' environment rather than to a container.
- `ready_command` is usually pointless — nothing is booting — and is skipped
  when absent. This is the one mode where it may be omitted: with an `image` it
  is required, because without it the `load_command` fires at a container that
  is still starting.
- `memory` and `cpus` are container limits with no meaning here; they are
  ignored with a warning. Use the pod's own resource limits.
- `--keep` has nothing to keep.

Paths are relative to the workdir, which is where the commands already are —
absolute ones like `/work` or `/restore` assume a bind mount that is not there
and a writable filesystem root the pod may not have:

```yaml
restore:
  load_command: mkdir -p restored && for f in *.sqlite.gz; do
    gunzip -c "$f" > "restored/$(basename "$f" .gz)"; done

checks:
  - name: every database restores and passes integrity_check
    command: find restored -name '*.sqlite' -exec sqlite3 {} 'PRAGMA integrity_check' \; 2>&1 | sort -u | tr -d '\n'
    expect: "ok"
```

```sh
backup-verify run plan.yaml --json
```

The whole plan is in
[`examples/backup-verify-sqlite-in-place.yaml`](../examples/backup-verify-sqlite-in-place.yaml).

## `checks`

A list of smoke queries run in the scratch environment — `docker exec … sh -c
<command>` in a container, `sh -c <command>` in the workdir when restoring in
place — each evaluated against its trimmed stdout:

| Field        | Meaning                                      |
| ------------ | -------------------------------------------- |
| `name`       | Label shown in output                        |
| `command`    | Shell command run in the scratch environment |
| `expect`     | Exact string match                           |
| `expect_min` | Output cast to float, must be ≥ this         |
| `expect_max` | Output cast to float, must be ≤ this         |

A run only counts as `PASS` if every check passes.

## `notify`

| Field           | Meaning                                                                                                          |
| --------------- | ---------------------------------------------------------------------------------------------------------------- |
| `heartbeat_url` | GET-pinged only when all checks pass (dead-man switch, e.g. healthchecks.io)                                     |
| `history_file`  | Appends one `{timestamp, duration_seconds, ok}` JSON line per run (an `error` field is added when the run threw) |
| `on_failure`    | Shell pipeline run when any check fails **or** the run throws (best-effort, `shell=True` like `fetch.command`)   |

All are optional. `heartbeat_url` fires only on success — silence is the signal
— while `on_failure` is its counterpart, firing only on failure. The
`on_failure` command receives context through environment variables:

| Env var                       | Value                                                     |
| ----------------------------- | --------------------------------------------------------- |
| `BACKUP_VERIFY_STATUS`        | `fail` (a check failed) or `error` (the run threw)        |
| `BACKUP_VERIFY_FAILED_CHECKS` | Comma-separated names of failed checks (empty on `error`) |
| `BACKUP_VERIFY_ERROR`         | The exception string (empty when checks merely failed)    |
| `BACKUP_VERIFY_DURATION`      | Run duration in seconds                                   |

`on_failure` is best-effort: a notifier that errors or exits non-zero never
masks the real failure or changes the exit code.
