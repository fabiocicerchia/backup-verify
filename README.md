# backup-verify

[![CI](https://github.com/fabiocicerchia/backup-verify/actions/workflows/ci.yml/badge.svg)](https://github.com/fabiocicerchia/backup-verify/actions/workflows/ci.yml)
[![Security](https://github.com/fabiocicerchia/backup-verify/actions/workflows/security.yml/badge.svg)](https://github.com/fabiocicerchia/backup-verify/actions/workflows/security.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/fabiocicerchia/backup-verify/badge)](https://securityscorecards.dev/viewer/?uri=github.com/fabiocicerchia/backup-verify)
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Ffabiocicerchia%2Fbackup-verify.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2Ffabiocicerchia%2Fbackup-verify?ref=badge_shield)
[![Release](https://img.shields.io/github/v/release/fabiocicerchia/backup-verify)](https://github.com/fabiocicerchia/backup-verify/releases)

**Restores your latest backup into a scratch container on a schedule and runs
smoke queries against it.** A backup that hasn't been restored is a hope, not
a backup — this makes restore-testing a boring weekly cron instead of an
incident-day discovery.

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/fabiocicerchia/backup-verify/main/install.sh | bash
```

Or with pipx directly:

```sh
pipx install git+https://github.com/fabiocicerchia/backup-verify
```

## How it works

One YAML plan describes the loop
(see [`examples/backup-verify.yaml`](examples/backup-verify.yaml)):

1. **fetch** — shell command that pulls the *latest* backup (S3, …), or a
   native `type: restic` / `type: pgbackrest` fetcher (no shell)
1. **restore** — scratch container image, readiness probe, load command, on an
   isolated (`--internal`) per-run docker network; optional `memory`/`cpus`
   limits
1. **checks** — smoke queries with `expect` / `expect_min` / `expect_max`
   (row counts, data freshness, schema presence)
1. **notify** — heartbeat URL pinged *only on success*
   (healthchecks.io-style dead-man switch: silence = broken backups); optional
   `history_file` appends a `{timestamp, duration_seconds, ok}` JSON line per
   run, so you can trend RTO over time

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
- [x] MySQL/Mongo example plans (works today, needs documented recipes)
- [x] Restore-duration tracking (RTO trend over time)
- [x] Isolated network for the scratch container; resource limits
- [x] Native restic/pgBackRest fetchers instead of raw shell

## Development

`make dev` then `make test` / `make lint`.

## License

Apache 2.0 — see [LICENSE](LICENSE).
