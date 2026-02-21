---
name: async-issue-manager
description: |
  本地异步任务管理系统。用 .issues/ 目录 + Git 管理任务，Agent 自动建 Issue、调度派活、巡查修复。
  适合"上班前丢任务，下班后看结果"的异步工作流。不依赖任何外部服务。
metadata:
  version: 1.0.0
  author: YuLin807
  tags: [task-management, async, issues, automation, cron]
---

# Async Issue Manager

纯本地的异步任务管理系统。用文件系统代替数据库，Git 代替云服务，Agent 代替人工跟进。

## 核心理念

**人不在线时，Agent 依然在工作。**

```
你（早上）: "帮我研究一下 xxx"
  ↓
Agent 自动建 Issue → 排优先级 → 打标签
  ↓
白天每小时自动调度 → 判断派给哪个 Agent
  ↓
分析师/写手/探索者/临时工 → 各自执行
  ↓
完成 → 移入 .issues/closed/ → Git commit
  ↓
你（晚上）: 看 closed/ 里的结果
```

## 目录结构

```
.issues/
├── open/           # 待处理的任务
│   └── 035-研究xxx方案.md
├── in-progress/    # 正在执行的任务
│   └── 034-写教程.md
├── closed/         # 已完成的任务
│   ├── 001-修复bug.md
│   └── 002-写文档.md
└── index.json      # 索引（ID 计数器 + 全量记录）
```

## Issue 文件格式

每个 Issue 是一个 Markdown 文件，带 YAML front matter：

```markdown
---
id: 35
title: 研究 xxx 方案
priority: P1
labels: research, analysis
status: open
assignee: unassigned
created_at: 2026-02-21T10:00:00
updated_at: 2026-02-21T10:00:00
---

## 问题描述

具体描述任务内容...

## 期望结果

分析报告，包含方案对比...
```

### 优先级

| 优先级 | 含义 | 调度频率 |
|--------|------|----------|
| P0 | 紧急 | 立即处理 |
| P1 | 重要 | 下一个调度周期 |
| P2 | 普通 | 排队处理 |
| P3 | 低 | 有空再说 |

### 标签

标签决定任务派给谁：

| 标签 | 对应 Agent | 擅长 |
|------|-----------|------|
| `analysis`, `bug`, `performance` | 分析师 | 深度分析、架构设计 |
| `docs`, `writing` | 写手 | 中文写作、教程 |
| `research`, `cleanup` | 探索者 | 信息收集、整理 |
| `群聊`, `社交` | 社交 Agent | 群聊互动 |

## 使用方式

### 1. 创建 Issue（CLI）

```bash
# 在 Skill 目录内运行
python3 scripts/manager.py create \
  --title "研究 Peekaboo 集成方案" \
  --body "调研 Peekaboo macOS 自动化框架，评估与 OpenClaw 的集成可能" \
  --priority P1 \
  --labels research analysis
```

### 2. 创建 Issue（Agent 自然语言）

当用户说出任务时，Agent 应该：
1. 判断这是一个可异步执行的任务
2. 提取标题、优先级、标签
3. 调用 `manager.py create` 创建 Issue
4. 确认创建成功

**示例对话**：
```
用户: "帮我研究一下 karry_viber 的 Accessibility Service 方案"
Agent: 已创建 Issue #36: 研究 karry_viber Accessibility Service 方案 [P1, research]
```

### 3. 查看 Issue

```bash
# 列出所有 open Issues
python3 scripts/manager.py list --status open

# 查看单个 Issue
python3 scripts/manager.py show 35

# 按标签过滤
python3 scripts/manager.py list --labels research
```

### 4. 分配 Issue

```bash
python3 scripts/manager.py assign 35 analyst
```

### 5. 关闭 Issue

```bash
python3 scripts/manager.py close 35 --resolution "分析报告已生成，见 data/analysis.md"
```

## 自动化组件

### 自动调度（每小时）

