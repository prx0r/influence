#!/usr/bin/env bash
# launch-8795.sh — studio backend (youtube.agentcom.org). Detached, survives shell.
cd /root/influence/dash
export LIVE=1 YT_MODE=1 DASH_PORT=8795
export DASH_DB="${DASH_DB:-$PWD/influence.db}"
export DASH_JOURNAL="${DASH_JOURNAL:-$PWD/decisions.db}"
exec /root/stevejobless/.venv/bin/python server.py >> dash-8795.log 2>&1
