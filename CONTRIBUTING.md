# Contributing

Thanks for taking the time to contribute to backup-verify! By participating you
agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting started

You need Python 3.10+ and `make`.

```sh
make setup   # git hooks + pre-commit (secret scanning)
make dev     # editable install with dev dependencies (pytest, ruff, build)
make lint    # ruff check .
make test    # pytest
```

## Making changes

- Keep changes focused; one logical change per PR, keeping the existing style.
- Add or update tests for behavior changes.
- Update `docs/` and `examples/` when behavior changes.
- Make sure `make lint` and `make test` pass locally (CI runs `code-quality`,
  `security`, and `CI`).

Don't edit `CHANGELOG.md` by hand — it's generated from commit messages by
release-please (see [Releases](#releases)).

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`,
`fix:`, `docs:`, `chore:`, etc. This keeps history readable and drives the
version bump: `fix:` → patch, `feat:` → minor, `feat!:` or a
`BREAKING CHANGE:` footer → major.

## Pull requests

Fill out the PR template, link related issues, and request review. Be kind.

## Releases

Releases are automated by [release-please](.github/workflows/release.yml); you
don't tag or edit the changelog manually.

1. Merge `feat:`/`fix:` PRs into `main` as normal — **no tag is created**.
1. release-please keeps an open **release PR** ("chore: release X.Y.Z"),
   recalculating the next version (in `pyproject.toml`) and `CHANGELOG.md` on
   every merge.
1. When you're ready to ship, **merge the release PR** — that (and only that)
   creates the `vX.Y.Z` tag and GitHub Release, which builds and (if
   `PUBLISH_TO_PYPI` is set) publishes the sdist + wheel to PyPI.

## License

By contributing you agree that your contributions are licensed under the
Apache License 2.0 (see [LICENSE](LICENSE)).
