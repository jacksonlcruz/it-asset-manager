#!/bin/sh
set -e
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
GITHOOKS_DIR="$ROOT_DIR/.git/hooks"
SRC_DIR="$ROOT_DIR/.githooks"

if [ ! -d "$ROOT_DIR/.git" ]; then
  echo "This repository does not have a .git directory. Run this from the repo root."
  exit 1
fi

mkdir -p "$GITHOOKS_DIR"
cp "$SRC_DIR/pre-push" "$GITHOOKS_DIR/pre-push"
cp "$SRC_DIR/post-merge" "$GITHOOKS_DIR/post-merge"
chmod +x "$GITHOOKS_DIR/pre-push" "$GITHOOKS_DIR/post-merge"
echo "Hooks installed to $GITHOOKS_DIR"
