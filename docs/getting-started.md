# Getting Started

## Prerequisites

- Python 3.10+
- A container runtime on `PATH` (`docker` or `podman`) for scratch restores

## Setup

```sh
pip install backup-verify        # or: make dev  (editable + dev deps)
```

## Run

Write a plan (see [`../examples/backup-verify.yaml`](../examples/backup-verify.yaml))
describing the fetch → restore → checks → notify loop, then:

```sh
backup-verify run backup-verify.yaml
backup-verify run backup-verify.yaml --keep   # keep the scratch container to inspect failures
backup-verify run backup-verify.yaml --json   # machine-readable output
```

Schedule it weekly in CI or cron; the scratch container is always torn down
unless `--keep` is passed.
