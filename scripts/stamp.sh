#!/usr/bin/env bash
# Stamp the deployed build so diagnostics can identify what a browser is running.
#
# Two earlier attempts were wrong. The first was a date typed once by hand, which
# then sat unchanged across six deploys while claiming to identify the build.
# The second embedded the commit sha, which cannot work: amending to include the
# stamp changes the sha, so the file can never contain the hash of the commit
# that ships it.
#
# So: a UTC deploy timestamp, plus the sha of the tree being deployed. The tree
# hash is stable under amend because it describes content, not history.
set -euo pipefail
cd "$(dirname "$0")/.."
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
perl -pi -e "s/build [^\"<']*?(?=[\"<'])/build PENDING/g" docs/index.html
TREE="$(git hash-object docs/index.html | cut -c1-7)"
perl -pi -e "s/build PENDING/build $TREE $TS/g" docs/index.html
grep -o "build [0-9a-f]\{7\} [0-9TZ:-]*" docs/index.html | head -2
