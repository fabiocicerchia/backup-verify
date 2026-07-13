# backup-verify

[![CI](https://github.com/fabiocicerchia/backup-verify/actions/workflows/ci.yml/badge.svg)](https://github.com/fabiocicerchia/backup-verify/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

**Restores your latest backup into a scratch container on a schedule and runs
smoke queries against it.** A backup that hasn't been restored is a hope, not
a backup — this makes restore-testing a boring weekly cron instead of an
incident-day discovery.

## How it works

One YAML plan describes the loop
(see [`examples/backup-verify.yaml`](examples/backup-verify.yaml)):

1. **fetch** — shell command that pulls the *latest* backup (S3, restic, …)
1. **restore** — scratch container image, readiness probe, load command
1. **checks** — smoke queries with `expect` / `expect_min` / `expect_max`
   (row counts, data freshness, schema presence)
1. **notify** — heartbeat URL pinged *only on success*
   (healthchecks.io-style dead-man switch: silence = broken backups)

```console
$ backup-verify run backup-verify.yaml
backup-verify: fetching latest backup
backup-verify: starting scratch container (postgres:16-alpine)
backup-verify: loading dump
  ✓ users table is populated (48212)
  ✓ latest order is recent (3.2)
  ✓ schema contains critical tables (3)

backup-verify: PASS (3/3 checks)
```

Schedule it weekly in CI or with `fabiocicerchia/cron-runner`; the scratch
container is always torn down (`--keep` to inspect failures).

## Status & roadmap

- [x] Plan runner: fetch → restore → checks → heartbeat, JSON output
- [ ] MySQL/Mongo example plans (works today, needs documented recipes)
- [ ] Restore-duration tracking (RTO trend over time)
- [ ] Isolated network for the scratch container; resource limits
- [ ] Native restic/pgBackRest fetchers instead of raw shell

## Development

`make dev` then `make test` / `make lint`.

## License

Apache 2.0 — see [LICENSE](LICENSE).
