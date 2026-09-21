# Examples

- [`backup-verify.yaml`](backup-verify.yaml) — Postgres: fetch → restore →
  checks → heartbeat. Run it with:

  ```sh
  backup-verify run backup-verify.yaml
  ```

- [`backup-verify-mysql.yaml`](backup-verify-mysql.yaml) — same loop against a
  `mysqldump` restored into `mysql:8`, checked with `mysql -N -e`.

- [`backup-verify-mongo.yaml`](backup-verify-mongo.yaml) — same loop against a
  `mongodump --archive` restored into `mongo:7` with `mongorestore`, checked
  with `mongosh --eval`.

- [`backup-verify-sqlite-in-place.yaml`](backup-verify-sqlite-in-place.yaml) —
  no `restore.image`, and so no Docker: the load and the checks run in this
  process, in the workdir. For a Kubernetes CronJob or a throwaway VM that is
  already the disposable environment a scratch container would have provided.

- [`backup-verify-restic.yaml`](backup-verify-restic.yaml) — `fetch.type:
  restic` instead of a shell pipeline: runs `restic restore` directly (no
  shell). `fetch.type: pgbackrest` works the same way for pgBackRest stanzas.
