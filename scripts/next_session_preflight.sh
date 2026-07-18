#!/usr/bin/env bash
set -u

PROJECT_DIR="/Users/sanggyulee/codbeing"
INTERVIEW_JSON="/Users/sanggyulee/.ouroboros/data/interview_interview_20260716_124202.json"
MANUAL_SEED="$PROJECT_DIR/seed_codbeing_lab_ux_20260716.yaml"
HANDOFF="$PROJECT_DIR/NEXT_SESSION_HANDOFF_20260717.md"

status() {
  printf '%-34s %s\n' "$1" "$2"
}

printf 'codbeing next-session preflight\n'
printf '================================\n\n'

if [ -d "$PROJECT_DIR" ]; then
  status "project_dir" "ok: $PROJECT_DIR"
else
  status "project_dir" "missing: $PROJECT_DIR"
fi

if [ -f "$HANDOFF" ]; then
  status "handoff" "ok: $HANDOFF"
else
  status "handoff" "missing: $HANDOFF"
fi

if [ -n "${FAMILY_PROXY_API_KEY:-}" ]; then
  status "FAMILY_PROXY_API_KEY" "present"
else
  status "FAMILY_PROXY_API_KEY" "missing in this shell"
fi

if command -v zsh >/dev/null 2>&1; then
  zsh_key_status="$(zsh -ic 'printf "%s" "${FAMILY_PROXY_API_KEY:+present}"' 2>/dev/null || true)"
  if [ "$zsh_key_status" = "present" ]; then
    status "FAMILY_PROXY_API_KEY zsh -ic" "present"
  else
    status "FAMILY_PROXY_API_KEY zsh -ic" "missing"
  fi
fi

if [ -f "$INTERVIEW_JSON" ]; then
  interview_status="$(python3 - <<'PY' "$INTERVIEW_JSON"
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    data = json.load(f)
print(data.get("status", "<no status>"))
PY
)"
  status "interview_json" "ok: status=$interview_status"
else
  status "interview_json" "missing: $INTERVIEW_JSON"
fi

if [ -f "$MANUAL_SEED" ]; then
  seed_summary="$(python3 - <<'PY' "$MANUAL_SEED"
import sys
try:
    import yaml
except Exception:
    print("exists; pyyaml unavailable")
    raise SystemExit
with open(sys.argv[1], encoding="utf-8") as f:
    data = yaml.safe_load(f)
print(f"ok: ac={len(data.get('acceptance_criteria', []))}, constraints={len(data.get('constraints', []))}")
PY
)"
  status "manual_intent_seed" "$seed_summary"
else
  status "manual_intent_seed" "missing: $MANUAL_SEED"
fi

printf '\nOuroboros/MCP processes:\n'
ps aux | grep -i 'ouroboros mcp serve\|ooo seed\|ooo run\|pytest tests/unit/mcp' | grep -v grep || true

printf '\nExisting codbeing tests:\n'
(
  cd "$PROJECT_DIR" &&
  python3 -m unittest discover -s tests -v 2>&1
)

printf '\nNext if clean:\n'
printf '  cd %s\n' "$PROJECT_DIR"
printf '  /Users/sanggyulee/.local/bin/ooo seed interview_20260716_124202 --llm-backend codex\n'
