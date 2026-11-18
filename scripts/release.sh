#!/usr/bin/env bash
# Bump the version, commit, tag and push. The Publish workflow takes over from the tag.
#
#   scripts/release.sh 0.2.0
set -euo pipefail

VERSION="${1:?usage: scripts/release.sh X.Y.Z}"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Version must be X.Y.Z, got $VERSION"; exit 1; }

cd "$(dirname "$0")/.."
INIT=src/akeyless_cloudrun_rta/__init__.py
TAG="v${VERSION}"

[[ "$(git branch --show-current)" == "main" ]] || { echo "Run from main"; exit 1; }
[[ -z "$(git status --porcelain)" ]] || { echo "Working tree is not clean"; exit 1; }
git fetch -q origin main --tags
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || { echo "main is not in sync with origin/main"; exit 1; }
! git rev-parse -q --verify "refs/tags/${TAG}" >/dev/null || { echo "Tag ${TAG} already exists"; exit 1; }

CURRENT=$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' "$INIT")
if [[ "$CURRENT" != "$VERSION" ]]; then
  sed -i.bak "s/^__version__ = \".*\"$/__version__ = \"${VERSION}\"/" "$INIT" && rm -f "${INIT}.bak"
  git commit -q -m "chore: release ${TAG}" "$INIT"
fi

git tag -a "$TAG" -m "$TAG"
git push -q origin main "$TAG"
echo "Pushed ${TAG}. Follow the Publish workflow in GitHub Actions (approve the pypi environment if asked)."
