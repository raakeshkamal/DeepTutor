#!/usr/bin/env bash
# Run the source checkout with the existing DeepTutor runtime home.
set -euo pipefail
umask 077
DT_HOME="$HOME/deeptutor"
SOURCE="$HOME/Documents/DeepTutor"
VENV="$SOURCE/.venv"
DT="$VENV/bin/deeptutor"
API_PORT=8001
WEB_PORT=3782
PROXY="$SOURCE/scripts/litellm/manage.py"
export PATH="$VENV/node-runtime/node_modules/.bin:$VENV/bin:$PATH"
export DEEPTUTOR_HOME="$DT_HOME" DEEPTUTOR_CHAT_ENGINE=python NEXT_TELEMETRY_DISABLED=1
cd "$SOURCE"

listener() { lsof -tiTCP:"$1" -sTCP:LISTEN 2>/dev/null | head -1 || true; }
proxy() { uv run --no-project --python "$VENV/bin/python" python "$PROXY" "$1"; }
fork_backend() {
  local pid
  pid=$(listener "$API_PORT")
  [ -n "$pid" ] && ps -o command= -p "$pid" | rg -Fq -- "--app-dir $SOURCE "
}
ready() {
  proxy status >/dev/null 2>&1 && fork_backend &&
    curl -fsS --max-time 3 -o /dev/null "http://127.0.0.1:$API_PORT/api/knowledge-bases/health" 2>/dev/null &&
    curl -fsS --max-time 3 -o /dev/null "http://127.0.0.1:$WEB_PORT/api/knowledge-bases/health" 2>/dev/null
}
start() {
  proxy start
  if ready; then echo "DeepTutor fork is already running."; return; fi
  if [ -n "$(listener "$API_PORT")" ] || [ -n "$(listener "$WEB_PORT")" ]; then
    echo "A DeepTutor port is in use. Inspect it before starting the fork." >&2
    return 1
  fi
  "$DT" start --home "$DT_HOME" --detach --no-browser
  for _ in $(seq 1 120); do
    if ready; then echo "DeepTutor fork is ready at http://localhost:$WEB_PORT"; return; fi
    sleep 1
  done
  echo "DeepTutor did not become ready. Check $DT_HOME/data/user/runtime/launcher.log." >&2
  return 1
}
stop() {
  if [ -n "$(listener "$API_PORT")" ] && ! fork_backend; then
    echo "Port $API_PORT belongs to a different process. I did not stop it." >&2
    return 1
  fi
  "$DT" stop --home "$DT_HOME"
  if [ -n "$(listener "$API_PORT")" ] || [ -n "$(listener "$WEB_PORT")" ]; then
    echo "DeepTutor still owns a listening port; refusing to report a completed stop." >&2
    return 1
  fi
  proxy stop
}
case "${1:-start}" in
  start) start ;;
  stop) stop ;;
  status)
    if ready; then
      echo "DeepTutor fork is running: backend :$API_PORT, frontend :$WEB_PORT."
    else
      echo "DeepTutor fork is not ready on ports $API_PORT and $WEB_PORT."
      exit 1
    fi
    ;;
  restart)
    if [ -n "$(listener "$API_PORT")" ] || [ -n "$(listener "$WEB_PORT")" ]; then stop; fi
    start
    ;;
  upgrade)
    echo "This setup runs the checkout in $SOURCE. The packaged upgrade script does not update the fork." >&2
    exit 1
    ;;
  *) echo "Usage: $0 [start|stop|status|restart]" >&2; exit 2 ;;
esac
