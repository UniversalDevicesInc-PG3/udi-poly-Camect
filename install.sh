#!/usr/bin/env bash
# Install Polyglot deps, then pull the jimboca/camect-py fork (websocket
# connected/synced APIs) until upstream ships those hooks. Symlink so
# `import camect` resolves from the node server home directory.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

CAMECT_REPO="${CAMECT_REPO:-https://github.com/jimboca/camect-py.git}"
CAMECT_REF="${CAMECT_REF:-master}"

pip3 install -r requirements.txt --upgrade --user --no-warn-script-location
# Prefer the forked client over any prior PyPI camect-py install
pip3 uninstall -y camect-py >/dev/null 2>&1 || true

if [ -d camect-py/.git ]; then
  git -C camect-py fetch --depth 1 origin "$CAMECT_REF"
  git -C camect-py checkout -f FETCH_HEAD
else
  rm -rf camect-py
  git clone --depth 1 --branch "$CAMECT_REF" "$CAMECT_REPO" camect-py
fi

# NS home is on sys.path; this makes `import camect` use the fork
ln -sfn camect-py/camect camect

echo "Installed camect from ${CAMECT_REPO} (${CAMECT_REF}) via symlink ./camect"
