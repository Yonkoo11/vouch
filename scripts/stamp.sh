#!/usr/bin/env bash
# Stamp the deployed build with the commit that produced it.
#
# The first version of this was a date typed in once by hand. It then sat
# unchanged across six deploys while claiming to identify the build, which made
# the diagnostics output actively misleading. A stamp that does not change
# is worse than no stamp.
set -euo pipefail
cd "$(dirname "$0")/.."
SHA="$(git rev-parse --short HEAD)"
TS="$(date -u +%Y-%m-%dT%H:%MZ)"
perl -pi -e "s/build [0-9a-f]{7,}( \([^)]*\))?/build $SHA ($TS)/g; s/__BUILD_SHA__/$SHA ($TS)/g" docs/index.html
grep -o "build [0-9a-f]\{7,\} ([^)]*)" docs/index.html | head -1
