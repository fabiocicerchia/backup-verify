# Getting Started

## Prerequisites

- Python 3.10+
- A container runtime on `PATH` (`docker` or `podman`) for scratch restores

## Setup

```sh
pip install backup-verify        # or: make dev  (editable + dev deps)
```

## Run

Write a plan (see [`../examples/backup-verify.yaml`](https://github.com/fabiocicerchia/backup-verify/blob/main/examples/backup-verify.yaml))
describing the fetch → restore → checks → notify loop, then:

```sh
backup-verify run backup-verify.yaml
backup-verify run backup-verify.yaml --keep   # keep the scratch container to inspect failures
backup-verify run backup-verify.yaml --json   # machine-readable output
```

Schedule it weekly in CI or cron; the scratch container is always torn down
unless `--keep` is passed.

## Exit codes

| Code | Meaning                                           |
| ---- | ------------------------------------------------- |
| 0    | every check passed — the backup restores          |
| 1    | at least one check failed                         |
| 2    | bad command line (emitted by the argument parser) |
| 65   | the plan is not valid YAML                        |
| 66   | the plan file could not be read                   |

Anything non-zero means you found out today rather than during an incident.
