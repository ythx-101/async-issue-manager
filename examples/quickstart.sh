#!/bin/bash
# Quick Start — 5 分钟跑通异步 Issue 系统
#
# 前提: Python 3.8+

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)/scripts"
echo "📂 Skill 目录: $SCRIPT_DIR"

# 1. 初始化 .issues 目录
echo ""
echo "1️⃣  初始化 .issues/ 目录..."
mkdir -p .issues/{open,in-progress,closed}
echo "   ✅ 目录已创建"

# 2. 创建第一个 Issue
echo ""
echo "2️⃣  创建示例 Issue..."
python3 "$SCRIPT_DIR/manager.py" create \
  --title "测试：验证异步任务系统" \
  --body "这是一个测试 Issue，验证创建 → 分配 → 关闭的完整流程。" \
  --priority P2 \
  --labels test

# 3. 查看 Issue
echo ""
echo "3️⃣  查看 open Issues..."
python3 "$SCRIPT_DIR/manager.py" list --status open

# 4. 分配
echo ""
echo "4️⃣  分配给分析师..."
python3 "$SCRIPT_DIR/manager.py" assign 1 analyst

# 5. 关闭
echo ""
echo "5️⃣  关闭 Issue..."
python3 "$SCRIPT_DIR/manager.py" close 1 --resolution "测试通过，系统正常运行"

# 6. 统计
echo ""
echo "6️⃣  统计概览..."
python3 "$SCRIPT_DIR/manager.py" stats

# 7. 运行巡查
echo ""
echo "7️⃣  运行巡查系统..."
python3 "$SCRIPT_DIR/inspector.py" --dry-run

echo ""
echo "🎉 快速上手完成！"
echo ""
echo "接下来："
echo "  - 配置 cron 实现自动调度"
echo "  - 自定义 broadcast.py 中的 Agent 订阅"
echo "  - 在 inspector.py 中添加自定义检查规则"
