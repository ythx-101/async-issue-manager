#!/bin/bash
# Issue 系统自动调度 — 每小时运行
# 功能：巡查 → 建 Issue → 广播 → 通知主 Agent 派活
#
# 用法:
#   bash scripts/auto-dispatch.sh
#
# Cron (OpenClaw):
#   schedule: { kind: "cron", expr: "0 * * * *" }
#   payload: { kind: "systemEvent", text: "issue-hourly-dispatch" }

set -e

# 自动检测工作区
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="${WORKSPACE:-$(cd "$SCRIPT_DIR/.." && pwd)}"
cd "$WORKSPACE"

LOG_DIR="$WORKSPACE/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/issue-dispatch.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"; }

log "=== 开始 Issue 自动调度 ==="

# 1. 运行巡查（如果有 daily_check.py）
INSPECTOR="$WORKSPACE/scripts/inspector/daily_check.py"
if [ -f "$INSPECTOR" ]; then
    log "运行巡查..."
    python3 "$INSPECTOR" >> "$LOG_FILE" 2>&1 || true
fi

# 2. 广播 open Issues
log "广播 open Issues..."
python3 "$SCRIPT_DIR/broadcast.py" >> "$LOG_FILE" 2>&1

# 3. 统计
OPEN_COUNT=$(python3 "$SCRIPT_DIR/manager.py" list --status open 2>/dev/null | grep -c "^  #" || echo "0")

if [ "$OPEN_COUNT" -gt 0 ]; then
    log "发现 $OPEN_COUNT 个 open Issues，等待主 Agent 调度"
else
    log "无 open Issues，跳过"
fi

log "=== 调度完成 ==="
