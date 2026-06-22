#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  echo "Usage: $0 OWNER/REPOSITORY public|private" >&2
  exit 2
}

[[ $# -eq 2 ]] || usage
REPOSITORY="$1"
VISIBILITY="$2"

case "$VISIBILITY" in
  public|private) ;;
  *) usage ;;
esac

command -v git >/dev/null || {
  echo "git is required." >&2
  exit 1
}
command -v gh >/dev/null || {
  echo "GitHub CLI (gh) is required." >&2
  exit 1
}

gh auth status >/dev/null 2>&1 || {
  echo "GitHub authentication is missing. Run: gh auth login --web" >&2
  exit 1
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .git ]]; then
  git init -b main
fi

if ! git config user.name >/dev/null; then
  echo "Configure git user.name before publishing." >&2
  exit 1
fi
if ! git config user.email >/dev/null; then
  echo "Configure git user.email before publishing." >&2
  exit 1
fi

python3 -m py_compile src/collector.py
python3 -m unittest discover -s tests -v

git add .
if ! git diff --cached --quiet; then
  git commit -m "Initial public release"
fi

if gh repo view "$REPOSITORY" >/dev/null 2>&1; then
  if ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "https://github.com/${REPOSITORY}.git"
  fi
  git push -u origin main
else
  gh repo create "$REPOSITORY" \
    "--${VISIBILITY}" \
    --source=. \
    --remote=origin \
    --push \
    --description "Self-hosted multi-vendor threat-feed collector with resumable sync and configurable output routes."
fi

echo "Published: https://github.com/${REPOSITORY}"
