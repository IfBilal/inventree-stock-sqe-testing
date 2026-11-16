#!/usr/bin/env bash
# Build the React UI into the backend static dir (needed for browser tests). Slow and disk heavy (~1-1.5 GB node_modules).
set -euo pipefail
cd "$(dirname "$0")/../upstream/src/frontend"
if command -v yarn >/dev/null; then Y=yarn; else Y="npx --yes yarn@1"; fi
$Y install --frozen-lockfile
$Y run compile
$Y run build
