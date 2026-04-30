#!/usr/bin/env bash
set -u

failures=0

pass() { printf 'PASS: %s\n' "$1"; }
fail() {
  printf 'FAIL: %s\n' "$1"
  printf '      Next: %s\n' "$2"
  failures=$((failures + 1))
}

[ -f .trellis/.developer ] \
  && pass ".trellis/.developer exists" \
  || fail ".trellis/.developer is missing" "Run: python3 .trellis/scripts/init_developer.py <name>"

[ -d .gitnexus ] \
  && pass "GitNexus index exists" \
  || fail "GitNexus index is missing" "Run: npx gitnexus analyze"

command -v pnpm >/dev/null 2>&1 \
  && pass "pnpm is installed" \
  || fail "pnpm is not installed" "Install pnpm, then run: pnpm install"

[ -d node_modules ] \
  && pass "node_modules exists" \
  || fail "node_modules is missing" "Run: pnpm install"

head_commit="$(git rev-parse HEAD 2>/dev/null || true)"
index_commit=""
if [ -f .gitnexus/meta.json ]; then
  index_commit="$(python3 -c 'import json; print(json.load(open(".gitnexus/meta.json")).get("lastCommit", ""))' 2>/dev/null || true)"
fi

[ -n "$head_commit" ] && [ "$index_commit" = "$head_commit" ] \
  && pass "GitNexus index is fresh" \
  || fail "GitNexus index is stale or missing" "Run: npx gitnexus analyze"

if [ "$failures" -eq 0 ]; then
  printf '\nAll checks passed. Environment is ready.\n'
else
  printf '\n%d check(s) failed. See above for next steps.\n' "$failures"
fi

exit "$failures"
