#!/usr/bin/env sh
set -eu
export PYTHONDONTWRITEBYTECODE=1

if [ "$#" -lt 1 ]; then
  echo "usage: run-python.sh <script> [args...]" >&2
  exit 2
fi

script=$1
shift
case "$script" in
  /*) ;;
  *) script="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/$script" ;;
esac

if [ -n "${WORLDBUILDING_PYTHON:-}" ] && "$WORLDBUILDING_PYTHON" -c 'import sys' >/dev/null 2>&1; then
  exec "$WORLDBUILDING_PYTHON" "$script" "$@"
fi

if [ -x "$PWD/.venv/bin/python" ] && "$PWD/.venv/bin/python" -c 'import sys' >/dev/null 2>&1; then
  exec "$PWD/.venv/bin/python" "$script" "$@"
fi

for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys' >/dev/null 2>&1; then
    exec "$candidate" "$script" "$@"
  fi
done

echo "The bundled canon tools could not find a usable Python runtime." >&2
exit 127
