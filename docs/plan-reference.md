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
into the scratch container at `/work`.

| `type`       | Fields                                                                 |
| ------------ | ---------------------------------------------------------------------- |
| *(omitted)*  | `command` — an arbitrary shell pipeline (runs with `shell=True`)       |
| `restic`     | `repository`, `snapshot` (default `latest`), `target`, `password_file` |
| `pgbackrest` | `stanza`, `pg1_path`, `extra_args` (list)                              |

`restic`/`pgbackrest` run as argv (no shell); a bare `command` is your
responsibility to keep injection-safe since it runs through `sh -c`.

## `restore`

Boots the scratch container that the dump gets loaded into.

| Field            | Meaning                                                         |
| ---------------- | --------------------------------------------------------------- |
| `image`          | Docker image for the scratch database                           |
| `env`            | Environment variables passed to the container                   |
| `ready_command`  | Polled (every 2s, via `docker exec`) until it exits 0           |
| `ready_timeout`  | Seconds to wait for `ready_command` before failing (default 60) |
| `load_command`   | Loads the fetched dump from `/work` into the running database   |
| `memory`, `cpus` | Optional resource limits (`docker run --memory`/`--cpus`)       |

The container runs on its own `--internal` (no external egress) Docker
network and is removed afterward unless `--keep` is passed.

## `checks`

A list of smoke queries run inside the scratch container (`docker exec ...
sh -c <command>`), each evaluated against its trimmed stdout:

| Field        | Meaning                                   |
| ------------ | ----------------------------------------- |
| `name`       | Label shown in output                     |
| `command`    | Shell command to run inside the container |
| `expect`     | Exact string match                        |
| `expect_min` | Output cast to float, must be ≥ this      |
| `expect_max` | Output cast to float, must be ≤ this      |

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
