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
