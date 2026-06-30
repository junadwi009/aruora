#!/usr/bin/env bash
# Fail if any real API key could reach the browser. The threat model is the
# *built web bundle* only — server code (api/) legitimately references keys via
# env vars, so it is intentionally NOT scanned.
set -euo pipefail
cd "$(dirname "$0")/.."

# Ensure a fresh bundle exists to scan.
if [ ! -d web/dist ]; then ( cd web && npm run build ); fi

# Match actual key VALUES, not variable names:
#   OpenRouter  sk-or-v1-...   Anthropic  sk-ant-...   generic long sk- token
PATTERN='sk-or-v1-[A-Za-z0-9_-]{20,}|sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}'

hits=$(grep -rInE "$PATTERN" web/dist 2>/dev/null || true)
if [ -n "$hits" ]; then
  echo "SECRET SCAN FAILED — key-like string found in the web bundle:"
  echo "$hits"
  exit 1
fi
echo "secret scan: clean — no API key found in web/dist"
