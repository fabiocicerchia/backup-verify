# backup-verify

[![CI](https://github.com/fabiocicerchia/backup-verify/actions/workflows/ci.yml/badge.svg)](https://github.com/fabiocicerchia/backup-verify/actions/workflows/ci.yml)
[![Security](https://github.com/fabiocicerchia/backup-verify/actions/workflows/security.yml/badge.svg)](https://github.com/fabiocicerchia/backup-verify/actions/workflows/security.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/fabiocicerchia/backup-verify/badge)](https://securityscorecards.dev/viewer/?uri=github.com/fabiocicerchia/backup-verify)
[![CI carbon](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/fabiocicerchia/backup-verify/gh-pages/badge.json)](.github/workflows/carbon-badge.yml)
[![Release](https://img.shields.io/github/v/release/fabiocicerchia/backup-verify)](https://github.com/fabiocicerchia/backup-verify/releases)

**Restores your latest backup into a scratch container on a schedule and runs
smoke queries against it.** A backup that hasn't been restored is a hope, not
a backup — this makes restore-testing a boring weekly cron instead of an
incident-day discovery.

## Features

- Restores the **latest** backup into a scratch container and runs smoke
  queries against it, on a schedule — so a bad backup surfaces on a boring
  weekly cron rather than on incident day.
- One YAML plan covers the whole loop: **fetch → restore → checks → notify**.
- Native `restic` and `pgbackrest` fetchers with no shell involved; anything
  else via a shell command.
- Restores onto an isolated per-run Docker network (`--internal`), with
  optional `memory` / `cpus` limits.
- Checks assert with `expect` / `expect_min` / `expect_max` — row counts, data
  freshness, schema presence.
- Dead-man's-switch notification: the heartbeat URL is pinged **only on
  success**, so silence means the backups are broken.
- Optional `history_file` appends one `{timestamp, duration_seconds, ok}` line
  per run, so restore time can be trended rather than guessed.
- Optional `on_failure` command, handed `BACKUP_VERIFY_STATUS`,
  `BACKUP_VERIFY_FAILED_CHECKS`, `BACKUP_VERIFY_ERROR` and
  `BACKUP_VERIFY_DURATION` — no wrapper script needed.
- Always tears the scratch container down; `--keep` retains it to inspect a
  failure, `--json` for machine-readable output.

## Install

```sh
pipx install git+https://github.com/fabiocicerchia/backup-verify
```

Or with pip:

```sh
pip install --user git+https://github.com/fabiocicerchia/backup-verify
```

## How it works

One YAML plan describes the loop
(see [`examples/backup-verify.yaml`](examples/backup-verify.yaml), or the
field-by-field [Plan Reference](docs/plan-reference.md)):

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
   run, so you can trend RTO over time; optional `on_failure` shell command run
   *only on failure* (any check failing or the run throwing), handed
   `BACKUP_VERIFY_STATUS` / `BACKUP_VERIFY_FAILED_CHECKS` / `BACKUP_VERIFY_ERROR`
   / `BACKUP_VERIFY_DURATION` — so you don't have to wrap the run yourself

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

## Verifying the image

Every published image is signed with [cosign][cosign], keyless: the identity in
the signature is the workflow that published it, not a key anybody holds.

```sh
cosign verify ghcr.io/fabiocicerchia/backup-verify:latest \
  --certificate-identity-regexp \
    'https://github.com/fabiocicerchia/backup-verify/.github/workflows/.*' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

`no signatures found` means the tag predates signing, not that verification was
set up wrongly — a wrong identity or issuer says so explicitly. Re-run the
publish workflow for that tag to sign it.

[cosign]: https://docs.sigstore.dev/

## Development

`make dev` then `make test` / `make lint`.

## Usage

```sh
backup-verify run backup-verify.yaml
backup-verify run backup-verify.yaml --keep   # keep the scratch container to inspect failures
backup-verify run backup-verify.yaml --json   # machine-readable output
```

More in [`docs/getting-started.md`](docs/getting-started.md).

## Documentation

Full docs live in [`docs/`](docs/). Runnable examples live in [`examples/`](examples/).

## Support

Need help implementing this? [Get in touch](https://fabiocicerchia.it/contact).

## License

Apache 2.0 — see [LICENSE](LICENSE).
