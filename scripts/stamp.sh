#!/usr/bin/env bash
# Stamp the deployed build with the commit that produced it.
#
# The first version of this was a date typed in once by hand. It then sat
# unchanged across six deploys while claiming to identify the build, which made
# the diagnostics output actively misleading. A stamp that does not change
# is worse than no stamp.
set -euo pipefail
cd "$(dirname "$0")/.."
# Stamp AFTER the commit exists, then amend, or the recorded sha is the one
# before the commit that contains it. Off-by-one in a version marker is the
# same class of wrong as no marker at all.
SHA="$(git rev-parse --short HEAD)"
TS="$(date -u +%Y-%m-%dT%H:%MZ)"
perl -pi -e "s/build [0-9a-f]{7,}( \([^)]*\))?/build $SHA ($TS)/g; s/__BUILD_SHA__/$SHA ($TS)/g" docs/index.html
grep -o "build [0-9a-f]\{7,\} ([^)]*)" docs/index.html | head -1

# Amend so the file records the commit it actually ships in, then verify.
if [ "${STAMP_AMEND:-0}" = "1" ]; then
  git add docs/index.html
  git commit -q --amend --no-edit
  NEW="$(git rev-parse --short HEAD)"
  perl -pi -e "s/build [0-9a-f]{7,} \\(/build $NEW (/" docs/index.html
  git add docs/index.html && git commit -q --amend --no-edit
  FINAL="$(git rev-parse --short HEAD)"
  IN_FILE="$(grep -o 'build [0-9a-f]\{7,\}' docs/index.html | head -1 | awk '{print $2}')"
  [ "$FINAL" = "$IN_FILE" ] && echo "stamp matches commit: $FINAL" \
    || { echo "STAMP MISMATCH: file says $IN_FILE, commit is $FINAL"; exit 1; }
fi
