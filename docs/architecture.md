# Architecture

backup-verify is a single Python module (`backup_verify.py`) driven by a YAML
plan. There is no daemon or state — each run is a self-contained pipeline.

## Overview

A backup that hasn't been restored is a hope, not a backup. backup-verify
turns restore-testing into a boring, schedulable check: it restores the latest
backup into a throwaway container and runs smoke queries against it.

## Data flow

```
plan.yaml
   │
   ▼
fetch   ── shell command that pulls the latest backup (S3, restic, …)
   │
   ▼
restore ── start scratch container, wait for readiness probe, load the dump
   │
   ▼
checks  ── smoke queries with expect / expect_min / expect_max
   │        (row counts, data freshness, schema presence)
   ▼
notify  ── ping a heartbeat URL only on success (dead-man switch)
   │
   ▼
teardown ── scratch container removed (unless --keep)
```

## Components

- **Plan parser** — loads and validates the YAML plan.
- **Runner** — executes the fetch → restore → checks → notify stages.
- **Reporter** — human-readable or `--json` output.

## Decisions

Record significant choices here (or in a `docs/adr/` folder if they pile up).
