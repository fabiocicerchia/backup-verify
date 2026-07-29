# Changelog

This file is maintained automatically by
[release-please](https://github.com/googleapis/release-please) from Conventional
Commit messages — don't edit it by hand.

## 0.1.0 (2026-07-29)


### Features

* add install.sh one-liner installer ([ade97ee](https://github.com/fabiocicerchia/backup-verify/commit/ade97eef87aecedeeebeff120c6bb57a3323991a))
* add MySQL and MongoDB example verification plans ([ca1ce2c](https://github.com/fabiocicerchia/backup-verify/commit/ca1ce2cbb2c58f5e8a7253cd65b0b1c52e0570cf))
* add native restic/pgBackRest fetchers ([5c77349](https://github.com/fabiocicerchia/backup-verify/commit/5c77349714919fd68614ae073032958c79b538af))
* isolate scratch container on a per-run docker network with resource limits ([f2ba5d7](https://github.com/fabiocicerchia/backup-verify/commit/f2ba5d76f932e2202021c075655a412df89d90aa))
* track restore duration and append RTO history ([0455ff2](https://github.com/fabiocicerchia/backup-verify/commit/0455ff2b9f9aa0fa24c2c76c110120002c6b7b49))


### Bug Fixes

* restore executable bit and add explicit check=False ([#11](https://github.com/fabiocicerchia/backup-verify/issues/11)) ([c1f2d9f](https://github.com/fabiocicerchia/backup-verify/commit/c1f2d9f35ab4af2eb557d9450309121d1a8db2b7))


### Documentation

* add GitHub Pages site, trim completed roadmap items from README ([f83f3ff](https://github.com/fabiocicerchia/backup-verify/commit/f83f3ff19dfa9fb74613aa312bf6b8ffc1d0c17f))
* add missing README badges ([e70043d](https://github.com/fabiocicerchia/backup-verify/commit/e70043d77fb46ea3ce2e3f280d78d8085ed47be9))
* add plan reference page ([606eac5](https://github.com/fabiocicerchia/backup-verify/commit/606eac564aca9e63c94b756bb60db2b4e1df65fc))
* remove the broken FOSSA badge ([ef744f8](https://github.com/fabiocicerchia/backup-verify/commit/ef744f8feb77fc8a33e68ab297207c2e603c3aca))

## [0.1.0]

- Initial release: plan runner (fetch → restore → checks → heartbeat) with
  JSON output.