`scripts/auto-dispatch.sh` — cron 每小时运行：

1. 运行巡查系统扫描问题
2. 广播所有 open Issues 给匹配的 Agent
3. 触发主 Agent 判断派活

**调度逻辑**：主 Agent 读取 open Issues，根据标签和优先级判断派给哪个子 Agent 执行。不是死板的规则路由，而是智能判断。

### 巡查系统（每天 2 次）

`scripts/inspector.py` — 自动发现问题并创建 Issue：

| 检查项 | 描述 |
|--------|------|
| not-implemented stubs | 代码中未实现的功能 |
| 文档同步 | 代码改了但文档没更新 |
| 未使用 Skills | 30 天未修改的 Skill |
| MEMORY.md 大小 | 超过 10KB 需精简 |
| 冥想产出 | 昨天是否完成冥想 |
| 进化日志 | evolution-log 是否有记录 |

巡查发现问题 → 自动创建 Issue → 下一个调度周期自动派活处理。

**文档同步检查器**（可扩展，参考 `inspector.py` 的 `check_docs_sync` 方法）：
- 自动扫描所有 Git 项目和 Skills
- 检测代码改了但 README/SKILL.md 没更新
- 新项目自动纳入监控，无需手动配置

### 广播系统

`scripts/broadcast.py` — 根据 Agent 订阅配置，将 Issue 推送给匹配的 Agent：

```python
# Agent 订阅配置示例
AGENT_SUBSCRIPTIONS = {
    "analyst": {
        "labels": ["bug", "performance", "analysis"],
        "priority": ["P0", "P1"]
    },
    "writer": {
        "labels": ["docs", "writing"],
        "priority": ["P1", "P2"]
    }
}
```

## Cron 配置示例

```
# 每小时自动调度
0 * * * * cd /workspace && bash scripts/auto-dispatch.sh

# 早晨巡查（06:30）
30 6 * * * cd /workspace && python3 scripts/inspector.py

# 晚间巡查（22:00）
0 22 * * * cd /workspace && python3 scripts/inspector.py
```

在 OpenClaw 中，使用内置 cron 系统替代系统 crontab：
- `sessionTarget: "isolated"` + `payload.kind: "agentTurn"` 用于需要 Agent 判断的任务
- `sessionTarget: "main"` + `payload.kind: "systemEvent"` 用于简单触发

## Git 管理

整个 `.issues/` 目录纳入 Git 管理：

```bash
# 每小时自动 commit
git add .issues/ && git commit -m "issues: auto-update $(date +%H:%M)" && git push
```

好处：
- 完整历史可追溯（谁建的、谁改的、什么时候关的）
- 不依赖任何外部服务（GitHub Issues、Jira、Notion）
- 离线可用，本地速度
- 多设备同步靠 git push/pull

## 适用场景

| 场景 | 做法 |
|------|------|
| 上班族 | 早上丢任务 → 白天 Agent 自动跑 → 晚上看结果 |
| 开发者 | 巡查系统自动发现 bug → 建 Issue → Agent 修复 |
| 内容创作 | 建"写教程"Issue → 写手 Agent 生成草稿 → 人工审核 |
| 研究 | 建"研究 xxx"Issue → 探索者收集资料 → 分析师出报告 |

## 安装

1. 将整个 `async-issue-manager/` 目录复制到你的工作区 `skills/` 下
2. 创建 `.issues/` 目录结构：`mkdir -p .issues/{open,in-progress,closed}`
3. 设置环境变量 `WORKSPACE` 指向你的工作区根目录（或让脚本自动检测）
4. 配置 cron 定时任务（参考上方 Cron 配置）
5. 运行 `examples/quickstart.sh` 验证安装

## 注意事项

- Issue ID 全局递增，不会重复
- 巡查系统自动去重——相同标题的 Issue 不会重复创建
- 文件移动（open → in-progress → closed）靠脚本自动处理
- `index.json` 是索引文件，不要手动编辑
