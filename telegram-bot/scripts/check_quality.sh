#!/usr/bin/env bash
# Canonical lint + format + typecheck for modules touched by mention/LLM UX work and shared fixes.
# Run from repo root: ./scripts/check_quality.sh
# Requires: pip install -r requirements-dev.txt -r requirements.txt (use a venv).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

FILES=(
  ai/llm.py
  ai/schemas.py
  bot/common/event_states.py
  config/logging.py
  bot/handlers/mentions.py
  bot/commands/event_creation.py
  main.py
)

python -m flake8 "${FILES[@]}"
python -m black --check "${FILES[@]}"
python -m mypy --config-file=mypy.ini --follow-imports=silent "${FILES[@]}"
echo "Quality checks OK (${#FILES[@]} files)."
