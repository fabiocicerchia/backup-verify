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
make help    # Show this help
make setup   # Install the pre-commit hook
make install # Install the package
```

## Tooling

Shared config — the GitHub workflows, `.pre-commit-config.yaml`,
`.editorconfig`, `.hadolint.yaml`, `SECURITY.md` — comes from
[repo-skeleton](https://github.com/fabiocicerchia/repo-skeleton). Edit it
there, not here; a local edit is drift and the next sync overwrites it.
`check-drift.sh` in that repo reports what has diverged.

- `make setup` installs the pre-commit hook, and that is the whole of it.
  Don't add a `.githooks/` directory: `core.hooksPath` replaces `.git/hooks/`
  wholesale, so setting it silently stops every pre-commit hook from running.
- Hooks are pinned by commit SHA with the tag in a trailing comment. A tag can
  be moved, a SHA cannot.
- CI runs this same `.pre-commit-config.yaml` through `pre-commit/action`, so
  what passes locally is what gates the pull request.

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
