# Changelog

This file is maintained automatically by
[release-please](https://github.com/googleapis/release-please) from Conventional
Commit messages — don't edit it by hand.

## [0.4.3](https://github.com/fabiocicerchia/backup-verify/compare/v0.4.2...v0.4.3) (2026-09-12)


### Documentation

* add a Features section to the README ([#96](https://github.com/fabiocicerchia/backup-verify/issues/96)) ([9ac2af0](https://github.com/fabiocicerchia/backup-verify/commit/9ac2af00b27e48f53e1784fd1efcce75044981fe))

## [0.4.2](https://github.com/fabiocicerchia/backup-verify/compare/v0.4.1...v0.4.2) (2026-09-11)


### Bug Fixes

* **release:** let the release PR carry a token that isn't GITHUB_TOKEN ([#94](https://github.com/fabiocicerchia/backup-verify/issues/94)) ([af8c0f9](https://github.com/fabiocicerchia/backup-verify/commit/af8c0f9786bacb95b2ab6e6165f07d6f2332f3c7))

## [0.4.1](https://github.com/fabiocicerchia/backup-verify/compare/v0.4.0...v0.4.1) (2026-09-10)


### Bug Fixes

* **coc:** restore the reporting address and the version deep-link ([#92](https://github.com/fabiocicerchia/backup-verify/issues/92)) ([157a2be](https://github.com/fabiocicerchia/backup-verify/commit/157a2bebf8c0ae8a335d0d330c4d47010d331f68))

## [0.4.0](https://github.com/fabiocicerchia/backup-verify/compare/v0.3.2...v0.4.0) (2026-09-10)


### Features

* **packaging:** ship a man page with the wheel ([#86](https://github.com/fabiocicerchia/backup-verify/issues/86)) ([f099031](https://github.com/fabiocicerchia/backup-verify/commit/f099031a8460ec1ce3fe3060a6c7407da3c36f45))


### Bug Fixes

* **release:** grant id-token on the job that calls the signing workflow ([#89](https://github.com/fabiocicerchia/backup-verify/issues/89)) ([b7985f3](https://github.com/fabiocicerchia/backup-verify/commit/b7985f322305a3f54784e1ba8ea107f0e1256497))

## [0.3.2](https://github.com/fabiocicerchia/backup-verify/compare/v0.3.1...v0.3.2) (2026-09-08)


### Bug Fixes

* **ci:** pin the editorconfig-checker binary version ([#68](https://github.com/fabiocicerchia/backup-verify/issues/68)) ([8e4ed18](https://github.com/fabiocicerchia/backup-verify/commit/8e4ed18db37d5559558af21ad3f667f41c42cabc))


### Documentation

* drop the curl | sh installer, document the direct install ([#76](https://github.com/fabiocicerchia/backup-verify/issues/76)) ([748b4c5](https://github.com/fabiocicerchia/backup-verify/commit/748b4c59d75cc296e7b8554a1c336f8317ec2449))

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
