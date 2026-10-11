#!/bin/bash
# Installs the tools the scroll-world skill needs in Claude Code cloud sessions.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

HIGGSFIELD_CLI_VERSION="1.1.26"

# Higgsfield CLI (scene stills + video chain fallback)
if ! command -v higgsfield >/dev/null 2>&1 || ! higgsfield --version 2>/dev/null | grep -q "$HIGGSFIELD_CLI_VERSION"; then
  npm install -g "@higgsfield/cli@${HIGGSFIELD_CLI_VERSION}" --no-fund --no-audit
fi

# Pillow for references/knockout.py, plus the scraper's own deps
python3 -m pip install --quiet Pillow
if [ -f "$CLAUDE_PROJECT_DIR/requirements.txt" ]; then
  python3 -m pip install --quiet -r "$CLAUDE_PROJECT_DIR/requirements.txt"
fi

# ffmpeg / ffprobe for frame extraction and encoding
if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    (apt-get update -qq && apt-get install -y -qq ffmpeg) || echo "warning: could not install ffmpeg" >&2
  fi
fi

echo 'export HIGGSFIELD_NO_UPDATE_CHECK=1' >> "${CLAUDE_ENV_FILE:-/dev/null}"
