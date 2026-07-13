# CLAUDE.md

Guidance for Claude Code (and other AI agents) working in this repo.

## Project

backup-verify is a single-file Python CLI (`backup_verify.py`, entry point
`backup_verify:main`) that restores the latest backup into a scratch container
on a schedule and runs smoke queries against it. A YAML plan describes the
fetch → restore → checks → notify loop. Stdlib + `pyyaml` only.

## Commands

```sh
make dev     # editable install with dev deps (pytest, ruff, build)
make lint    # ruff check .
make test    # pytest -q
make build   # python -m build
backup-verify run examples/backup-verify.yaml   # run a plan
```

## Conventions

- Match existing style; don't reformat unrelated code.
- Conventional Commits for messages (see CONTRIBUTING.md).
- Update docs/ and examples/ with behavior changes. CHANGELOG.md is generated
  by release-please from commit messages — don't edit it by hand.
- Never commit secrets; CI runs gitleaks. Keep `.env` out of git.

## Guardrails

- Don't add dependencies without a clear reason; prefer stdlib.
- Don't touch generated files or lockfiles by hand.
- Ask before large refactors or destructive operations.
