#!/usr/bin/env bash
set -euo pipefail
# One-line installer for backup-verify
# Usage: curl -fsSL https://raw.githubusercontent.com/fabiocicerchia/backup-verify/main/install.sh | bash

if command -v pipx &>/dev/null; then
  pipx install git+https://github.com/fabiocicerchia/backup-verify
else
  pip install --user git+https://github.com/fabiocicerchia/backup-verify
fi
echo "backup-verify installed. Run: backup-verify --help"
