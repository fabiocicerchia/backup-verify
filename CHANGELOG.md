# Changelog

This file is maintained automatically by
[release-please](https://github.com/googleapis/release-please) from Conventional
Commit messages — don't edit it by hand.

## [0.3.1](https://github.com/fabiocicerchia/backup-verify/compare/v0.3.0...v0.3.1) (2026-08-29)

### Bug Fixes

- unblock quality and clear the Scorecard pinned-dependencies finding ([#53](https://github.com/fabiocicerchia/backup-verify/issues/53)) ([c1794bf](https://github.com/fabiocicerchia/backup-verify/commit/c1794bf5a5d35ee49db2dcc1150e5a954cdeba50))

## [0.3.0](https://github.com/fabiocicerchia/backup-verify/compare/v0.2.0...v0.3.0) (2026-08-25)

### Features

- **docs:** build the docs site in Actions and drop Read the Docs ([#44](https://github.com/fabiocicerchia/backup-verify/issues/44)) ([148d7f3](https://github.com/fabiocicerchia/backup-verify/commit/148d7f34e206be0ccad8b113cc1711dd682f6a7c))

### Bug Fixes

- **ci:** compute the next release PR after the draft is published ([#41](https://github.com/fabiocicerchia/backup-verify/issues/41)) ([556d351](https://github.com/fabiocicerchia/backup-verify/commit/556d351fd61b108b7ed7111a08b9a17761a404a6))

## [0.2.0](https://github.com/fabiocicerchia/backup-verify/compare/v0.1.2...v0.2.0) (2026-08-14)

### Features

- **notify:** record failures in history and add on_failure hook ([#36](https://github.com/fabiocicerchia/backup-verify/issues/36)) ([2130b26](https://github.com/fabiocicerchia/backup-verify/commit/2130b265fbcafca1904fca8f78112cb92e1f0055))

## [0.1.2](https://github.com/fabiocicerchia/backup-verify/compare/v0.1.1...v0.1.2) (2026-08-13)

### Bug Fixes

- security and code-quality findings ([#33](https://github.com/fabiocicerchia/backup-verify/issues/33)) ([14bb728](https://github.com/fabiocicerchia/backup-verify/commit/14bb72856774b21c4f180d99aed708022f3a427e))

## [0.1.1](https://github.com/fabiocicerchia/backup-verify/compare/v0.1.0...v0.1.1) (2026-08-06)

### Bug Fixes

- **pre-commit:** stop check-yaml failing on Helm templates and multi-doc manifests ([0d17661](https://github.com/fabiocicerchia/backup-verify/commit/0d17661263a9d5ba0c1acfcb7e3c9dc422199b49))
- **security:** skip the SARIF upload on private repos ([1047c38](https://github.com/fabiocicerchia/backup-verify/commit/1047c38522f6d0486aa788cbd6b1c78329d7aba1))

## [0.1.0]

- Initial release: plan runner (fetch → restore → checks → heartbeat) with
  JSON output.
